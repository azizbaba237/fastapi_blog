from pydantic import BaseModel, ConfigDict, Field 

# Base class for post data
class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=50)
    
# Create class for creating a new post
class PostCreate(PostBase):
    pass

# Response class for returning post data
class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)
    id: int 
    date_posted: str 
    