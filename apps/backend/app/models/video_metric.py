from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VideoMetric(Base):
    __tablename__ = "video_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False, unique=True, index=True)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    favorite_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coin_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reply_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_at: Mapped[str] = mapped_column(String(64), nullable=False)

    video: Mapped["Video"] = relationship("Video", back_populates="metrics")
