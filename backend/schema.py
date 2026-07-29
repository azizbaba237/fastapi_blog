from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime 

# Base class for user data
class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email : EmailStr = Field(max_length=120)

class UserCreate(UserBase):
    password: str = Field(min_length= 8)

class UserUpdate(BaseModel):
    username: str | None = Field(min_length=1, max_length=50, default=None)
    email: EmailStr | None = Field(max_length=100, default=None)
    image_file: str | None = Field(default=None, min_length=1, max_length=200)

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username:str 
    image_file: str | None 
    image_path: str 
    
class UserPrivate(UserPublic):
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str

# Base class for post data
class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    
# Create class for creating a new post
class PostCreate(PostBase):
    pass
    
# Update class for updating an existing post
class PostUpdate(BaseModel):
    title: str | None = Field(min_length=1, max_length=100, default=None)
    content: str | None = Field(min_length=1, default=None)

# Response class for returning post data
class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)
    id: int 
    user_id: int
    author: UserPublic
    date_posted: datetime
    