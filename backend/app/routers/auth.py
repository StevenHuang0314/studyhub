"""Registration, login and the current-user endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select

from app.deps import CurrentUser, DbSession
from app.models import User
from app.schemas import LoginRequest, Token, UserCreate, UserRead, UserUpdate
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _authenticate(db: DbSession, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    # Always run the hash comparison so a wrong email and a wrong password take
    # about the same time — otherwise the response time leaks which accounts exist.
    if user is None:
        verify_password(password, "$2b$12$" + "x" * 53)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    return user


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession) -> Token:
    """Create an account and return a token, so the client can sign in immediately."""
    email = payload.email.lower()
    existing = db.scalar(
        select(User).where(or_(User.email == email, User.username == payload.username))
    )
    if existing is not None:
        field = "email" if existing.email == email else "username"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"That {field} is already taken"
        )

    user = User(
        email=email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: DbSession) -> Token:
    """JSON login used by the web client."""
    user = _authenticate(db, payload.email, payload.password)
    return Token(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.post("/token", response_model=Token)
def login_form(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    """OAuth2 password-flow login.

    Same thing as /login, but form-encoded, which is what makes the
    "Authorize" button work in the interactive docs at /docs.
    """
    user = _authenticate(db, form_data.username, form_data.password)
    return Token(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserUpdate, current_user: CurrentUser, db: DbSession) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "username" in data and data["username"] != current_user.username:
        taken = db.scalar(select(User).where(User.username == data["username"]))
        if taken is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="That username is already taken"
            )
    for field, value in data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
