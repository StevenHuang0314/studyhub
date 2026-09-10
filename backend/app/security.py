"""Password hashing and JWT creation/verification."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

# bcrypt silently truncates anything past 72 bytes, so do it explicitly.
MAX_PASSWORD_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), hashed_password.encode("utf-8"))
    except ValueError:
        # Raised when the stored value isn't a valid bcrypt hash.
        return False


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    """Sign a JWT whose subject is the user's id."""
    minutes = expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {
        "sub": str(user_id),  # the JWT spec requires `sub` to be a string
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> int | None:
    """Return the user id encoded in the token, or None if it is invalid/expired."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        subject = payload.get("sub")
        if subject is None:
            return None
        return int(subject)
    except (jwt.PyJWTError, TypeError, ValueError):
        return None
