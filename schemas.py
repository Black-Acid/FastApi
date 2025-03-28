import pydantic as pdt
from pydantic import Field
from datetime import datetime
from typing import Optional
from enum import Enum
from fastapi import Form


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
    password: str = Field(..., title="Password", description="User's password.")
    
    class Config:
        from_attributes = True

class UserResponse(UserBase):
    
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
        
        

class FarmDetailsPostBase(pdt.BaseModel):
    model_config = pdt.ConfigDict(from_attributes=True)
    
    farm_name: str
    location: str
    

    
class FarmDetailsPostRequest(FarmDetailsPostBase):
    pass    

class FarmDetailsPostResponse(FarmDetailsPostBase):
    id: int
    user_id: int
    rating: int
    verified: bool
    created_at: datetime
    
    
class AddNewProduct(pdt.BaseModel):
    model_config = pdt.ConfigDict(from_attributes=True)
    # Field(..., title="Email", description="The user's email address.")
    farm_id: int
    productName: str
    category: str = Field(..., title="Product Category", description="The category to which the product belongs")
    description: str
    quantity_available: int
    price: float
    
    
    @classmethod
    def as_form(
        cls, 
        productName: str = Form(...), 
        price: float = Form(...), 
        category: str = Form(...), 
        description: str = Form(...),
        quantity_available: int = Form(...),
        farm_id: int = Form(...),
    ):
        return cls(
            productName=productName, 
            farm_id=farm_id,
            price=price, 
            category=category, 
            description=description,
            quantity_available=quantity_available
        )
        
        
        
class CartItem(pdt.BaseModel):
    product_id: int
    order_status: str   
    quantity_purchased_price: float 
    quantity_purchased: float    




class PlaceOrderPost(pdt.BaseModel):
    model_config = pdt.ConfigDict(from_attributes=True)
    # parameters -> farmId, ProductName, Consumer, Quantity, address, order_status, total price
    
    # for every order we will need order_status, address cart 
    # in the cart farm_id, product_id, order_status, quantity purchased, price_of_quantity_purchased
    
    cart_items: CartItem
    address: str
    order_status: str
    

    
    