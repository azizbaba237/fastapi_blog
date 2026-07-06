from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime 


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email : EmailStr = Field(max_length=120)


class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int 
    image_file: str | None 
    image_path: str 



# Base class for post data
class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    
# Create class for creating a new post
class PostCreate(PostBase):
    user_id: int # for testing 

# Response class for returning post data
class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)
    id: int 
    user_id: int
    author: UserResponse
    date_posted: datetime
    