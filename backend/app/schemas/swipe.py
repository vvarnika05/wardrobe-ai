from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SwipeCreate(BaseModel):
    outfit_id: int
    # Anything other than these two values → FastAPI 422
    decision: Literal["accepted", "rejected"]


class SwipeResponse(BaseModel):
    id: int
    user_id: int
    outfit_id: int
    decision: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SavedOutfit(BaseModel):
    outfit_id: int
    category: str | None
    color_tags: list
    formality_level: str | None
    swiped_at: datetime
