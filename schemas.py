import pydantic as pdt
from datetime import datetime

class UserBase(pdt.BaseModel):
    model_config = pdt.ConfigDict(from_attributes=True)
    username: str
    email: str
    
    
class UserRequest(UserBase):
    password: str
    
    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
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