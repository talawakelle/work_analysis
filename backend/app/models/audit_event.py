from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    actor_username: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    actor_display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    target_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
