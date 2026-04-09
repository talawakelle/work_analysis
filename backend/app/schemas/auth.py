from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    username: str
    display_name: str | None = None
    resolved_estate: str | None = None
    accessible_estates: list[str] = Field(default_factory=list)
    accessible_plantations: list[str] = Field(default_factory=list)
    selected_plantation: str | None = None
    role: str = "viewer"
    can_upload: bool = False
    can_switch_estate: bool = False
    access_mode: str = "locked"
    access_message: str | None = None


class AccessConfigUploadResponse(BaseModel):
    source_filename: str
    estates_count: int
    estate_user_count: int
    plantation_codes: list[str] = Field(default_factory=list)
    users_count: int
    message: str
    warnings: list[str] = Field(default_factory=list)
