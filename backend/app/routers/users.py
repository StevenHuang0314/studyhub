"""Read-only user profiles and the signed-in user's own dashboard data."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.deps import CurrentUser, DbSession
from app.models import GroupMembership, Note, Rating, StudyGroup, User
from app.routers.groups import serialize_group
from app.routers.notes import serialize_note
from app.schemas import GroupRead, NoteRead, UserRead

router = APIRouter(prefix="/api/users", tags=["users"])


def _notes_for_author(db: Session, author_id: int) -> list[NoteRead]:
    notes = list(
        db.scalars(
            select(Note)
            .where(Note.author_id == author_id)
            .options(selectinload(Note.author))
            .order_by(Note.created_at.desc())
        ).all()
    )
    serialized: list[NoteRead] = []
    for note in notes:
        average, count = db.execute(
            select(func.avg(Rating.score), func.count(Rating.id)).where(Rating.note_id == note.id)
        ).one()
        serialized.append(serialize_note(note, average, count))
    return serialized


@router.get("/me/notes", response_model=list[NoteRead])
def my_notes(current_user: CurrentUser, db: DbSession) -> list[NoteRead]:
    return _notes_for_author(db, current_user.id)


@router.get("/me/groups", response_model=list[GroupRead])
def my_groups(current_user: CurrentUser, db: DbSession) -> list[GroupRead]:
    """Every group the caller belongs to, whether they own it or joined it."""
    groups = list(
        db.scalars(
            select(StudyGroup)
            .join(GroupMembership, GroupMembership.group_id == StudyGroup.id)
            .where(GroupMembership.user_id == current_user.id)
            .options(
                selectinload(StudyGroup.owner),
                selectinload(StudyGroup.memberships).selectinload(GroupMembership.user),
            )
            .order_by(StudyGroup.created_at.desc())
        ).all()
    )
    return [serialize_group(group) for group in groups]


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DbSession) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/{user_id}/notes", response_model=list[NoteRead])
def notes_by_user(user_id: int, db: DbSession) -> list[NoteRead]:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _notes_for_author(db, user_id)
