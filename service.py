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
from sqlalchemy import func, desc


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
    # the line below to to find the user's role if it was not added but I think I ca improve it
    db_user = db.query(models.UserModel).filter(models.UserModel.email == user_schema.email).first()
    user_dict = user_schema.model_dump()
    
    del user_dict["created_at"]
    #since the role has now become a mandated field then it means this line will become redundant
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


async def add_new_product(data: sma.AddNewProduct, db: orm.Session):
    product = db.query(models.FarmProducts).get(data.productName)
    
    # Masa come back here don't we need to know the farmer that is adding the product
    
    if product:
        raise HTTPException(status_code=401, detail="This Product already exists")
    
    new_product = models.FarmProducts(**data.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    
async def dashboardStuffs(user_id: int, db: orm.Session):
    user = db.query(models.UserBalance).filter_by(user_id=user_id)
    # Total balance in user's Account
    user_balance = user.order_by(models.UserBalance.last_update.desc()).first()
    
    # Total orders placed to that particular farmer
    total_orders = (
        db.query(func.count(models.FarmProducts.id))
        .join(models.FarmDetails, models.FarmDetails.id == models.FarmProducts.farm_id)
        .filter(models.FarmDetails.user_id == user_id)
        .scalar()
    )
    
    
    # top selling Products
    top_selling = (
        db.query(
            models.FarmProducts.productName,
            (models.FarmProducts.initial_quantity - models.FarmProducts.quantity_available).label("total_sold")
        )
        .join(models.FarmDetails, models.FarmDetails.id == models.FarmProducts.farm_id)
        .filter(models.FarmDetails.user_id == user_id)
        .order_by(desc("total_sold"))
        .limit(4)
        .all()
    )
    
    final_top_selling = {product.productName: product.total_sold for product in top_selling}
    
    
    sales_by_category = (
        db.query(
            models.FarmProducts.category,
            func.sum(models.FarmProducts.initial_quantity - models.FarmProducts.quantity_available).label("total_sold")
        )
        .join(models.FarmDetails, models.FarmDetails.id == models.FarmProducts.farm_id)
        .filter(models.FarmDetails.user_id == user_id)
        .group_by(models.FarmProducts.category)
        .all()
    )
    
    total_sales = sum(sold for _, sold in sales_by_category)
    
    sales_by_cat = {category: (sold / total_sales) * 100 for category, sold in sales_by_category} if total_sales else {}
    
    
    return {
        "Balance": user_balance,
        "total_Orders": total_orders,
        "top_selling_products": final_top_selling,
        "sales_by_category": sales_by_cat
    }
    
    
async def ordersPage(user_id: int, db: orm.Session):
    # list of products that has been ordered from this Farmer 
    # Buyer's Name 
    # Product Name
    # Quantity Ordered
    # Date the order was placed
    # Price of the product
    # Status of the product
    pass