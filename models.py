import datetime as dt
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Enum as Saenum, func)
import sqlalchemy.orm as orm
from sqlalchemy.orm import validates 
import passlib.hash as hash
from enum import Enum
import database as db


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    FARMER = "FARMER"
    CONSUMER = "CONSUMER"


class UserModel(db.Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(
        Saenum(RoleEnum, name="roleenum"), 
        nullable=False,
        default=RoleEnum.CONSUMER          # Use the correctly cased enum member
    )
    address = Column(String)
    created_at = Column(DateTime, default=dt.datetime.now())
    updated_at = Column(DateTime, default=func.now())
    reviews = orm.relationship("ReviewModel", back_populates="user", cascade="all, delete")
    farms = orm.relationship("FarmDetails", back_populates="user", cascade="all, delete")
    orders = orm.relationship("OrderModel", back_populates="consumer", cascade="all, delete")
    transactions = orm.relationship("TransactionModel", back_populates="user", cascade="all, delete")
    
    
    
    def password_verification(self, password: str):
        return hash.bcrypt.verify(password, self.password_hash)
    
    

    
    
    
class FarmDetails(db.Base):
    __tablename__ = "Farms"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id"))
    farm_name = Column(Integer)
    location = Column(String)
    farm_image = Column(String)
    rating = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    user = orm.relationship("UserModel", back_populates="farms", cascade="all, delete")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    products = orm.relationship("FarmProducts", back_populates="farmer", cascade="all, delete")
    reviews = orm.relationship("ReviewModel", back_populates="farm", cascade="all, delete")
    
    
    @validates("user")
    def validate_farmer(self, key, user):
        if user.role != RoleEnum.FARMER:
            raise ValueError("Associated User must be a farmer")
        return user
    
    
class FarmProducts(db.Base):
    __tablename__ = "Farm_Products"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("Farms.id"))
    category = Column(String)
    description = Column(String)
    quantity_available = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    farmer = orm.relationship("FarmDetails", back_populates="products", cascade="all, delete")
    
    
class OrderModel(db.Base):
    __tablename__ = "Orders_Made"
    id = Column(Integer, primary_key=True)
    consumer_id = Column(Integer, ForeignKey("User.id"))
    order_status = Column(String)
    shipping_address = Column(String)
    order_date = Column(DateTime)
    delivery_date = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    consumer = orm.relationship("UserModel", back_populates="orders", cascade="all, delete")
    order_items = orm.relationship("OrderItemsModel", back_populates="order", cascade="all, delete")
    
    
    def validate_consumer(self, key, consumer_id):
        session = db.sessionLocal()  # Create a new session
        try:
            user = session.get(UserModel, consumer_id)  # Fetch user from DB
            if user and user.role != RoleEnum.CONSUMER:
                raise ValueError("Associated User must be a Consumer")
            return consumer_id
        finally:
            session.close() 
    
    
class OrderItemsModel(db.Base):
    __tablename__ = "Items_Ordered"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("Orders_Made.id"))
    product_id = Column(Integer, ForeignKey("Farm_Products.id"))
    quantity_purchased = Column(Integer)
    price_of_purchased_quantity = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    order = orm.relationship("OrderModel", back_populates="order_items", cascade="all, delete")
    
    
class TransactionModel(db.Base):
    __tablename__ = "Transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id"))
    order_id = Column(Integer, ForeignKey("Orders_Made.id"))
    amount_paid = Column(Float)
    payment_method = Column(String)
    payment_status = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    user = orm.relationship("UserModel", back_populates="transactions", cascade="all, delete")
    
    
class ReviewModel(db.Base):
    __tablename__ = "Review"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id"))
    farm_id = Column(Integer, ForeignKey("Farms.id"))
    review_content = Column(String, index=True)
    created_at = Column(DateTime, default=dt.datetime.now())
    user = orm.relationship("UserModel", back_populates="reviews")
    farm = orm.relationship("FarmDetails", back_populates="reviews", cascade="all, delete")