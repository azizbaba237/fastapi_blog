from fastapi import HTTPException, status, Depends, APIRouter
from schema import PostCreate, PostUpdate, PostResponse
from sqlalchemy.orm import selectinload
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from sqlalchemy import select
from auth import CurrentUser
import models

# =============================================================================
# ROUTER INSTANCE
# =============================================================================
router = APIRouter()

# =============================================================================
# ENDPOINTS: POST MANAGEMENT
# =============================================================================

@router.get("", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Retrieve a list of all posts on the platform.

    Posts are ordered by most recent first and include the author's information
    via eager loading to avoid N+1 queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        list[PostResponse]: A list of all posts with their authors.
    """
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
    )
    posts = result.scalars().all()
    return posts


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Create a new post for the authenticated user.

    The post author is automatically set to the ID of the current user.

    Args:
        post (PostCreate): The post data (title, content).
        current_user (User): The authenticated user (injected).
        db (AsyncSession): The database session.

    Returns:
        PostResponse: The newly created post, including the author relationship.

    Raises:
        HTTPException 401: If the user is not authenticated (handled by dependency).
    """
    # --- Create and persist the new post ---
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=current_user.id
    )

    db.add(new_post)
    await db.commit()
    # Refresh with the author relationship loaded to return complete data
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Retrieve a single post by its ID.

    The author relationship is eagerly loaded.

    Args:
        post_id (int): The ID of the post to retrieve.
        db (AsyncSession): The database session.

    Returns:
        PostResponse: The requested post with its author.

    Raises:
        HTTPException 404: If no post exists with the given ID.
    """
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if post:
        return post

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found"
    )


@router.put("/{post_id}", response_model=PostResponse)
async def update_post_full(
    post_id: int,
    current_user: CurrentUser,
    post_data: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Fully replace an existing post using the PUT method.

    All fields (title, content) are required and will be overwritten.
    The author cannot be changed; the current user must be the owner.

    Args:
        post_id (int): The ID of the post to update.
        current_user (User): The authenticated user (injected).
        post_data (PostCreate): The complete new post data.
        db (AsyncSession): The database session.

    Returns:
        PostResponse: The updated post with its author.

    Raises:
        HTTPException 404: If the post does not exist.
        HTTPException 403: If the current user is not the owner.
    """
    # --- Check that the post exists ---
    result = await db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # --- Authorization: only the owner can update ---
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post."
        )

    # --- Apply the full update ---
    post.title = post_data.title
    post.content = post_data.content

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int,
    current_user: CurrentUser,
    post_data: PostUpdate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Partially update an existing post using the PATCH method.

    Only the fields provided in the request body are modified.
    The current user must be the owner.

    Args:
        post_id (int): The ID of the post to update.
        current_user (User): The authenticated user (injected).
        post_data (PostUpdate): The partial data to apply (title, content, or both).
        db (AsyncSession): The database session.

    Returns:
        PostResponse: The updated post with its author.

    Raises:
        HTTPException 404: If the post does not exist.
        HTTPException 403: If the current user is not the owner.
    """
    # --- Check that the post exists ---
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # --- Authorization: only the owner can update ---
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post."
        )

    # --- Apply only the fields that were provided ---
    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Permanently delete a post by its ID.

    Only the post owner is allowed to delete it.

    Args:
        post_id (int): The ID of the post to delete.
        current_user (User): The authenticated user (injected).
        db (AsyncSession): The database session.

    Raises:
        HTTPException 404: If the post does not exist.
        HTTPException 403: If the current user is not the owner.
    """
    # --- Check that the post exists ---
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # --- Authorization: only the owner can delete ---
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post"
        )

    await db.delete(post)
    await db.commit()