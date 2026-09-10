"""SQLAlchemy ORM models.

Schema overview:
    User  1---N Note        (a user authors many notes)
    User  1---N Rating      (a user rates many notes, at most once each)
    Note  1---N Rating
    User  N---M StudyGroup  (through GroupMembership)
"""

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    """Naive UTC timestamp.

    SQLite drops the offset from timezone-aware values, so storing naive UTC
    everywhere keeps reads and writes consistent (no mixing aware and naive
    datetimes). The API layer re-attaches the UTC marker on the way out — see
    `UtcDatetime` in schemas.py.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str] = mapped_column(String(280), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    notes: Mapped[list["Note"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    ratings: Mapped[list["Rating"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    owned_groups: Mapped[list["StudyGroup"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User {self.id} {self.username}>"


class Note(Base):
    """A shared study resource: lecture notes, a cheat sheet, a problem set walkthrough."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    course_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    # Stored as a comma-separated string so SQLite stays a single-file DB.
    # The API exposes it as a JSON array (see schemas.NoteRead).
    tags: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resource_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    author: Mapped["User"] = relationship(back_populates="notes")
    ratings: Mapped[list["Rating"]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Note {self.id} {self.title!r}>"


class Rating(Base):
    """A 1-5 star review of a note. One per user per note, enforced in the DB."""

    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("note_id", "user_id", name="uq_rating_note_user"),
        CheckConstraint("score >= 1 AND score <= 5", name="ck_rating_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    note: Mapped["Note"] = relationship(back_populates="ratings")
    user: Mapped["User"] = relationship(back_populates="ratings")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Rating note={self.note_id} user={self.user_id} score={self.score}>"


class StudyGroup(Base):
    __tablename__ = "study_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    course_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    meeting_time: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="owned_groups")
    memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )

    @property
    def member_count(self) -> int:
        return len(self.memberships)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StudyGroup {self.id} {self.name!r}>"


class GroupMembership(Base):
    """Association row joining users to study groups."""

    __tablename__ = "group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_membership_group_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("study_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    group: Mapped["StudyGroup"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<GroupMembership group={self.group_id} user={self.user_id}>"


__all__ = ["GroupMembership", "Note", "Rating", "StudyGroup", "User", "utcnow"]
