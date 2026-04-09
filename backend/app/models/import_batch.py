from datetime import date, datetime

from sqlalchemy import Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(120), index=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    month_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    month_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    rows_processed: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(40), default="processing")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    work_records = relationship("WorkRecord", back_populates="import_batch")
