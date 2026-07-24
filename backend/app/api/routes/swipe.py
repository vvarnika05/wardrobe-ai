from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.outfit import Outfit
from app.models.swipe_log import SwipeLog
from app.models.user import User
from app.schemas.swipe import SavedOutfit, SwipeCreate, SwipeResponse

router = APIRouter()


@router.post("/swipe", response_model=SwipeResponse, status_code=status.HTTP_201_CREATED)
def create_swipe(
    payload: SwipeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SwipeLog:
    """Log one swipe decision (accepted or rejected) for the current user."""
    outfit = db.query(Outfit).filter(Outfit.id == payload.outfit_id).first()
    if outfit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outfit {payload.outfit_id} not found",
        )

    swipe = SwipeLog(
        user_id=current_user.id,
        outfit_id=payload.outfit_id,
        decision=payload.decision,
    )
    db.add(swipe)
    db.commit()
    db.refresh(swipe)
    return swipe


@router.get("/saved", response_model=list[SavedOutfit])
def get_saved_outfits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedOutfit]:
    """Return outfits the user accepted, most recent first."""
    rows = (
        db.query(SwipeLog, Outfit)
        .join(Outfit, Outfit.id == SwipeLog.outfit_id)
        .filter(
            SwipeLog.user_id == current_user.id,
            SwipeLog.decision == "accepted",
        )
        .order_by(SwipeLog.created_at.desc())
        .all()
    )

    return [
        SavedOutfit(
            outfit_id=outfit.id,
            category=outfit.category,
            color_tags=outfit.color_tags if isinstance(outfit.color_tags, list) else [],
            formality_level=outfit.formality_level,
            swiped_at=swipe.created_at,
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
        .order_by(SwipeLog.created_at.desc())
        .all()
    )
