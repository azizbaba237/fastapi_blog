"""
Pydantic Schemas for Data Validation and Serialization

This module defines the request/response models for the API endpoints.
It includes schemas for user management (creation, update, public/private views),
authentication tokens, and post management (creation, update, response).

All schemas use Pydantic's built-in validation (Field, EmailStr) and support
ORM object conversion via from_attributes = True.
"""

from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime


# =============================================================================
# USER SCHEMAS
# =============================================================================

class UserBase(BaseModel):
    """
    Base schema for user data with common fields used across multiple operations.

    Attributes:
        username (str): The user's display name. Must be between 1 and 50 characters.
        email (EmailStr): The user's email address. Must be a valid email format
            and at most 120 characters.
    """
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)


class UserCreate(UserBase):
    """
    Schema for creating a new user account.

    Inherits from UserBase and adds the password field.
    The password is hashed before storage, not stored in plain text.

    Attributes:
        password (str): The user's password. Must be at least 8 characters long.
    """
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    """
    Schema for updating an existing user profile (partial updates).

    All fields are optional to support PATCH requests. Only provided fields
    will be updated.

    Attributes:
        username (str | None): New username. Must be between 1 and 50 characters.
        email (EmailStr | None): New email. Must be valid and at most 100 characters.
        image_file (str | None): New profile image filename. Must be at least 1 character.
    """
    username: str | None = Field(min_length=1, max_length=50, default=None)
    email: EmailStr | None = Field(max_length=100, default=None)


class UserPublic(BaseModel):
    """
    Public view of a user (excludes sensitive information like email).

    This schema is used when returning user data to non-owners or in lists.

    Attributes:
        id (int): The user's unique identifier.
        username (str): The user's display name.
        image_file (str | None): The stored filename of the profile image.
        image_path (str): The full URL or path to the profile image.
    """
    model_config = ConfigDict(from_attributes=True)  # Enables ORM object conversion

    id: int
    username: str
    image_file: str | None
    image_path: str


class UserPrivate(UserPublic):
    """
    Private view of a user (includes email, used for the authenticated user).

    Inherits all fields from UserPublic and adds the email field.

    Attributes:
        email (EmailStr): The user's email address.
    """
    email: EmailStr


class Token(BaseModel):
    """
    Authentication token response schema.

    Returned when a user successfully logs in.

    Attributes:
        access_token (str): The JWT access token string.
        token_type (str): The type of token (e.g., "bearer").
    """
    access_token: str
    token_type: str


# =============================================================================
# POST SCHEMAS
# =============================================================================

class PostBase(BaseModel):
    """
    Base schema for post data with common fields.

    Attributes:
        title (str): The post title. Must be between 1 and 100 characters.
        content (str): The post content. Must be at least 1 character.
    """
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class PostCreate(PostBase):
    """
    Schema for creating a new post.

    Inherits all fields from PostBase (title, content).
    The author (user_id) is set automatically from the authenticated user.
    """
    pass


class PostUpdate(BaseModel):
    """
    Schema for updating an existing post (partial updates).

    All fields are optional to support PATCH requests.

    Attributes:
        title (str | None): New title. Must be between 1 and 100 characters.
        content (str | None): New content. Must be at least 1 character.
    """
    title: str | None = Field(min_length=1, max_length=100, default=None)
    content: str | None = Field(min_length=1, default=None)


class PostResponse(PostBase):
    """
    Schema for returning post data in API responses.

    Includes the post's metadata and the author's public information.

    Attributes:
        id (int): The post's unique identifier.
        user_id (int): The ID of the author.
        author (UserPublic): The author's public profile data.
        date_posted (datetime): The timestamp when the post was created.
    """
    model_config = ConfigDict(from_attributes=True)  # Enables ORM object conversion

    id: int
    user_id: int
    author: UserPublic
    date_posted: datetime
    
    
class PaginatedPostsResponse(BaseModel):
    """
    Schema for paginated post responses.

    Used when returning a list of posts with pagination metadata.

    Attributes:
        total (int): Total number of posts available.
        skip (int): Current page number.
        limit (int): Number of posts per page.
        has_more (bool): Indicates if there are more posts available beyond the current page.
        posts (list[PostResponse]): List of post response objects for the current page.
    """
    total: int
    skip: int
    limit: int
    has_more: bool
    posts: list[PostResponse]
    