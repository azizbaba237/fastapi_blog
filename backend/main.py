"""
FastAPI Application Entry Point

This module initializes the FastAPI application, configures static file serving,
template rendering, database lifecycle management, and includes all route routers.
It also defines HTML page routes (home, post detail, user posts, login, register, account)
and global exception handlers for both API and HTML responses.
"""

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
from sqlalchemy import select, func
from database import get_db, engine
import models
from routes import users, posts
from config import settings



# =============================================================================
# APPLICATION LIFECYCLE MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Context manager for application startup and shutdown events.

    Startup:
        Creates all database tables if they do not already exist.
    Shutdown:
        Disposes the database connection pool to release resources cleanly.

    Args:
        _app (FastAPI): The FastAPI application instance (unused but required).

    Yields:
        None
    """
    # --- Startup ---
    # async with engine.begin() as conn:
    #     # Create tables based on SQLAlchemy models
    #     await conn.run_sync(Base.metadata.create_all)
    yield
    # --- Shutdown ---
    await engine.dispose()


# =============================================================================
# FASTAPI APPLICATION INSTANCE
# =============================================================================

app = FastAPI(lifespan=lifespan)

# --- Static Files ---
# Mount directories for serving CSS, JavaScript, images, and user-uploaded media
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

# --- Template Engine ---
# Configure Jinja2 to render HTML templates from the 'templates' folder
templates = Jinja2Templates(directory="templates")


# =============================================================================
# ROUTER INCLUSION
# =============================================================================

# Include API routers with their respective prefixes and tags
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])


# =============================================================================
# HTML PAGE ROUTES
# =============================================================================

@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Home page displaying all posts ordered by most recent first.

    This route serves the main landing page and the /posts endpoint.
    Posts include their author relationship via eager loading.

    Args:
        request (Request): The HTTP request object.
        db (AsyncSession): The database session (injected).

    Returns:
        TemplateResponse: Rendered home.html with the list of posts.
    """
    result_count = await db.execute(select(func.count()).select_from(models.Post))
    total = result_count.scalar() or 0
    
    # Fetch all posts with authors, ordered by date (newest first)
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .limit(settings.post_per_page)  # Limit to configured number of posts per page
    )
    all_posts = result.scalars().all()
    
    has_more = len(all_posts) < total  # Determine if there are more posts than displayed
    
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": all_posts,
         "title": "Home",
         "limit": settings.post_per_page,
         "has_more": has_more
         },
        
    )


@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Detail page for a single post, identified by its ID.

    Args:
        request (Request): The HTTP request object.
        post_id (int): The ID of the post to display.
        db (AsyncSession): The database session (injected).

    Returns:
        TemplateResponse: Rendered post.html with the post data.

    Raises:
        HTTPException 404: If no post exists with the given ID.
    """
    # Fetch the post with its author relationship
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if post:
        title = post.title[:50]  # Truncate for <title> tag
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Page displaying all posts written by a specific user.

    Args:
        request (Request): The HTTP request object.
        user_id (int): The ID of the user whose posts are to be shown.
        db (AsyncSession): The database session (injected).

    Returns:
        TemplateResponse: Rendered user_posts.html with the user and their posts.

    Raises:
        HTTPException 404: If the user does not exist.
    """
    # Fetch the user first to ensure they exist
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Fetch the user's posts with author relationship, ordered by date
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )


# =============================================================================
# AUTHENTICATION PAGES (LOGIN, REGISTER, ACCOUNT)
# =============================================================================

@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    """
    Login page – serves the login form.

    Args:
        request (Request): The HTTP request object.

    Returns:
        TemplateResponse: Rendered login.html.
    """
    return templates.TemplateResponse(
        request,
        "login.html",
        {"title": "Login"},
    )


@app.get("/register", include_in_schema=False)
async def register_page(request: Request):
    """
    Registration page – serves the sign-up form.

    Args:
        request (Request): The HTTP request object.

    Returns:
        TemplateResponse: Rendered register.html.
    """
    return templates.TemplateResponse(
        request,
        "register.html",
        {"title": "Register"},
    )


@app.get("/account", include_in_schema=False)
async def account_page(request: Request):
    """
    Account settings page – displays user profile management interface.

    Args:
        request (Request): The HTTP request object.

    Returns:
        TemplateResponse: Rendered account.html.
    """
    return templates.TemplateResponse(
        request,
        "account.html",
        {"title": "Account"},
    )


# =============================================================================
# PASSWORD MANAGEMENT (FORGOT-PASSWORD, RESET-PASSWORD)
# =============================================================================

@app.get("/forgot-password", include_in_schema=False)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"title": "Forgot Password"},
    )

@app.get("/reset-password", include_in_schema=False)
async def reset_password_page(request: Request):
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        {"title": "Reset Password"},
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# =============================================================================
# GLOBAL ERROR HANDLERS
# =============================================================================

@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    """
    Handles generic HTTP exceptions (e.g., 404, 500).

    For API routes (starting with /api), returns a JSON response using the
    default FastAPI handler. For HTML routes, renders a custom error page.

    Args:
        request (Request): The HTTP request that triggered the exception.
        exception (StarletteHTTPException): The caught exception.

    Returns:
        Response: JSON error for API routes, or HTML template response for others.
    """
    # API routes return JSON error responses
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    # HTML routes render a user-friendly error page
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
    Handles Pydantic validation errors (e.g., malformed request bodies).

    For API routes, returns a JSON error with validation details.
    For HTML routes, renders a generic error page.

    Args:
        request (Request): The HTTP request that triggered the exception.
        exception (RequestValidationError): The validation error details.

    Returns:
        Response: JSON validation errors for API, or HTML error page for others.
    """
    # API routes return structured validation error details
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    # HTML routes show a simple error message
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