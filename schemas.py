import pydantic as pdt
from pydantic import Field
from datetime import datetime
from typing import Optional
from enum import Enum


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    FARMER = "FARMER"
    CONSUMER = "CONSUMER"

class UserBase(pdt.BaseModel):
    model_config = pdt.ConfigDict(from_attributes=True)
    
    username: str = Field(..., title="Username", description="The unique username of the user.")
    email: str = Field(..., title="Email", description="The user's email address.")
    role: RoleEnum = Field(..., title="Role", description="The role of the user. Options: Admin, Consumer, Farmer.")
    address: Optional[str] = Field(None, title="Address", description="The user's address (optional).")
    
class LoginRequest(pdt.BaseModel):
    email: str
    password: str    
    
class UserRequest(UserBase):
    # password: str
    password: str = Field(..., title="Password", description="User's password.")
    
    class Config:
        from_attributes = True

class UserResponse(UserBase):
    # id: int
    # created_at: datetime
    
    id: int = Field(..., title="User ID", description="Unique identifier for the user.")
    created_at: datetime = Field(..., title="Created At", description="Timestamp when the user was created.")
    
    class Config:
        from_attributes = True
        
class PostBase(pdt.BaseModel):
    review_content: str
    created_at: datetime
    
    
class PostRequest(PostBase):
    pass



class PostResponse(PostBase):
    id: int
    user_id : int
    created_at: datetime
    
    class Config:
        from_attributes = True