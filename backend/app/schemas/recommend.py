from pydantic import BaseModel


class RecommendedOutfit(BaseModel):
    outfit_id: int
    category: str | None
    color_tags: list
    formality_level: str | None
    reason: str
    # Full browser-loadable URL, e.g. http://localhost:8000/static/images/35989.jpg
    image_url: str | None = None


class RecommendResponse(BaseModel):
    outfits: list[RecommendedOutfit]
