import datetime as dt
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey)
import sqlalchemy.orm as orm
import passlib.hash as hash

import database as db


class UserModel(db.Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=dt.datetime.now())
    reviews = orm.relationship("ReviewModel", back_populates="user", cascade="all, delete")
    
    
    def password_verification(self, password: str):
        return hash.bcrypt.verify(password, self.password_hash)
    
    
class ReviewModel(db.Base):
    __tablename__ = "Review"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id"))
    review_content = Column(String, index=True)
    created_at = Column(DateTime, default=dt.datetime.now())
    user = orm.relationship("UserModel", back_populates="reviews")
    