from datetime import date, datetime

from pydantic import BaseModel, Field


class ImportValidationSheetResponse(BaseModel):
    sheet_name: str
    estate: str | None = None
    rows: int = 0
    missing_columns: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ImportValidationResponse(BaseModel):
    source_filename: str
    validation_message: str | None = None
    validated_period: str | None = None
    validated_rows: int | None = None
    validated_sheets: int | None = None
    validated_estates: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    validation_sheet_results: list[ImportValidationSheetResponse] = Field(default_factory=list)


class ImportBatchResponse(BaseModel):
    id: int
    label: str
    source_filename: str
    month_start: date | None
    month_end: date | None
    rows_processed: int
    status: str
    created_at: datetime
    validation_message: str | None = None
    validated_period: str | None = None
    validated_rows: int | None = None
    validated_sheets: int | None = None
    validated_estates: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    validation_sheet_results: list[ImportValidationSheetResponse] = Field(default_factory=list)


class ImportListResponse(BaseModel):
    items: list[ImportBatchResponse]
