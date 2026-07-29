from fastapi import HTTPException, status, Depends, APIRouter
from schema import PostCreate, PostUpdate, PostResponse
from sqlalchemy.orm import selectinload
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from sqlalchemy import select
from auth import CurrentUser
import models

router = APIRouter()

# =============================================================================
# ROUTERS & ENDPOINTS: POSTS
# =============================================================================

@router.get("", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Retrieve the list of all posts on the platform, ordered by most recent first.
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
    current_user:CurrentUser, 
    db: Annotated[AsyncSession, 
    Depends(get_db)]
    ):
    """
    Create a new post after verifying that the author (user_id) exists.
    """
    # Create and persist the new post
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=current_user.id
    )

    db.add(new_post)
    await db.commit()
    # Refresh with the author relationship loaded
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Retrieve a single post by its ID, including the author relationship.
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
    current_user:CurrentUser,
    post_data: PostCreate, 
    db: Annotated[AsyncSession, Depends(get_db)]
    ):
    """
    Fully update (PUT) an existing post.
    All fields are required; if the user_id changes, the new user must exist.
    """
    # Check that the post exists
    result = await db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
        
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post."
        )
    
    # Apply the full update
    post.title = post_data.title
    post.content = post_data.content

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int, 
    current_user:CurrentUser,
    post_data: PostUpdate, 
    db: Annotated[AsyncSession, Depends(get_db)]
    ):
    """
    Partially update (PATCH) an existing post.
    Only the fields provided in the request body are modified.
    """
    # Check that the post exists
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
        
    # Check if the user is authorized 
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post."
        )
        
    # Apply only the fields that were provided
    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user:CurrentUser, 
    db: Annotated[AsyncSession, Depends(get_db)]
    ):
    """
    Permanently delete a post by its ID.
    """
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post"
        )
    
    await db.delete(post)
    await db.commit()