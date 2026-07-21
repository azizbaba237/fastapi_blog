from fastapi import FastAPI, HTTPException, Request, status, Depends
from contextlib import asynccontextmanager
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db, engine, Base
import models 
from schema import PostCreate, PostResponse, UserCreate, UserResponse, PostUpdate, UserUpdate

# -----------------------------------------------------------------------------
# CONFIGURATION ET INITIALISATION DE L'APPLICATION
# -----------------------------------------------------------------------------

# Initialisation de la base de données
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup 
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown 
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

# Montage des fichiers statiques et médias
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

# Configuration du moteur de templates HTML
templates = Jinja2Templates(directory="templates")


# =============================================================================
# ROUTEURS & ENDPOINTS : UTILISATEURS (USERS)
# =============================================================================

@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Rendu HTML : Affiche tous les posts d'un utilisateur spécifique.
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
    
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts."}
    )


@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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


@app.get("/api/users/{user_id}", response_model=UserResponse)
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


@app.put("/api/users/{user_id}", response_model=UserResponse)
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
    

@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
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


@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# =============================================================================
# ROUTEURS & ENDPOINTS : ARTICLES (POSTS)
# =============================================================================

@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Rendu HTML : Page d'accueil listant les derniers articles publiés du plus récent au plus ancien.
    """
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).order_by(models.Post.date_posted.desc())
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )


@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Rendu HTML : Page de détail d'un article spécifique via son ID.
    """
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Liste l'ensemble des posts de la plateforme.
    """
    result = await db.execute(select(models.Post).order_by(models.Post.date_posted.desc()))
    posts = result.scalars().all()
    return posts


@app.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Crée un nouveau post en s'assurant que l'auteur (user_id) existe bien.
    """
    result = await db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id
    )
    
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Récupère un post unique par son ID.
    """
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_full(post_id: int, post_data: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Mise à jour complète (PUT) d'un post existant.
    """
    result = await db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )
    post = result.scalars().first()
     
    if not post:
         raise HTTPException(
             status_code=status.HTTP_404_NOT_FOUND, 
             detail="Post not found"
         )
        
    if post_data.user_id != post.user_id:
        result = await db.execute(select(models.User).where(models.User.id == post_data.user_id))
        user = result.scalars().first()
    
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id
    
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post
    

@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_partial(post_id: int, post_data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Mise à jour partielle (PATCH) des champs fournis d'un post.
    """
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
     
    if not post:
         raise HTTPException(
             status_code=status.HTTP_404_NOT_FOUND, 
             detail="Post not found"
         )
    
    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)
    
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post
    

@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    API : Supprime définitivement un post par son ID.
    """
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    await db.delete(post)
    await db.commit()


# =============================================================================
# GESTIONNAIRES D'ERREURS GLOBALES (ERROR HANDLERS)
# =============================================================================

@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    """
    Intercepte les erreurs HTTP génériques. 
    Renvoie du JSON pour les routes API, et une page HTML d'erreur pour le reste.
    """

    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)
    
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    """
    Intercepte les erreurs de validation des schémas de données (Pydantic).
    Renvoie le détail de la validation pour l'API, ou un rendu HTML d'erreur générique.
    """
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )