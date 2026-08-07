from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    style_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_tags: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    color_prefs: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    fit_pref: Mapped[str | None] = mapped_column(String, nullable=True)
    sleeve_pref: Mapped[str | None] = mapped_column(String, nullable=True)
    # Clothing department the user wants to browse — not identity.
    # Allowed: "men" | "women" | "unisex" (nullable for older profiles).
    gender_pref: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
#this file defines the Profile model for the database. It uses SQLAlchemy's ORM to map the Profile class to the profiles table in the database. Each attribute of the class corresponds to a column in the table, with types and constraints defined. The model includes fields for user ID, style description, style tags, color preferences, fit preference, sleeve preference, and timestamps for creation and updates.