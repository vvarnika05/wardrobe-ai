from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.recommend import RecommendResponse
from app.services.recommendation_engine import generate_recommendations

router = APIRouter()


@router.get("", response_model=RecommendResponse)
def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendResponse:
    """
    Build a ranked swipe deck for the logged-in user.
    Requires an existing Profile (create one via POST /profile first).
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create one with POST /profile first.",
        )

    style_tags = profile.style_tags if isinstance(profile.style_tags, dict) else {}
    color_prefs = profile.color_prefs if isinstance(profile.color_prefs, list) else []
    fit_pref = profile.fit_pref or ""
    sleeve_pref = profile.sleeve_pref or ""

    try:
        outfits = generate_recommendations(
            profile=style_tags,
            color_prefs=color_prefs,
            fit_pref=fit_pref,
            sleeve_pref=sleeve_pref,
            deck_size=10,
        )
    except ValueError as exc:
        # Validation failures (invented IDs, empty picks) and clear data errors.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recommendation validation failed: {exc}",
        ) from exc
    except Exception as exc:
        # LLM / network / unexpected failures.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recommendation LLM request failed: {exc}",
        ) from exc

    return RecommendResponse(outfits=outfits)
