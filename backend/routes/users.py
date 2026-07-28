from fastapi import HTTPException, status, Depends, APIRouter
from schema import UserCreate, UserUpdate, PostResponse, UserPublic, UserPrivate, Token
from sqlalchemy.orm import selectinload
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from sqlalchemy import select, func
import models
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from auth import (
    create_access_token,
    hash_password,
    oauth2_scheme,
    verify_password,
    verify_access_token
)
from config import settings

router = APIRouter()

# =============================================================================
# ROUTERS & ENDPOINTS: USERS
# =============================================================================

@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Create a new user after verifying that the username and email are unique.
    """
    # Check if username already exists (case-insensitive)
    result = await db.execute(
        select(models.User).
        where(func.lower(models.User.username) == user.username.lower())
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email already exists (case-insensitive)
    result = await db.execute(
        select(models.User)
        .where(func.lower(models.User.email) == user.email.lower())
    )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Create and persist the new user
    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Authenticate a user and return a JWT access token.
    Note: OAuth2PasswordRequestForm uses the "username" field, but we treat it as email.
    """
    # Look up user by email (case-insensitive)
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower(),
        ),
    )
    user = result.scalars().first()

    # Verify user exists and password is correct
    # Do not reveal which check failed (security best practice)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivate)
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the currently authenticated user from the JWT token."""
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate that user_id is a valid integer (defense against malformed JWT)
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(models.User).where(models.User.id == user_id_int),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Retrieve public information for a user by their ID.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.put("/{user_id}", response_model=UserPrivate)
async def update_user(user_id: int, user_data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Update a user after verifying uniqueness of the new username and/or email (if changed).
    """
    # Check that the user exists
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalars().first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check uniqueness of the new email (only if it has changed)
    if user_data.email != db_user.email:
        email_result = await db.execute(
            select(models.User)
            .where(func.lower(models.User.email) == user_data.email.lower())
        )
        existing_email = email_result.scalars().first()

        # Another user already has this email -> 400 Bad Request
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists."
            )

    # Check uniqueness of the new username (only if it has changed)
    if user_data.username != db_user.username:
        username_result = await db.execute(
            select(models.User)
            .where(func.lower(models.User.username) == user_data.username.lower())
        )
        existing_username = username_result.scalars().first()

        # Another user already has this username -> 400 Bad Request
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists."
            )

    # Apply only the fields that were provided in the request
    update_data = user_data.model_dump(exclude_unset=True)

    if "username" in update_data and update_data["username"] is not None:
        db_user.username = update_data["username"]

    if "email" in update_data and update_data["email"] is not None:
        db_user.email = update_data["email"]

    if "image_file" in update_data and update_data["image_file"] is not None:
        db_user.image_file = update_data["image_file"]

    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Retrieve all posts belonging to a given user, ordered by most recent first.
    """
    # Ensure the user exists
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Fetch posts with their author relationship eagerly loaded
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
    )
    posts = result.scalars().all()
    return posts


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Delete a user and all of their associated posts from the database.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    await db.delete(user)
    await db.commit()