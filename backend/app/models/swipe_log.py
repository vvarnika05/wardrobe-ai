from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SwipeLog(Base):
    __tablename__ = "swipe_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    outfit_id: Mapped[int] = mapped_column(ForeignKey("outfits.id"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)  # accepted / rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
