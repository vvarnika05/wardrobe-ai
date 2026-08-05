from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, profile, recommend, swipe

app = FastAPI(title="Fashion Recommender API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(recommend.router, prefix="/recommend", tags=["recommend"])
app.include_router(swipe.router, tags=["swipe"])

# Serve outfit JPGs so the frontend can load them as <img src="...">.
# DB stores paths like "data/raw/images/35989.jpg"; URLs become /static/images/35989.jpg
_IMAGES_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "images"
app.mount("/static/images", StaticFiles(directory=str(_IMAGES_DIR)), name="outfit_images")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
