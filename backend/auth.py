from datetime import UTC, datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from config import settings
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
import models
import jwt

# =============================================================================
# PASSWORD HASHING
# =============================================================================

# Initialize the password hasher using the recommended algorithm (bcrypt)
password_hash = PasswordHash.recommended()

# OAuth2 scheme for token extraction from the Authorization header
# The tokenUrl must match the login endpoint path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using the configured hashing algorithm.

    Args:
        password (str): The plain-text password to hash.

    Returns:
        str: The hashed password (includes salt and algorithm metadata).
    """
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored hash.

    Args:
        plain_password (str): The plain-text password provided by the user.
        hashed_password (str): The stored password hash.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    return password_hash.verify(plain_password, hashed_password)


# =============================================================================
# JWT TOKEN MANAGEMENT
# =============================================================================

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token with an expiration time.

    The token contains the provided payload (e.g., user ID) and an 'exp' claim
    set to the current time plus the expiration delta.

    Args:
        data (dict): The payload to encode in the token (typically {"sub": user_id}).
        expires_delta (timedelta | None): Optional custom expiration duration.
            If not provided, uses the default from settings.

    Returns:
        str: The encoded JWT token as a string.

    Raises:
        Exception: Any exception raised by the JWT library (e.g., encoding errors).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes,
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def verify_access_token(token: str) -> str | None:
    """
    Verify a JWT access token and extract the subject (user ID).

    The token must contain an 'exp' (expiration) claim and a 'sub' (subject) claim.
    If the token is invalid, expired, or missing required claims, returns None.

    Args:
        token (str): The JWT token to verify.

    Returns:
        str | None: The subject (user ID) as a string if valid, otherwise None.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        # Token is invalid, expired, or malformed
        return None
    else:
        return payload.get("sub")


# =============================================================================
# DEPENDENCY: CURRENT USER
# =============================================================================

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> models.User:
    """
    Dependency that extracts and validates the JWT token, then fetches the user.

    Steps:
        1. Extract the token from the Authorization header.
        2. Verify the token and get the user ID from the 'sub' claim.
        3. Convert the user ID to an integer.
        4. Fetch the user from the database.
        5. Return the user object if all checks pass.

    Args:
        token (str): The JWT token (injected by FastAPI via OAuth2PasswordBearer).
        db (AsyncSession): The database session (injected by FastAPI).

    Returns:
        models.User: The authenticated user object.

    Raises:
        HTTPException 401: If the token is invalid, expired, missing 'sub',
            the user ID is malformed, or the user does not exist in the database.
            In all cases, the WWW-Authenticate header is set to prompt re-authentication.
    """
    # --- Step 1: Verify the token and extract the subject (user ID) ---
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- Step 2: Convert the subject to an integer ---
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- Step 3: Fetch the user from the database ---
    result = await db.execute(
        select(models.User).where(models.User.id == user_id_int),
    )
    user = result.scalars().first()

    # --- Step 4: Ensure the user exists ---
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Type alias for easy dependency injection in route handlers
CurrentUser = Annotated[models.User, Depends(get_current_user)]