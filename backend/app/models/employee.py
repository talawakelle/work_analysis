from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (UniqueConstraint("estate_id", "employee_no", name="uq_employee_estate_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    estate_id: Mapped[int] = mapped_column(ForeignKey("estates.id"), index=True)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    employee_name: Mapped[str] = mapped_column(String(200), index=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gang: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    estate = relationship("Estate", back_populates="employees")
    work_records = relationship("WorkRecord", back_populates="employee")
