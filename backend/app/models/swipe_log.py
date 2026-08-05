from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SwipeLog(Base):
    __tablename__ = "swipe_logs"
    __table_args__ = (
        # One swipe record per user+outfit; re-swipes update this row.
        UniqueConstraint("user_id", "outfit_id", name="uq_swipe_logs_user_outfit"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    outfit_id: Mapped[int] = mapped_column(ForeignKey("outfits.id"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)  # accepted / rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Bumped on every re-swipe so "most recent" ordering stays correct.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
