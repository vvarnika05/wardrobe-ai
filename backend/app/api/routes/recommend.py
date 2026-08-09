from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.outfit import Outfit
from app.models.profile import Profile
from app.models.swipe_log import SwipeLog
from app.models.user import User
from app.schemas.recommend import RecommendResponse
from app.services.recommendation_engine import generate_recommendations

router = APIRouter()


def _public_image_url(request: Request, stored_path: str | None) -> str | None:
    """
    Turn a DB path like "data/raw/images/35989.jpg" into a browser URL
    served by FastAPI StaticFiles at /static/images/...
    """
    if not stored_path:
        return None
    if stored_path.startswith("http://") or stored_path.startswith("https://"):
        return stored_path
    # data/raw/images/35989.jpg → 35989.jpg
    filename = stored_path.rstrip("/").split("/")[-1]
    base = str(request.base_url).rstrip("/")
    return f"{base}/static/images/{filename}"


@router.get("", response_model=RecommendResponse)
def get_recommendations(
    request: Request,
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
    gender_pref = profile.gender_pref  # may be None on older profiles

    # Any prior swipe (accepted or rejected) — exclude so decks don't resurface.
    exclude_ids = {
        outfit_id
        for (outfit_id,) in db.query(SwipeLog.outfit_id)
        .filter(SwipeLog.user_id == current_user.id)
        .all()
    }

    try:
        outfits, curated_by_ai = generate_recommendations(
            profile=style_tags,
            color_prefs=color_prefs,
            fit_pref=fit_pref,
            sleeve_pref=sleeve_pref,
            deck_size=10,
            exclude_ids=exclude_ids,
            gender_pref=gender_pref,
        )
    except Exception as exc:
        # Retrieval / unexpected failures only — Gemini errors are handled inside
        # generate_recommendations via color-sorted fallback (HTTP 200).
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recommendation retrieval failed: {exc}",
        ) from exc

    # Attach browser-loadable image URLs from Outfit rows.
    ids = [o["outfit_id"] for o in outfits]
    rows = {
        row.id: row
        for row in db.query(Outfit).filter(Outfit.id.in_(ids)).all()
    } if ids else {}
    for o in outfits:
        row = rows.get(o["outfit_id"])
        o["image_url"] = _public_image_url(request, row.image_url if row else None)

    return RecommendResponse(
        outfits=outfits,
        curated_by_ai=curated_by_ai,
        used_llm=curated_by_ai,
    )
