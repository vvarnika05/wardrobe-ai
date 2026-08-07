from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


GenderPref = Literal["men", "women", "unisex"]


class ProfileCreate(BaseModel):
    style_description: str
    color_prefs: list[str]
    fit_pref: str
    sleeve_pref: str
    # Clothing department to browse — not the user's identity.
    gender_pref: GenderPref = Field(
        ...,
        description='Clothing filter: "men", "women", or "unisex"',
    )


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    style_description: str | None
    style_tags: dict | None
    color_prefs: list | dict | None
    fit_pref: str | None
    sleeve_pref: str | None
    gender_pref: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
