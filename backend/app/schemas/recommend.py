from pydantic import BaseModel


class RecommendedOutfit(BaseModel):
    outfit_id: int
    category: str | None
    color_tags: list
    formality_level: str | None
    reason: str


class RecommendResponse(BaseModel):
    outfits: list[RecommendedOutfit]
