
## Fashion Recommender

A swipe-based fashion recommendation app. Users describe their style, set color / fit / sleeve preferences and which clothing department they want to browse, then get a personalized deck of outfits. Likes are saved; already-seen looks are excluded from future decks.

This repo is a full-stack v1: FastAPI backend + Vite React frontend, with text-tag retrieval (Chroma) and Gemini ranking.

---

## Features

- **Auth** — signup / login with JWT
- **Style onboarding** — free-text style note → Gemini → structured tags, plus color chips, fit, sleeve, and clothing-to-show (`men` / `women` / `unisex`)
- **Swipe deck** — ranked recommendations with reasons; accept / reject logged to Postgres
- **Saved wardrobe** — accepted outfits with images
- **Profile** — view and edit preferences
- **Resilient recommendations** — if Gemini is unavailable (quota, network, etc.), the API still returns a color-sorted Chroma shortlist (`curated_by_ai: false`) so swipe keeps working

---

## Stack

| Layer | Tech |
|--------|------|
| Frontend | Vite, React (JavaScript), React Router, Framer Motion |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | Postgres (e.g. Supabase) |
| Vectors | Chroma (local persistent store) + `sentence-transformers` (`all-MiniLM-L6-v2`) |
| LLM | Google Gemini (profile parsing + deck ranking) |
| Catalog | Stratified ~180 outfits from the Kaggle Fashion Product Images (Small) dump |

No Docker. No Alembic (schema changes via small SQL scripts).

---

## How recommendations work

This is **text-tag retrieval + LLM ranking**, not image/CLIP embeddings.

1. **Profile** — style text → Gemini `style_tags`; form stores `color_prefs`, fit/sleeve, `gender_pref`
2. **Index** — each outfit embedded from a string like `category / tags / color / formality / gender` into Chroma
3. **Retrieve** — embed a profile query; Chroma top-k with optional **gender** metadata filter; drop already-swiped IDs
4. **Rank** — color MATCH/MISMATCH tagging; Gemini ranks and writes short reasons (user color prefs outrank trend phrases)
5. **Fallback** — on Gemini failure, return color-sorted retrieval results with a generic reason and `curated_by_ai: false`
6. **Serve** — attach public image URLs from `/static/images/...`

---

## Project layout

```
fashion-recommender/
├── backend/          # FastAPI app, scripts, data, Chroma store
│   ├── app/
│   ├── scripts/      # dataset load, embeddings, migrations
│   └── data/         # raw Kaggle dump, metadata, trends, chroma_store
├── frontend/         # Vite React SPA
└── PROJECT_NOTES.md  # detailed handoff / architecture notes
```

---

## Setup

### Prerequisites

- Python 3.11+ (3.13 works in this project)
- Node.js 18+
- Postgres database
- Gemini API key
- Kaggle Fashion Product Images (Small): `styles.csv` + `images/` under `backend/data/raw/`

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME
JWT_SECRET_KEY=your-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
GEMINI_API_KEY=your-gemini-key
# Optional: force color-sorted fallback without calling Gemini
# RECOMMEND_FORCE_FALLBACK=true
```

Bootstrap data (from `backend/` with venv active):

```bash
python scripts/create_tables.py
python scripts/build_outfit_dataset.py
python scripts/load_outfits_to_db.py
python scripts/build_embeddings.py

# If upgrading an existing DB (gender columns, swipe uniqueness, etc.):
python scripts/migrate_swipe_logs_unique.py
python scripts/migrate_add_gender.py
python scripts/backfill_outfit_gender.py
python scripts/build_embeddings.py --force
```

Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

```bash
npm run dev
```

App: `http://localhost:5173`

---

## API overview

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | — | Health check |
| `POST` | `/auth/signup` | — | Create account |
| `POST` | `/auth/login` | — | Login → JWT |
| `GET` | `/auth/me` | Bearer | Current user |
| `POST` | `/profile` | Bearer | Upsert style profile |
| `GET` | `/profile/me` | Bearer | Current profile |
| `GET` | `/recommend` | Bearer | Swipe deck (`curated_by_ai` / `used_llm`) |
| `POST` | `/swipe` | Bearer | Log accept / reject (upsert) |
| `GET` | `/saved` | Bearer | Accepted outfits |
| `GET` | `/swipes` | Bearer | Full swipe history (debug) |
| `GET` | `/static/images/{file}` | — | Outfit images |

`gender_pref` is **clothing to browse** (`men` / `women` / `unisex`), not personal identity.

---

## Frontend routes

| Route | Page |
|-------|------|
| `/` | Landing |
| `/signup` | Signup → onboarding |
| `/login` | Login → swipe |
| `/onboarding` | Style quiz |
| `/swipe` | Recommendation deck |
| `/saved` | Saved outfits |
| `/profile` | Profile view / edit |

---

## Known limitations (v1)

- Outfit images are **60×80** (Kaggle Small) — some softness when displayed large
- ~180 curated items; decks can run short after many swipes
- Tag-only embeddings (no vision); color matching is exact string overlap, not synonyms
- Bright colors (e.g. pink/red/purple) are sparse in the catalog
- No Docker / Alembic; keep Postgres and Chroma in sync after `--force` reloads (re-run `build_embeddings.py` so orphan vector IDs don’t cause “No image”)

More detail: see [`PROJECT_NOTES.md`](./PROJECT_NOTES.md).

---

