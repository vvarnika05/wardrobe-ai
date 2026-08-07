from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileCreate, ProfileResponse #pydantic models the incoming request is validated against profileCreate and the outgoing response is validated against profileResponse
from app.services.profile_parser import parse_style_profile

router = APIRouter() #this is the router for the profile endpoints. It is included in the main app in main.py

#Notice something. There is no /profile here. Only an empty string. Why? Because the router is included in the main app with a prefix of /profile. So the full path for this endpoint is /profile. This is a common pattern in FastAPI to keep the code organized and avoid repeating the prefix in every endpoint.
@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_profile(
    payload: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    """
    Create a profile for the logged-in user, or update it if one already exists.
    style_tags come from Gemini parsing of style_description.
    """
    try:
        style_tags = parse_style_profile(payload.style_description) # this calls the function that uses Gemini API to parse the style description and return style tags
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse style description with LLM: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM request failed: {exc}",
        ) from exc

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if profile is None:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    profile.style_description = payload.style_description
    profile.style_tags = style_tags
    profile.color_prefs = payload.color_prefs
    profile.fit_pref = payload.fit_pref
    profile.sleeve_pref = payload.sleeve_pref
    profile.gender_pref = payload.gender_pref

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create one with POST /profile first.",
        )
    return profile
