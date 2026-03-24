from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    singleton_key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, default="default")
    default_search_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    default_source: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    default_filter_text: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    bilibili_cookie: Mapped[str] = mapped_column(Text, nullable=False, default="")
    download_output_dir: Mapped[str] = mapped_column(Text, nullable=False, default="./data/downloads")
    theme: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="zh-CN")
    library_sort: Mapped[str] = mapped_column(String(32), nullable=False, default="recent")
    hide_watched_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)
