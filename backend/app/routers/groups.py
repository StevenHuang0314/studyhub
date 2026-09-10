"""CRUD for study groups, plus join/leave membership actions."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.deps import CurrentUser, DbSession
from app.models import GroupMembership, StudyGroup, User
from app.schemas import (
    GroupCreate,
    GroupList,
    GroupRead,
    GroupUpdate,
    MemberRead,
    UserSummary,
)

router = APIRouter(prefix="/api/groups", tags=["study groups"])


def serialize_group(group: StudyGroup, include_members: bool = True) -> GroupRead:
    members = [
        MemberRead(
            id=membership.user.id,
            username=membership.user.username,
            joined_at=membership.joined_at,
        )
        for membership in sorted(group.memberships, key=lambda m: m.joined_at)
    ]
    count = len(members)
    return GroupRead(
        id=group.id,
        name=group.name,
        description=group.description,
        course_code=group.course_code,
        meeting_time=group.meeting_time,
        location=group.location,
        capacity=group.capacity,
        owner=UserSummary.model_validate(group.owner),
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=count,
        is_full=count >= group.capacity,
        members=members if include_members else [],
    )


def _get_group_or_404(db: Session, group_id: int) -> StudyGroup:
    group = db.get(StudyGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study group not found")
    return group


def _require_owner(group: StudyGroup, user: User) -> None:
    if group.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group owner can do that",
        )


def _apply_filters(stmt: Select, search: str | None, course_code: str | None) -> Select:
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(StudyGroup.name.ilike(pattern), StudyGroup.description.ilike(pattern))
        )
    if course_code:
        stmt = stmt.where(StudyGroup.course_code == course_code.strip().upper().replace(" ", ""))
    return stmt


def member_count_subquery():
    """Members per group, so "only groups with space" can be a SQL filter."""
    return (
        select(
            GroupMembership.group_id.label("group_id"),
            func.count(GroupMembership.id).label("member_count"),
        )
        .group_by(GroupMembership.group_id)
        .subquery()
    )


@router.get("", response_model=GroupList)
def list_groups(
    db: DbSession,
    search: str | None = None,
    course_code: str | None = None,
    has_space: Annotated[bool, Query(description="Hide groups that are already full")] = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GroupList:
    counts = member_count_subquery()
    space_left = func.coalesce(counts.c.member_count, 0) < StudyGroup.capacity

    stmt = (
        select(StudyGroup)
        .outerjoin(counts, StudyGroup.id == counts.c.group_id)
        .options(
            selectinload(StudyGroup.owner),
            selectinload(StudyGroup.memberships).selectinload(GroupMembership.user),
        )
        .order_by(StudyGroup.created_at.desc())
    )
    count_stmt = select(func.count(StudyGroup.id)).outerjoin(
        counts, StudyGroup.id == counts.c.group_id
    )
    if has_space:
        # Filtering in SQL rather than in Python keeps `total` honest, so
        # pagination doesn't silently return short pages.
        stmt = stmt.where(space_left)
        count_stmt = count_stmt.where(space_left)

    stmt = _apply_filters(stmt, search, course_code)
    count_stmt = _apply_filters(count_stmt, search, course_code)

    total = db.scalar(count_stmt) or 0
    groups = list(db.scalars(stmt.offset(skip).limit(limit)).all())
    return GroupList(
        items=[serialize_group(group) for group in groups],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, current_user: CurrentUser, db: DbSession) -> GroupRead:
    """Create a group. The creator is added as its first member."""
    group = StudyGroup(
        name=payload.name.strip(),
        description=payload.description.strip(),
        course_code=payload.course_code,
        meeting_time=payload.meeting_time.strip(),
        location=payload.location.strip(),
        capacity=payload.capacity,
        owner_id=current_user.id,
    )
    group.memberships.append(GroupMembership(user_id=current_user.id))
    db.add(group)
    db.commit()
    db.refresh(group)
    return serialize_group(group)


@router.get("/{group_id}", response_model=GroupRead)
def get_group(group_id: int, db: DbSession) -> GroupRead:
    return serialize_group(_get_group_or_404(db, group_id))


@router.patch("/{group_id}", response_model=GroupRead)
def update_group(
    group_id: int, payload: GroupUpdate, current_user: CurrentUser, db: DbSession
) -> GroupRead:
    group = _get_group_or_404(db, group_id)
    _require_owner(group, current_user)

    data = payload.model_dump(exclude_unset=True)
    if data.get("capacity") is not None and data["capacity"] < len(group.memberships):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Capacity cannot be lower than the current member count ({len(group.memberships)})",
        )
    for field, value in data.items():
        if value is not None:
            setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return serialize_group(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, current_user: CurrentUser, db: DbSession) -> Response:
    group = _get_group_or_404(db, group_id)
    _require_owner(group, current_user)
    db.delete(group)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{group_id}/members", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def join_group(group_id: int, current_user: CurrentUser, db: DbSession) -> GroupRead:
    group = _get_group_or_404(db, group_id)

    already_member = any(m.user_id == current_user.id for m in group.memberships)
    if already_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You are already in this group"
        )
    if len(group.memberships) >= group.capacity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This group is full")

    db.add(GroupMembership(group_id=group_id, user_id=current_user.id))
    db.commit()
    db.refresh(group)
    return serialize_group(group)


@router.delete("/{group_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
def leave_group(group_id: int, current_user: CurrentUser, db: DbSession) -> Response:
    group = _get_group_or_404(db, group_id)
    if group.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The owner cannot leave; delete the group instead",
        )

    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == current_user.id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="You are not in this group"
        )
    db.delete(membership)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
