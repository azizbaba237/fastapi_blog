from fastapi import HTTPException, status, Depends, APIRouter
from schema import UserCreate, UserResponse, UserUpdate, PostResponse
from sqlalchemy.orm import selectinload
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from sqlalchemy import select
import models 

router = APIRouter()

# =============================================================================
# ROUTEURS & ENDPOINTS : UTILISATEURS (USERS)
# =============================================================================

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Crée un nouvel utilisateur après vérification de l'unicité du pseudo et de l'email.
    """
    # Vérification du nom d'utilisateur
    result = await db.execute(select(models.User).where(models.User.username == user.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
        
    # Vérification de l'adresse email
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
        
    new_user = models.User(
        username=user.username,
        email=user.email
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Récupère les informations d'un utilisateur par son ID.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    
    if user:
        return user
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )        


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Modifier un utilisateur après vérification de l'unicité du pseudo et de l'email.
    """
    # Vérification si l'utilisateur existe
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalars().first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    # Vérifier l'unicité du nouvel email (seulement s'il a changé)
    if user_data.email != db_user.email :
        email_result = await db.execute(select(models.User).where(models.User.email == user_data.email))
        existing_email = email_result.scalars().first()
        
        # Si on trouve quelqu'un d'autre avec cet email -> Erreur 400 (Bad Request)
        if existing_email :
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exist."
            ) 
            
    # Vérifier l'unicité du nom d'utilsateur (seulement s'il a changé)
    if user_data.username != db_user.username :
        username_result = await db.execute(select(models.User).where(models.User.username == user_data.username))
        existing_username = username_result.scalars().first()
        
        # Si on trouve quelqu'un d'autre avec le meme nom d'utilsateur -> Erreur 400 (Bad Request)
        if existing_username :
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exist."
            )  
    
    update_data = user_data.model_dump(exclude_unset=True)
    
    # On applique dynamiquement les modifications uniquement si elles sont présentes
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
    API : Récupère la liste de tous les posts d'un utilisateur donné.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Supprimer un utilisateur et ses posts de la base de donné".
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    
    if not user :
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await db.delete(user)
    await db.commit()
