from datetime import datetime

from pydantic import BaseModel


class ProfileCreate(BaseModel):
    style_description: str
    color_prefs: list[str]
    fit_pref: str
    sleeve_pref: str


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    style_description: str | None
    style_tags: dict | None
    color_prefs: list | dict | None
    fit_pref: str | None
    sleeve_pref: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
