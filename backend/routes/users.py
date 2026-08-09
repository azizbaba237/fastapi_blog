from fastapi import HTTPException, status, Depends, APIRouter, UploadFile
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
    CurrentUser,
    hash_password,
    verify_password
)
from config import settings
from PIL import UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from image_utils import process_profile_image, delete_profile_image


# =============================================================================
# ROUTER INSTANCE
# =============================================================================
router = APIRouter()

# =============================================================================
# ENDPOINTS: USER MANAGEMENT
# =============================================================================

@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Create a new user account.

    Validates that the username and email are unique (case-insensitive),
    hashes the password, and stores the user in the database.

    Args:
        user (UserCreate): The user data (username, email, password).
        db (AsyncSession): The database session.

    Returns:
        UserPrivate: The created user object (with password hash excluded).

    Raises:
        HTTPException 400: If the username or email is already taken.
    """
    # --- Check for duplicate username (case-insensitive) ---
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

    # --- Check for duplicate email (case-insensitive) ---
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

    # --- Create and persist the new user ---
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
    Authenticate a user and issue a JWT access token.

    Note: OAuth2PasswordRequestForm uses the "username" field,
    but this endpoint treats it as the user's email address.

    Args:
        form_data (OAuth2PasswordRequestForm): The OAuth2 form containing
            "username" (email) and "password".
        db (AsyncSession): The database session.

    Returns:
        Token: An object containing the access token and token type.

    Raises:
        HTTPException 401: If the email or password is incorrect (generic message
            for security reasons).
    """
    # --- Look up user by email (case-insensitive) ---
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower(),
        ),
    )
    user = result.scalars().first()

    # --- Verify user existence and password validity ---
    # Do not reveal which check failed (security best practice)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- Create access token with user ID as subject ---
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivate)
async def get_current_user(current_user: CurrentUser):
    """
    Retrieve the currently authenticated user's full profile.

    This endpoint uses the injected `CurrentUser` dependency, which validates
    the JWT token and returns the user object.

    Args:
        current_user (User): The authenticated user (injected).

    Returns:
        UserPrivate: The user's private data (including email and image).
    """
    return current_user


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Retrieve public information about a user by their ID.

    This endpoint does not require authentication and only exposes
    public fields (username, image, etc.).

    Args:
        user_id (int): The ID of the user to retrieve.
        db (AsyncSession): The database session.

    Returns:
        UserPublic: The user's public data.

    Raises:
        HTTPException 404: If no user exists with the given ID.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a user's own profile.

    Only the authenticated user can update their own information.
    Ensures that the new username/email, if provided, are unique.

    Args:
        user_id (int): The ID of the user to update.
        user_update (UserUpdate): The fields to update (username, email, image_file).
        current_user (User): The authenticated user (injected).
        db (AsyncSession): The database session.

    Returns:
        UserPrivate: The updated user object.

    Raises:
        HTTPException 403: If the authenticated user does not match the requested user_id.
        HTTPException 404: If the user does not exist.
        HTTPException 400: If the new username or email is already taken.
    """
    # --- Ensure the user can only update their own profile ---
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )

    # --- Fetch the user from the database ---
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # --- Validate username uniqueness if changing ---
    if (
        user_update.username is not None
        and user_update.username.lower() != user.username.lower()
    ):
        result = await db.execute(
            select(models.User).where(
                func.lower(models.User.username) == user_update.username.lower(),
            ),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    # --- Validate email uniqueness if changing ---
    if (
        user_update.email is not None
        and user_update.email.lower() != user.email.lower()
    ):
        result = await db.execute(
            select(models.User).where(
                func.lower(models.User.email) == user_update.email.lower(),
            ),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # --- Apply updates selectively ---
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email.lower()

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Retrieve all posts written by a specific user.

    Only the authenticated user can access their own posts.
    Posts are ordered by most recent first.

    Args:
        user_id (int): The ID of the user whose posts are requested.
        current_user (User): The authenticated user (injected).
        db (AsyncSession): The database session.

    Returns:
        list[PostResponse]: A list of the user's posts, including author details.

    Raises:
        HTTPException 404: If the user does not exist or if the authenticated user
            is not the owner (kept as 404 for security).
    """
    # --- Verify that the authenticated user matches the requested user_id ---
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not authorized to delete this user"
        )

    # --- Check that the user exists ---
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # --- Fetch posts with author relationship eagerly loaded to avoid N+1 queries ---
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
    )
    posts = result.scalars().all()
    return posts


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Delete a user and all of their associated posts.

    Only the authenticated user can delete their own account.
    This operation is irreversible and cascades to all posts.

    Args:
        user_id (int): The ID of the user to delete.
        current_user (User): The authenticated user (injected).
        db (AsyncSession): The database session.

    Raises:
        HTTPException 403: If the authenticated user is not the owner.
        HTTPException 404: If the user does not exist.
    """
    # --- Ensure the user is deleting their own account ---
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )

    # --- Fetch the user ---
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
     
    #  --- Store the old profile picture filename to delete after user deletion ---   
    old_filename = user.image_file

    # --- Delete the user (cascade will remove related posts) ---
    await db.delete(user)
    await db.commit()
    
    # --- Delete the user's profile picture if it exists ---
    if old_filename:
        delete_profile_image(old_filename)
    

@router.patch("/{user_id}/picture", response_model=UserPrivate)
async def upload_profile_picture(
    user_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's picture",
        )

    content = await file.read()

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_bytes // (1024 * 1024)}MB",
        )

    try:
        new_filename = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please upload a valid image (JPEG, PNG, GIF, WebP).",
        ) from err

    old_filename = current_user.image_file

    current_user.image_file = new_filename
    await db.commit()
    await db.refresh(current_user)

    if old_filename:
        delete_profile_image(old_filename)

    return current_user


@router.delete("/{user_id}/picture", response_model=UserPrivate)
async def delete_user_picture(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user's picture",
        )

    old_filename = current_user.image_file

    if old_filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete",
        )

    current_user.image_file = None
    await db.commit()
    await db.refresh(current_user)

    delete_profile_image(old_filename)

    return current_user
