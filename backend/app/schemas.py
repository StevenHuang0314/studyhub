"""Pydantic models describing every request and response body.

Keeping these separate from the ORM models means the API contract is explicit:
password hashes can never leak into a response, and clients can't set fields
like `author_id` by sending them.
"""

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, field_validator


def _to_utc_iso(value: datetime) -> str:
    """Serialize timestamps as UTC ISO-8601 with a `Z` suffix.

    Timestamps are stored naive-UTC (see models.utcnow). Without the marker,
    `new Date(...)` in the browser would read them as local time.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(_to_utc_iso, return_type=str)]

# --------------------------------------------------------------------------
# Users & auth
# --------------------------------------------------------------------------


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_is_url_safe(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.replace("_", "").replace("-", "").isalnum():
            raise ValueError("username may only contain letters, numbers, hyphens and underscores")
        return cleaned


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    bio: str | None = Field(default=None, max_length=280)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    bio: str
    created_at: UtcDatetime


class UserSummary(BaseModel):
    """Trimmed author/member payload embedded in other responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


# --------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------


class NoteBase(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    content: str = Field(min_length=1)
    course_code: str = Field(min_length=2, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=8)
    resource_url: str = Field(default="", max_length=500)

    @field_validator("course_code")
    @classmethod
    def normalize_course_code(cls, value: str) -> str:
        return value.strip().upper().replace(" ", "")

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for tag in value:
            cleaned = tag.strip().lower()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    """Every field optional — this backs a PATCH, not a PUT."""

    title: str | None = Field(default=None, min_length=3, max_length=160)
    content: str | None = Field(default=None, min_length=1)
    course_code: str | None = Field(default=None, min_length=2, max_length=20)
    tags: list[str] | None = Field(default=None, max_length=8)
    resource_url: str | None = Field(default=None, max_length=500)

    @field_validator("course_code")
    @classmethod
    def normalize_course_code(cls, value: str | None) -> str | None:
        return value.strip().upper().replace(" ", "") if value is not None else None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        seen: list[str] = []
        for tag in value:
            cleaned = tag.strip().lower()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen


class NoteRead(BaseModel):
    id: int
    title: str
    content: str
    course_code: str
    tags: list[str]
    resource_url: str
    author: UserSummary
    created_at: UtcDatetime
    updated_at: UtcDatetime
    average_rating: float | None = None
    rating_count: int = 0


class NoteList(BaseModel):
    """Paginated envelope so the client knows how many results exist in total."""

    items: list[NoteRead]
    total: int
    skip: int
    limit: int


# --------------------------------------------------------------------------
# Ratings
# --------------------------------------------------------------------------


class RatingCreate(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=500)


class RatingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note_id: int
    score: int
    comment: str
    user: UserSummary
    created_at: UtcDatetime
    updated_at: UtcDatetime


# --------------------------------------------------------------------------
# Study groups
# --------------------------------------------------------------------------


class GroupBase(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    course_code: str = Field(min_length=2, max_length=20)
    meeting_time: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    capacity: int = Field(default=8, ge=2, le=100)

    @field_validator("course_code")
    @classmethod
    def normalize_course_code(cls, value: str) -> str:
        return value.strip().upper().replace(" ", "")


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    course_code: str | None = Field(default=None, min_length=2, max_length=20)
    meeting_time: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    capacity: int | None = Field(default=None, ge=2, le=100)

    @field_validator("course_code")
    @classmethod
    def normalize_course_code(cls, value: str | None) -> str | None:
        return value.strip().upper().replace(" ", "") if value is not None else None


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    joined_at: UtcDatetime


class GroupRead(BaseModel):
    id: int
    name: str
    description: str
    course_code: str
    meeting_time: str
    location: str
    capacity: int
    owner: UserSummary
    created_at: UtcDatetime
    updated_at: UtcDatetime
    member_count: int
    is_full: bool
    members: list[MemberRead] = Field(default_factory=list)


class GroupList(BaseModel):
    items: list[GroupRead]
    total: int
    skip: int
    limit: int


class Message(BaseModel):
    detail: str
