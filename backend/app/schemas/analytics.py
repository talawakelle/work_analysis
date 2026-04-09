from datetime import date

from pydantic import BaseModel

from app.schemas.common import SummaryCard, WorkCodeSummaryItem


class EmployeeWorkSummaryItem(BaseModel):
    work_code: str
    work_name: str
    days: int
    kilos: float


class DashboardResponse(BaseModel):
    summary: list[SummaryCard]
    work_code_summary: list[WorkCodeSummaryItem]


class WeeklyPluckingSummaryItem(BaseModel):
    week_label: str
    week_number: int
    weekday_total_kilos: float
    weekend_total_kilos: float
    weekday_days: int
    weekend_days: int
    weekday_avg_kilos: float
    weekend_avg_kilos: float


class WorkAnalysisRow(BaseModel):
    employee_id: int
    employee_no: str
    employee_name: str
    estate: str
    division: str | None
    employment_type: str | None
    total_kilos: float
    total_days: int
    avg_kilos_per_day: float
    row_color: str


class WorkAnalysisResponse(BaseModel):
    summary: list[SummaryCard]
    work_code_summary: list[WorkCodeSummaryItem]
    weekly_plucking: list[WeeklyPluckingSummaryItem]
    rows: list[WorkAnalysisRow]


class EmployeeSearchItem(BaseModel):
    employee_id: int
    employee_no: str
    employee_name: str
    estate: str
    division: str | None


class CalendarDay(BaseModel):
    date: date
    kilos: float
    worked: bool
    work_hour: float | None
    work_code: str | None
    work_name: str | None
    employment_type: str | None
    division: str | None
    field_code: str | None
    gang: str | None
    plantation: str | None
    crop: str | None
    hectare: float | None
    gender: str | None
    color: str


class DailyRecord(BaseModel):
    date: date
    division: str | None
    plantation: str | None
    crop: str | None
    field_code: str | None
    gang: str | None
    kilos: float
    work_hour: float | None
    hectare: float | None
    work_code: str | None
    work_name: str | None
    employment_type: str | None
    gender: str | None


class EmployeeProfile(BaseModel):
    employee_id: int
    employee_no: str
    employee_name: str
    estate: str
    gender: str | None
    primary_division: str | None
    primary_gang: str | None


class AttendanceSummary(BaseModel):
    present_days: int
    absent_days: int
    total_days: int


class PluckingKiloShare(BaseModel):
    division: str | None
    division_plucking_kilos: float
    employee_plucking_kilos: float
    other_division_plucking_kilos: float


class EmployeeDetailResponse(BaseModel):
    employee: EmployeeProfile
    period: str
    summary: list[SummaryCard]
    work_code_summary: list[WorkCodeSummaryItem]
    work_summary: list[EmployeeWorkSummaryItem]
    attendance: AttendanceSummary
    plucking_kilo_share: PluckingKiloShare
    calendar: list[CalendarDay]
    records: list[DailyRecord]
