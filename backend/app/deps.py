"""Shared FastAPI dependencies: DB session, current user, optional current user."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    """Resolve the bearer token to a User, or raise 401."""
    if not token:
        raise CREDENTIALS_ERROR
    user_id = decode_access_token(token)
    if user_id is None:
        raise CREDENTIALS_ERROR
    user = db.get(User, user_id)
    if user is None:
        raise CREDENTIALS_ERROR
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
