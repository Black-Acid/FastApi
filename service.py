import database as db
import fastapi 
import fastapi.security as security
import sqlalchemy.orm as orm
import passlib.hash as hash
import models
import schemas as sma
import email_validator as emv
import jwt
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.cors import CORSMiddleware
from fastapi import HTTPException


JWT_SECRET = "hlsakjdlsjdhlksjdlkashdlsadhkds"
oauth2schema = security.OAuth2PasswordBearer("/api/login")


def create_db():
    return db.Base.metadata.create_all(bind=db.engine)


def get_db():
    database = db.sessionLocal()
    
    try:
        yield database
    finally:
        database.close


def getUserByEmail(email: str, db: orm.Session):
    return db.query(models.UserModel).filter(models.UserModel.email == email).first()

 
def create_user(user: sma.UserRequest, db= orm.Session):
    try:
        emailIsValid = emv.validate_email(user.email)
        email = emailIsValid.email
    except emv.EmailNotValidError:
        raise fastapi.HTTPException(status_code=400, detail="Invalid Email")
    
    
    hashed_password = hash.bcrypt.hash(user.password)
    
    try:
        user_Object = models.UserModel(
            email=email,
            username=user.username,
            password_hash=hashed_password,
            role = user.role,
            address= user.address
        )
        db.add(user_Object)
        db.commit()
        db.refresh(user_Object)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register user due to internal error")
    
    return user_Object


def create_token(user: models.UserModel, db: orm.Session):
    user_schema = sma.UserResponse.model_validate(user)
    db_user = db.query(models.UserModel).filter(models.UserModel.email == user_schema.email).first()
    user_dict = user_schema.model_dump()
    
    del user_dict["created_at"]
    user_dict["role"] = db_user.role.strip()
    
    
    
    token = jwt.encode(user_dict, JWT_SECRET)
    
    return dict(access_token=token, token_type="bearer")


def login(identifier: str, password: str, db: orm.Session):
    user = db.query(models.UserModel).filter(
        (models.UserModel.email == identifier) | (models.UserModel.username == identifier)
    ).first()
    
    if not user:
        return False
    
    if not user.password_verification(password):
        return False
    
    return user



def current_user(db: orm.Session = fastapi.Depends(get_db), token: str = fastapi.Depends(oauth2schema)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        db_user = db.query(models.UserModel).get(payload["id"]) #get User by id which will be decoded from payload along with other details
    except:
        raise fastapi.HTTPException(status_code=401, detail="Invalid creddentials")
    
    return sma.UserResponse.model_validate(db_user)


def create_farm(post_request: sma.FarmDetailsPostRequest, user: sma.UserResponse, db: orm.Session):
    post = models.FarmDetails(**post_request.model_dump(), user_id=user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    
    return sma.FarmDetailsPostResponse.model_validate(post)


def get_farms_by_user(user: sma.UserResponse, db: orm.Session):
    post = db.query(models.FarmDetails).filter_by(user_id=user.id)
    return list(map(sma.FarmDetailsPostResponse.model_validate, post))

def get_farm_details(farm_id: int, db: orm.Session):
    farm = db.query(models.FarmDetails).filter_by(id=farm_id).first()
    
    if farm is None:
        raise HTTPException(status_code=401, detail="Farm cannot be found")
    
    return sma.FarmDetailsPostResponse.model_validate(farm)