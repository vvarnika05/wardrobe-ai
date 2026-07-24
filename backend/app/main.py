from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
# usually for a fastapi application we should write all the routes in the main.py but in this application we kind of decouple it into different files and merge them all in the main file

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


