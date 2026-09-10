"""CRUD for notes (shared study resources) plus their ratings."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.deps import CurrentUser, DbSession
from app.models import Note, Rating, User
from app.schemas import (
    NoteCreate,
    NoteList,
    NoteRead,
    NoteUpdate,
    RatingCreate,
    RatingRead,
    UserSummary,
)

router = APIRouter(prefix="/api/notes", tags=["notes"])

SortOption = Literal["newest", "oldest", "top_rated", "most_rated"]


def rating_summary_subquery():
    """avg score + review count per note, computed in SQL rather than Python."""
    return (
        select(
            Rating.note_id.label("note_id"),
            func.avg(Rating.score).label("average_rating"),
            func.count(Rating.id).label("rating_count"),
        )
        .group_by(Rating.note_id)
        .subquery()
    )


def serialize_note(note: Note, average: float | None, count: int | None) -> NoteRead:
    return NoteRead(
        id=note.id,
        title=note.title,
        content=note.content,
        course_code=note.course_code,
        tags=[tag for tag in note.tags.split(",") if tag],
        resource_url=note.resource_url,
        author=UserSummary.model_validate(note.author),
        created_at=note.created_at,
        updated_at=note.updated_at,
        average_rating=round(float(average), 2) if average is not None else None,
        rating_count=int(count or 0),
    )


def _get_note_or_404(db: Session, note_id: int) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


def _require_author(note: Note, user: User) -> None:
    if note.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only modify your own notes"
        )


def _apply_filters(
    stmt: Select,
    search: str | None,
    course_code: str | None,
    tag: str | None,
    author_id: int | None,
) -> Select:
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(or_(Note.title.ilike(pattern), Note.content.ilike(pattern)))
    if course_code:
        stmt = stmt.where(Note.course_code == course_code.strip().upper().replace(" ", ""))
    if tag:
        stmt = stmt.where(Note.tags.ilike(f"%{tag.strip().lower()}%"))
    if author_id:
        stmt = stmt.where(Note.author_id == author_id)
    return stmt


@router.get("", response_model=NoteList)
def list_notes(
    db: DbSession,
    search: Annotated[str | None, Query(description="Matches title or body text")] = None,
    course_code: Annotated[str | None, Query(description="e.g. CS400")] = None,
    tag: str | None = None,
    author_id: int | None = None,
    sort: SortOption = "newest",
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> NoteList:
    """Browse notes with search, filtering, sorting and pagination."""
    summary = rating_summary_subquery()

    stmt = (
        select(Note, summary.c.average_rating, summary.c.rating_count)
        .outerjoin(summary, Note.id == summary.c.note_id)
        .options(selectinload(Note.author))
    )
    stmt = _apply_filters(stmt, search, course_code, tag, author_id)

    count_stmt = _apply_filters(select(func.count(Note.id)), search, course_code, tag, author_id)
    total = db.scalar(count_stmt) or 0

    order_by = {
        "newest": Note.created_at.desc(),
        "oldest": Note.created_at.asc(),
        # NULLs (unrated notes) sort last in both rating orders.
        "top_rated": func.coalesce(summary.c.average_rating, 0).desc(),
        "most_rated": func.coalesce(summary.c.rating_count, 0).desc(),
    }[sort]
    stmt = stmt.order_by(order_by, Note.id.desc()).offset(skip).limit(limit)

    items = [serialize_note(note, average, count) for note, average, count in db.execute(stmt)]
    return NoteList(items=items, total=total, skip=skip, limit=limit)


@router.get("/courses", response_model=list[str])
def list_course_codes(db: DbSession) -> list[str]:
    """Distinct course codes, for populating the filter dropdown."""
    rows = db.scalars(select(Note.course_code).distinct().order_by(Note.course_code)).all()
    return list(rows)


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, current_user: CurrentUser, db: DbSession) -> NoteRead:
    note = Note(
        title=payload.title.strip(),
        content=payload.content,
        course_code=payload.course_code,
        tags=",".join(payload.tags),
        resource_url=payload.resource_url.strip(),
        author_id=current_user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return serialize_note(note, None, 0)


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note_id: int, db: DbSession) -> NoteRead:
    note = _get_note_or_404(db, note_id)
    stats = db.execute(
        select(func.avg(Rating.score), func.count(Rating.id)).where(Rating.note_id == note_id)
    ).one()
    return serialize_note(note, stats[0], stats[1])


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    note_id: int, payload: NoteUpdate, current_user: CurrentUser, db: DbSession
) -> NoteRead:
    note = _get_note_or_404(db, note_id)
    _require_author(note, current_user)

    data = payload.model_dump(exclude_unset=True)
    if "tags" in data and data["tags"] is not None:
        data["tags"] = ",".join(data["tags"])
    for field, value in data.items():
        if value is not None:
            setattr(note, field, value)
    db.commit()
    db.refresh(note)

    stats = db.execute(
        select(func.avg(Rating.score), func.count(Rating.id)).where(Rating.note_id == note_id)
    ).one()
    return serialize_note(note, stats[0], stats[1])


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, current_user: CurrentUser, db: DbSession) -> Response:
    note = _get_note_or_404(db, note_id)
    _require_author(note, current_user)
    db.delete(note)  # ratings cascade away with it
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# Ratings live under their note
# --------------------------------------------------------------------------


@router.get("/{note_id}/ratings", response_model=list[RatingRead])
def list_ratings(note_id: int, db: DbSession) -> list[Rating]:
    _get_note_or_404(db, note_id)
    stmt = (
        select(Rating)
        .where(Rating.note_id == note_id)
        .options(selectinload(Rating.user))
        .order_by(Rating.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.put("/{note_id}/ratings", response_model=RatingRead)
def rate_note(
    note_id: int, payload: RatingCreate, current_user: CurrentUser, db: DbSession
) -> Rating:
    """Create or replace the caller's rating for a note.

    PUT rather than POST because a user has at most one rating per note, so
    the operation is idempotent — sending it twice leaves the same state.
    """
    note = _get_note_or_404(db, note_id)
    if note.author_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot rate your own note"
        )

    rating = db.scalar(
        select(Rating).where(Rating.note_id == note_id, Rating.user_id == current_user.id)
    )
    if rating is None:
        rating = Rating(note_id=note_id, user_id=current_user.id)
        db.add(rating)
    rating.score = payload.score
    rating.comment = payload.comment.strip()

    db.commit()
    db.refresh(rating)
    return rating


@router.delete("/{note_id}/ratings/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_rating(note_id: int, current_user: CurrentUser, db: DbSession) -> Response:
    rating = db.scalar(
        select(Rating).where(Rating.note_id == note_id, Rating.user_id == current_user.id)
    )
    if rating is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="You have not rated this note"
        )
    db.delete(rating)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
