from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.outfit import Outfit
from app.models.swipe_log import SwipeLog
from app.models.user import User
from app.schemas.swipe import SavedOutfit, SwipeCreate, SwipeResponse

router = APIRouter()


def _public_image_url(request: Request, stored_path: str | None) -> str | None:
    """DB path like data/raw/images/35989.jpg → http://…/static/images/35989.jpg"""
    if not stored_path:
        return None
    if stored_path.startswith("http://") or stored_path.startswith("https://"):
        return stored_path
    filename = stored_path.rstrip("/").split("/")[-1]
    base = str(request.base_url).rstrip("/")
    return f"{base}/static/images/{filename}"


@router.post("/swipe", response_model=SwipeResponse)
def create_swipe(
    payload: SwipeCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SwipeLog:
    """
    Upsert a swipe: insert if new (user, outfit), otherwise update decision.
    """
    outfit = db.query(Outfit).filter(Outfit.id == payload.outfit_id).first()
    if outfit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outfit {payload.outfit_id} not found",
        )

    swipe = (
        db.query(SwipeLog)
        .filter(
            SwipeLog.user_id == current_user.id,
            SwipeLog.outfit_id == payload.outfit_id,
        )
        .first()
    )

    now = datetime.now(timezone.utc)

    if swipe is None:
        swipe = SwipeLog(
            user_id=current_user.id,
            outfit_id=payload.outfit_id,
            decision=payload.decision,
        )
        db.add(swipe)
        response.status_code = status.HTTP_201_CREATED
    else:
        swipe.decision = payload.decision
        # Explicitly bump updated_at so "most recent" reflects this re-swipe
        # (SQLAlchemy onupdate only fires on UPDATE via ORM flush, but being
        # explicit keeps behavior obvious when reading the code).
        swipe.updated_at = now
        response.status_code = status.HTTP_200_OK

    db.commit()
    db.refresh(swipe)
    return swipe


@router.get("/saved", response_model=list[SavedOutfit])
def get_saved_outfits(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedOutfit]:
    """Return outfits the user accepted, most recent swipe first."""
    rows = (
        db.query(SwipeLog, Outfit)
        .join(Outfit, Outfit.id == SwipeLog.outfit_id)
        .filter(
            SwipeLog.user_id == current_user.id,
            SwipeLog.decision == "accepted",
        )
        .order_by(SwipeLog.updated_at.desc())
        .all()
    )

    return [
        SavedOutfit(
            outfit_id=outfit.id,
            category=outfit.category,
            color_tags=outfit.color_tags if isinstance(outfit.color_tags, list) else [],
            formality_level=outfit.formality_level,
            swiped_at=swipe.updated_at,
            image_url=_public_image_url(request, outfit.image_url),
        )
        for swipe, outfit in rows
    ]


@router.get("/swipes", response_model=list[SwipeResponse])
def get_swipe_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SwipeLog]:
    """Full swipe history (accepted + rejected) for debugging."""
    return (
        db.query(SwipeLog)
        .filter(SwipeLog.user_id == current_user.id)
        .order_by(SwipeLog.updated_at.desc())
        .all()
    )
