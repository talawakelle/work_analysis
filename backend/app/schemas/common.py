from pydantic import BaseModel


class SummaryCard(BaseModel):
    label: str
    value: str | int | float


class WorkCodeSummaryItem(BaseModel):
    work_code: str
    work_name: str
    days: int
    records: int
