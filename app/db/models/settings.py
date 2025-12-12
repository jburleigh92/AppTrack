from datetime import datetime
from sqlalchemy import Integer, Boolean, CheckConstraint, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class Settings(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    email_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    llm_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    auto_analyze: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_singleton"),
    )
