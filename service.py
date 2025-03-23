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
from sqlalchemy import func, desc, extract
from datetime import timedelta, datetime
import shutil
import os


UPLOAD_DIR = "uploads"  # Directory to store images
os.makedirs(UPLOAD_DIR, exist_ok=True) 




JWT_SECRET = "hlsakjdlsjdhlksjdlkashdlsadhkds"
oauth2schema = security.OAuth2PasswordBearer("/api/login")


def create_db():
    return db.Base.metadata.create_all(bind=db.engine)

create_db()

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
    if user.role == "FARMER":
        #post = models.FarmDetails(**post_request.model_dump(), user_id=user.id)
        Newpost = models.FarmDetails(
            farm_name=post_request.farm_name,
            user_id=user.id,
            location=post_request.location,
        )
        db.add(Newpost)
        db.commit()
        db.refresh(Newpost)
    else:
        raise HTTPException(status_code=401, detail="You're not logged in as a Farmer")
    
    return sma.FarmDetailsPostResponse.model_validate(Newpost)


def get_farms_by_user(user: sma.UserResponse, db: orm.Session):
    post = db.query(models.FarmDetails).filter_by(user_id=user.id)
    return list(map(sma.FarmDetailsPostResponse.model_validate, post))



def get_farm_details(farm_id: int, db: orm.Session):
    farm = db.query(models.FarmDetails).filter_by(id=farm_id).first()
    
    if farm is None:
        raise HTTPException(status_code=401, detail="Farm cannot be found")
    
    return sma.FarmDetailsPostResponse.model_validate(farm)


async def add_new_product(
    user_id: int, 
    db: orm.Session, 
    farm_image: fastapi.UploadFile = fastapi.File(...), 
    data: sma.AddNewProduct = fastapi.Depends(sma.AddNewProduct.as_form)
):
    user = db.query(models.UserModel).filter(models.UserModel.id == user_id).first()
    
    if user.role != "FARMER":
        raise HTTPException(status_code=401, detail="You are not a Producer/Farmer")
    
    
    file_location = f"{UPLOAD_DIR}/{farm_image.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(farm_image.file, buffer)
    
    
    new_product = models.FarmProducts(**data.model_dump(), productImage=file_location)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    return {
        "message": "Product added successfully",
        "product": {
            "name": new_product.productName,
            "price": new_product.price,
            "category": new_product.category,
            "image_url": file_location,  # Return the image path
        }
    }
    
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
    
    # Unprocessed Orders and Processed orders
    order_counts = (
        db.query(
            models.OrderItemsModel.order_status,
            func.count(models.OrderItemsModel.id).label("OrderStatus_Count")
        )
        .join(models.FarmProducts, models.OrderItemsModel.product_id == models.FarmProducts.id)
        .join(models.FarmDetails, models.FarmProducts.farm_id == models.FarmDetails.id)
        .filter(models.FarmDetails.user_id == user_id)
        .group_by(models.OrderItemsModel.order_status)
        .all()
    )
    
    order_types = {status: count for status, count in order_counts}
    
    
    
    # New Customers who bought from the week
    week_ago = datetime.now(datetime.UTC) - timedelta(days=7)
    
    total_customers = (
        db.query(func.count(func.distinct(models.OrderItemsModel.user_id)))
        .join(models.FarmProducts, models.OrderItemsModel.product_id == models.FarmProducts.id)  
        .join(models.FarmDetails, models.FarmProducts.farm_id == models.FarmDetails.id)  
        .filter(models.FarmDetails.user_id == user_id)  
        .filter(models.OrderItemsModel.created_at >= week_ago)  # Filter for past week
        .scalar()
    )
    
    # Cumulative profit for the week
    
    monthly_profit = (
            db.query(
            extract('month', models.OrderItemsModel.created_at).label('month'),
            func.sum(models.OrderItemsModel.price_of_purchased_quantity).label('profit')
        )
        .join(models.FarmProducts, models.OrderItemsModel.product_id == models.FarmProducts.id)
        .join(models.FarmDetails, models.FarmProducts.farm_id == models.FarmDetails.id)
        .filter(models.FarmDetails.user_id == user_id)  # Filter by farmer's user_id
        .group_by('month')
        .order_by('month')
        .all()
    )

    # Convert to a dictionary for a chart
    profit_chart_data = {f"{year}-{month:02d}": profit for year, month, profit in monthly_profit}

    #average rating
    # He will make it a dummy data
    

    
    return {
        "Balance": user_balance,
        "total_Orders": total_orders,
        "top_selling_products": final_top_selling,
        "sales_by_category": sales_by_cat,
        "Order_types": order_types,
        "Profit_chart": profit_chart_data,
        "Customers_for_week": total_customers
    }
    
    
async def ordersPage(user_id: int, db: orm.Session):
    orders = (
        db.query(
            models.UserModel.username,  # Name of the customer
            models.FarmProducts.productName,  # Product they are purchasing
            models.OrderItemsModel.order_status,  # Status of their order
            models.OrderItemsModel.quantity_purchased,  # Quantity purchased
            models.OrderModel.created_at,  # Date of order placement
            models.OrderItemsModel.price_of_purchased_quantity,  # Total price of the items
        )
        .join(models.OrderModel, models.OrderModel.id == models.OrderItemsModel.order_id)  
        .join(models.UserModel, models.OrderModel.consumer_id == models.UserModel.id)  # Join with users to get their names
        .join(models.FarmProducts, models.OrderItemsModel.product_id == models.FarmProducts.id)  # Join products
        .join(models.FarmDetails, models.FarmProducts.farm_id == models.FarmDetails.id)  # Link products to farms
        .filter(models.FarmDetails.user_id == user_id)  # Only fetch orders for this farmer
        .all()
    )
    
    
    
    order_details = [
        {
            "customer_name": order.username,
            "product_name": order.productName,
            "order_status": order.order_status,
            "quantity": order.quantity_purchased,
            "order_date": order.created_at.strftime("%Y-%m-%d"),  # Formatting date
            "total_price": order.price_of_purchased_quantity
        }
        for order in orders
    ]
    
    return order_details

    # list of products that has been ordered from this Farmer 
    # Buyer's Name 
    # Product Name
    # Quantity Ordered
    # Date the order was placed
    # Price of the product
    # Status of the product



async def reviewMessages(user_id: int, db: orm.Session):
    
    reviews = (
        db.query(models.ReviewModel)
        .join(models.FarmDetails, models.ReviewModel.farm_id == models.FarmDetails.id)
        .filter(models.FarmDetails.user_id == user_id)
        .all()
    )
    
    
    
    final_review = [
        {
            "customer_name": review.user.username,
            "review_content": review.review_content,
            "review_rate": review.review_rate,
            "avaerage_rating": sum(review.review_rate for review in reviews) / len(reviews) if reviews else 0,
            "total_rates": len(reviews)
        }
        for review in reviews
    ]
    
    return final_review
    # Customer Name
    # Rate
    # Total Rates for USer
    # Average rating
    
    
    
async def StatisticsPage(user_id: int, db: orm.Session):
    pass