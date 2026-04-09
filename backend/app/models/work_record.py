from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WorkRecord(Base):
    __tablename__ = "work_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), index=True)
    estate_id: Mapped[int] = mapped_column(ForeignKey("estates.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)

    division: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    plantation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    crop: Mapped[str | None] = mapped_column(String(80), nullable=True)
    field_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    hectares_plucked: Mapped[float | None] = mapped_column(Float, nullable=True)
    gang: Mapped[str | None] = mapped_column(String(120), nullable=True)
    work_hour: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    work_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    work_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    weighing_date: Mapped[date] = mapped_column(Date, index=True)
    kilos: Mapped[float] = mapped_column(Float, default=0)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)

    estate = relationship("Estate", back_populates="work_records")
    employee = relationship("Employee", back_populates="work_records")
    import_batch = relationship("ImportBatch", back_populates="work_records")
