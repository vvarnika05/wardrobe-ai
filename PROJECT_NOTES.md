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
| `POST` | `/profile` | yes | upsert by `user_id`; body `{style_description, color_prefs, fit_pref, sleeve_pref, gender_pref}` where `gender_pref` is `"men"` \| `"women"` \| `"unisex"` (clothing to browse, **not** identity); Gemini parses `style_description` → `style_tags` |
| `GET` | `/profile/me` | yes | 404 if no profile; `gender_pref` may be `null` on older rows |
| `GET` | `/recommend` | yes | ranked swipe deck; excludes already-swiped outfit_ids; Chroma **gender** filter when `gender_pref` is men/women; color-relevance ranking; `image_url` via `/static/images/...` |
| `POST` | `/swipe` | yes | `{outfit_id, decision}` where decision is `"accepted"` \| `"rejected"`; **upsert** on `(user_id, outfit_id)` |
| `GET` | `/saved` | yes | accepted swipes + outfit metadata + `image_url` + `swiped_at` |
| `GET` | `/swipes` | yes | full swipe history (debug) |

**Static images:** `GET /static/images/{filename}` serves files from `backend/data/raw/images/`.

**Outfit image resolution (known limitation):** every curated outfit file is **60×80 px** JPEG — the Kaggle Fashion Product Images **Small** dump. Softness from upscaling is inherent; CSS cannot invent detail. UI prioritizes a usable focal card over pixel-perfect sharpness: SwipeDeck page `max-width: 480px` → card ~**440px** wide (capped by `max-height: min(62vh, 580px)`); Saved grid `minmax(200px, 1fr)`. Overlay labels are stacked (category, then formality/color) so they don’t collide. Profile / StyleQuizForm do **not** render outfit images. Swap to the high-res Kaggle set if crisp product photos are required.

### Models (Postgres)

- **User** — id, email, hashed_password, created_at  
- **Profile** — user_id FK, style_description, style_tags (JSON dict from Gemini), color_prefs, fit_pref, sleeve_pref, **gender_pref** (`men`/`women`/`unisex`, nullable), timestamps  
- **Outfit** — image_url, category, **gender** (Kaggle: Men/Women/Boys/Girls/Unisex), style_tags, formality_level, color_tags, embedding_id  
- **SwipeLog** — unique `(user_id, outfit_id)`, decision, created_at, updated_at  

### Scripts (run from `backend/` with venv + `.env`)

1. `python scripts/create_tables.py` — `create_all` only (does **not** alter existing tables)  
2. `python scripts/build_outfit_dataset.py` — Kaggle `data/raw/styles.csv` → `data/outfit_dataset/metadata.json` (~180 stratified; includes `gender` + `source_id`; skips Accessories; skips kidswear display names — some kids image files in the Kaggle dump are mismatched, e.g. id `5019` CSV=Skirts but `5019.jpg` is a tote)  
3. `python scripts/load_outfits_to_db.py` [`--force`] — load JSON into Outfit  
4. `python scripts/build_embeddings.py` [`--force`] — text embed → Chroma + set `embedding_id` (metadata includes `gender`)  
5. `python scripts/migrate_swipe_logs_unique.py` — add `updated_at` + unique constraint (needed because no Alembic)  
6. `python scripts/migrate_add_gender.py` — `ALTER` add `outfits.gender` + `profiles.gender_pref`  
7. `python scripts/backfill_outfit_gender.py` — CSV gender → Outfit rows (match by image filename / source_id); also patches `metadata.json`

**Gender rollout (existing DB) — run in order:**

```bash
cd backend && source .venv/bin/activate
python scripts/migrate_add_gender.py
python scripts/backfill_outfit_gender.py
python scripts/build_embeddings.py --force
```

Then restart uvicorn. Edit profile to set `gender_pref`, then hit `/recommend`.

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

**StyleQuizForm** — color chips + **Clothing to show** chips (`gender_pref`: Men / Women / Unisex). Profile Preferences card shows `gender_pref` or “Not set yet”.

---

## Recommendation / “RAG” pipeline (architectural)

This is **text-tag retrieval + LLM ranking**, not image embeddings and not a classic document RAG corpus.

1. **Profile** — free text → Gemini → structured `style_tags`; form also stores `color_prefs`, fit/sleeve, and **`gender_pref`** (clothing department).  
2. **Index** — each outfit embedded from a fixed string shape including gender, e.g.  
   `category: …, tags: …, color: …, formality: …, gender: …`  
   via `sentence-transformers` `all-MiniLM-L6-v2` → Chroma collection `"outfits"` (persistent under `backend/data/chroma_store/`). Metadata includes scalar `gender` for filters.  
3. **Retrieve** — `retrieve_candidate_outfits(...)` embeds a profile query string; if `gender_pref` is **`men`** → Chroma `where gender $in [Men, Unisex]`; **`women`** → `[Women, Unisex]`; **`unisex` or unset** → **no gender filter** (full catalog — only ~2 Unisex-tagged curated items, so filtering to Unisex alone would empty decks). Over-fetches, drops already-swiped ids, keeps up to `top_k=15`.  
4. **Generate** — `generate_recommendations` tags each candidate `[COLOR MATCH]` / `[COLOR MISMATCH]` via case-insensitive overlap of outfit `color_tags` vs profile `color_prefs`, sends candidates + profile + static trends to Gemini (prompt strongly prefers MATCH); LLM must pick only given `outfit_id`s. Exhausted catalog → short/`[]` deck, no error.  
5. **Validate** — drop invented IDs; merge reasons; **re-sort COLOR MATCH before MISMATCH**.  
6. **Serve** — attach public `image_url` in the recommend (and saved) routes.

**Swipe exclusion:** `GET /recommend` loads all of the current user’s `SwipeLog.outfit_id`s into `exclude_ids` before retrieval.

**Trends** are a manually edited JSON list — no scraping, no scheduling, not embedded.

---

## Design system (do not contradict)

- **`frontend/src/styles/brand.css`** — sitewide tokens: Fraunces (`--font-display`), Caveat (`--font-script`), Inter (`--font-body`), coral accent `--color-accent: #e8836b` (replaced old gold `#c4a05a`).  
- **Dark app pages** — `#0d0d0d` background (`index.css`); cards often `#1a1a1a`.  
- **Landing** — separate cream palette under `.landing-page` only; typography/accent alias brand tokens.  
- Shared form: **StyleQuizForm** (onboarding + profile edit) — dark inputs, coral chips (colors + clothing-to-show), styled selects.

---

## Known issues / fragile spots

- **Kaggle image/ID mismatches** — rare corrupt pairs where `styles.csv` is correct but `{id}.jpg` shows a different product (confirmed: `5019` CSV=Skirts/Bottomwear, image=tote). Mapping was fine; kidswear display-name filter in `build_outfit_dataset.py` drops those rows. Accessories (bags, watches, etc.) are already excluded via `masterCategory`.  
- **Low-res outfit images (60×80)** — source Kaggle “small” dataset; some upscale softness is accepted so SwipeDeck stays a large focal card (~440px). True sharpness needs higher-res assets.  
- **Query vs document text mismatch** — profile query uses `aesthetic` / `fit` / `sleeve`; outfit vectors use `category` / Kaggle tags; retrieval is directional but noisy. Color preference is reinforced post-retrieval via exact `color_tags` ∩ `color_prefs` (case-insensitive) — synonyms like cream≈beige are not fuzzy-matched.  
- **Tag-only embeddings** — no CLIP/vision; color can lose to shared “Casual Topwear” tokens.  
- **Catalog exhaustion** — ~180 outfits; after enough swipes `/recommend` may return a short or empty deck (by design — no error). Re-swiping the same id still upserts `SwipeLog`. Gender filter further shrinks the candidate pool.  
- **Chroma vs Postgres sync** — if `data/chroma_store/` is deleted, `build_embeddings.py` without `--force` skips rows that already have `embedding_id`. Use `--force` to rebuild. After `load_outfits_to_db.py --force` (new outfit ids), always re-run `build_embeddings.py` (even without `--force` is enough to **delete orphan Chroma ids**); leftover old ids caused “No image” on swipe cards.  
- **`create_all` ≠ migrations** — schema changes need explicit SQL/scripts (`migrate_add_gender.py`, etc.).  
- **Gemini** — sync, can be slow; `google.generativeai` shows deprecation warnings; model name may be `gemini-2.5-flash` in `llm_client.py`.  
- **Swipe drag** — buttons are solid; drag/exit animation can be rough.  
- **CORS** — `allow_origins=["*"]` + credentials is fine for Bearer-token SPA in dev; tighten before deploy.  
- **Profiles** — no DB unique on `user_id` (app upserts; rare race possible). Older profiles may have `gender_pref=null` until edited.  
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
- `gender_pref` is clothing-department preference, not identity.
