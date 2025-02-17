import database as db
import fastapi 
import sqlalchemy.orm as orm
import passlib.hash as hash
import models
import schemas as sma
import email_validator as emv
import jwt
from starlette.middleware.cors import CORSMiddleware


JWT_SECRET = "hlsakjdlsjdhlksjdlkashdlsadhkds"

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
    
    user_Object = models.UserModel(
        email=email,
        username=user.username,
        password_hash=hashed_password
        
    )
    db.add(user_Object)
    db.commit()
    db.refresh(user_Object)
    return user_Object


def create_token(user: models.UserModel):
    user_schema = sma.UserResponse.model_validate(user)
    user_dict = user_schema.model_dump()
    
    del user_dict["created_at"]
    
    token = jwt.encode(user_dict, JWT_SECRET)
    
    return dict(access_token=token, token_type="bearer")