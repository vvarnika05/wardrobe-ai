from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Outfit(Base):
    __tablename__ = "outfits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    image_url: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    # Kaggle gender label: Men / Women / Boys / Girls / Unisex (catalog department).
    gender: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    style_tags: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    formality_level: Mapped[str | None] = mapped_column(String, nullable=True)
    color_tags: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String, nullable=True)
