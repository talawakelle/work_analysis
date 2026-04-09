from datetime import date

from pydantic import BaseModel, Field


class MetaFiltersResponse(BaseModel):
    estates: list[str]
    min_date: date | None
    max_date: date | None
    import_labels: list[str]
    resolved_user: str | None = None
    display_name: str | None = None
    resolved_estate: str | None = None
    accessible_estates: list[str] = Field(default_factory=list)
    accessible_plantations: list[str] = Field(default_factory=list)
    selected_plantation: str | None = None
    role: str = "viewer"
    can_switch_estate: bool = False
    can_upload: bool = False
    access_mode: str = "open"
    access_message: str | None = None
