# Fashion Recommender — Project Notes

Concise handoff for a fresh session. Do **not** re-architect what already works without an explicit ask.

**Stack:** FastAPI + Postgres (Supabase) + Chroma (local) + Gemini · Vite React (JS) frontend  
**Layout:** `backend/` and `frontend/` siblings · **no Docker** · git is handled manually by the owner

---

## Backend — endpoints that exist and work

Base URL (dev): `http://localhost:8000`  
Auth: JWT Bearer (`Authorization: Bearer <token>`). CORS allows all origins for now.

| Method | Path | Auth | Notes |
|--------|------|------|--------|
| `GET` | `/health` | no | `{"status":"ok"}` |
| `POST` | `/auth/signup` | no | `{email, password}` → `{access_token, token_type}` |
| `POST` | `/auth/login` | no | same |
| `GET` | `/auth/me` | yes | current user |
| `POST` | `/profile` | yes | upsert by `user_id`; body `{style_description, color_prefs, fit_pref, sleeve_pref}`; Gemini parses `style_description` → `style_tags` |
| `GET` | `/profile/me` | yes | 404 if no profile |
| `GET` | `/recommend` | yes | ranked swipe deck; excludes already-swiped outfit_ids (any decision); includes `image_url` (full URL via `/static/images/...`) |
| `POST` | `/swipe` | yes | `{outfit_id, decision}` where decision is `"accepted"` \| `"rejected"`; **upsert** on `(user_id, outfit_id)` |
| `GET` | `/saved` | yes | accepted swipes + outfit metadata + `image_url` + `swiped_at` |
| `GET` | `/swipes` | yes | full swipe history (debug) |

**Static images:** `GET /static/images/{filename}` serves files from `backend/data/raw/images/`.

### Models (Postgres)

- **User** — id, email, hashed_password, created_at  
- **Profile** — user_id FK, style_description, style_tags (JSON dict from Gemini), color_prefs, fit_pref, sleeve_pref, timestamps  
- **Outfit** — image_url (relative path in DB), category, style_tags, formality_level, color_tags, embedding_id  
- **SwipeLog** — unique `(user_id, outfit_id)`, decision, created_at, updated_at  

### Scripts (run from `backend/` with venv + `.env`)

1. `python scripts/create_tables.py` — `create_all` only (does **not** alter existing tables)  
2. `python scripts/build_outfit_dataset.py` — Kaggle `data/raw/styles.csv` → `data/outfit_dataset/metadata.json` (~180 stratified)  
3. `python scripts/load_outfits_to_db.py` [`--force`] — load JSON into Outfit  
4. `python scripts/build_embeddings.py` [`--force`] — text embed → Chroma + set `embedding_id`  
5. `python scripts/migrate_swipe_logs_unique.py` — add `updated_at` + unique constraint (needed because no Alembic)

---

## Frontend — pages that exist and work

Dev: `npm run dev` in `frontend/` · `VITE_API_BASE_URL=http://localhost:8000`

| Route | Page | Auth | Notes |
|-------|------|------|--------|
| `/` | Landing | public | Cream/olive/maroon scroll landing; scoped `landing.css` |
| `/signup` | Signup | public | → onboarding |
| `/login` | Login | public | → `/swipe` |
| `/onboarding` | Onboarding | protected | StyleQuizForm → Gemini profile → `/swipe` |
| `/swipe` | SwipeDeck | protected | NavBar; buttons + optional framer-motion drag; background `POST /swipe` |
| `/saved` | SavedOutfits | protected | Grid of accepted outfits |
| `/profile` | Profile | protected | Read cards + Edit via shared StyleQuizForm |

**NavBar** only on `/swipe`, `/saved`, `/profile` — not on Landing / Login / Signup / Onboarding.

---

## Recommendation / “RAG” pipeline (architectural)

This is **text-tag retrieval + LLM ranking**, not image embeddings and not a classic document RAG corpus.

1. **Profile** — free text → Gemini → structured `style_tags` (`aesthetic`, `formality_range`, `dominant_colors`, `pattern_pref`).  
2. **Index** — each outfit embedded from a fixed string shape, e.g.  
   `category: …, tags: …, color: …, formality: …`  
   via `sentence-transformers` `all-MiniLM-L6-v2` → Chroma collection `"outfits"` (persistent under `backend/data/chroma_store/`).  
3. **Retrieve** — `retrieve_candidate_outfits(...)` embeds a profile query string, over-fetches from Chroma (`top_k + len(exclude_ids)`), drops already-swiped `outfit_id`s, then keeps up to `top_k=15` neighbors with distance (lower = closer).  
4. **Generate** — `generate_recommendations` sends candidates + profile + static trends (`data/trend_data.json` via `get_current_trends`) to Gemini; LLM must pick only given `outfit_id`s. If the catalog is exhausted after exclusions, returns fewer than `deck_size` (or `[]`) — no error.  
5. **Validate** — `validate_llm_outfit_selection` drops invented IDs / bad shapes; merge reasons onto real candidate metadata.  
6. **Serve** — attach public `image_url` in the recommend (and saved) routes.

**Swipe exclusion:** `GET /recommend` loads all of the current user’s `SwipeLog.outfit_id`s (accepted **and** rejected) into `exclude_ids`, passes them into `generate_recommendations` → `retrieve_candidate_outfits`. Filtering happens before `top_k` truncation so exclusions don’t starve the shortlist.

**Trends** are a manually edited JSON list — no scraping, no scheduling, not embedded.

---

## Design system (do not contradict)

- **`frontend/src/styles/brand.css`** — sitewide tokens: Fraunces (`--font-display`), Caveat (`--font-script`), Inter (`--font-body`), coral accent `--color-accent: #e8836b` (replaced old gold `#c4a05a`).  
- **Dark app pages** — `#0d0d0d` background (`index.css`); cards often `#1a1a1a`.  
- **Landing** — separate cream palette under `.landing-page` only; typography/accent alias brand tokens.  
- Shared form: **StyleQuizForm** (onboarding + profile edit) — dark inputs, coral color chips, styled selects.

---

## Known issues / fragile spots

- **Query vs document text mismatch** — profile query uses `aesthetic` / `fit` / `sleeve`; outfit vectors use `category` / Kaggle tags; retrieval is directional but noisy.  
- **Tag-only embeddings** — no CLIP/vision; color can lose to shared “Casual Topwear” tokens.  
- **Catalog exhaustion** — ~180 outfits; after enough swipes `/recommend` may return a short or empty deck (by design — no error). Re-swiping the same id still upserts `SwipeLog`.  
- **Chroma vs Postgres sync** — if `data/chroma_store/` is deleted, `build_embeddings.py` without `--force` skips rows that already have `embedding_id`. Use `--force` to rebuild.  
- **`create_all` ≠ migrations** — schema changes (e.g. swipe unique) need explicit SQL/scripts.  
- **Gemini** — sync, can be slow; `google.generativeai` shows deprecation warnings; model name may be `gemini-2.5-flash` in `llm_client.py`.  
- **Swipe drag** — buttons are solid; drag/exit animation can be rough.  
- **CORS** — `allow_origins=["*"]` + credentials is fine for Bearer-token SPA in dev; tighten before deploy.  
- **Profiles** — no DB unique on `user_id` (app upserts; rare race possible).  
- **LLM output** — `style_tags` shape not schema-validated beyond “is a dict”; invented recommend IDs are dropped by validators.

---

## How to run (dev)

```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev
```

Env: `backend/.env` (DATABASE_URL, JWT_*, GEMINI_API_KEY) · `frontend/.env` (`VITE_API_BASE_URL`).

---

## Explicit non-goals / past decisions

- No Docker.  
- No Alembic (scripts + occasional raw SQL).  
- No image/vision embeddings for v1.  
- No automated trend scraping.  
- Frontend is JavaScript (not TypeScript) by choice.  
- JWT in `localStorage` is intentional for this Vite SPA.
