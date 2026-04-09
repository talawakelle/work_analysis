from datetime import date, datetime

from pydantic import BaseModel, Field


class CoverageItem(BaseModel):
    plantation: str
    total_estates: int
    estates_with_data: int
    estates_missing_data: int


class FreshnessItem(BaseModel):
    label: str
    value: str | int | float


class ImportHistoryItem(BaseModel):
    id: int
    label: str
    source_filename: str
    created_at: datetime
    rows_processed: int
    status: str
    month_start: date | None = None
    month_end: date | None = None


class AdminOverviewResponse(BaseModel):
    freshness_cards: list[FreshnessItem] = Field(default_factory=list)
    coverage: list[CoverageItem] = Field(default_factory=list)
    recent_imports: list[ImportHistoryItem] = Field(default_factory=list)


class AuditEventResponse(BaseModel):
    id: int
    event_type: str
    actor_username: str | None = None
    actor_display_name: str | None = None
    actor_role: str | None = None
    target_type: str | None = None
    target_value: str | None = None
    details: dict = Field(default_factory=dict)
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse] = Field(default_factory=list)
