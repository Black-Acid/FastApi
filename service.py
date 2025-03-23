import database as db
import fastapi 
import fastapi.security as security
import sqlalchemy.orm as orm
import passlib.hash as hash
import models
from models import * 
import schemas as sma
import email_validator as emv
import jwt
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from sqlalchemy import func, desc, extract
from datetime import timedelta, datetime, timezone
import shutil
import os


UPLOAD_DIR = "uploads"  # Directory to store images
os.makedirs(UPLOAD_DIR, exist_ok=True) 




JWT_SECRET = "hlsakjdlsjdhlksjdlkashdlsadhkds"
oauth2schema = security.OAuth2PasswordBearer("/api/login")



def get_total_orders():
    pass


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
    return db.query(UserModel).filter(UserModel.email == email).first()

 
def create_user(user: sma.UserRequest, db= orm.Session):
    try:
        emailIsValid = emv.validate_email(user.email)
        email = emailIsValid.email
    except emv.EmailNotValidError:
        raise fastapi.HTTPException(status_code=400, detail="Invalid Email")
    
    
    hashed_password = hash.bcrypt.hash(user.password)
    
    try:
        user_Object = UserModel(
            email=email,
            username=user.username,
            password_hash=hashed_password,
            role = user.role,
            address= user.address
        )
        db.add(user_Object)
        db.commit()
        db.refresh(user_Object)
        
        
        if user_Object.role == "FARMER":
            user_balance = models.UserBalance(
                user_id=user_Object.id,
                balance=0.00
            )
            db.add(user_balance)
            db.commit()
            db.refresh(user_balance)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to register user {str(e)}")
    
    return user_Object


def create_token(user: UserModel, db: orm.Session):
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
    user = db.query(UserModel).filter(
        (UserModel.email == identifier) | (UserModel.username == identifier)
    ).first()
    
    if not user:
        return False
    
    if not user.password_verification(password):
        return False
    
    return user



def current_user(db: orm.Session = fastapi.Depends(get_db), token: str = fastapi.Depends(oauth2schema)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        db_user = db.query(UserModel).get(payload["id"]) #get User by id which will be decoded from payload along with other details
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
    post = db.query(FarmDetails).filter_by(user_id=user.id)
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
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if user.role != "FARMER":
        raise HTTPException(status_code=401, detail="You are not a Producer/Farmer")
    
    
    file_location = f"{UPLOAD_DIR}/{farm_image.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(farm_image.file, buffer)
    
    
    new_product = FarmProducts(**data.model_dump(), productImage=file_location)
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
    user = db.query(UserBalance).filter_by(user_id=user_id)
    # Total balance in user's Account
    user_balance = user.order_by(UserBalance.last_update.desc()).first()
    
    # Total orders placed to that particular farmer
    total_orders = (
        db.query(func.count(FarmProducts.id))
        .join(FarmDetails, FarmDetails.id == FarmProducts.farm_id)
        .filter(FarmDetails.user_id == user_id)
        .scalar()
    )
    
    
    
    
    
    
    # top selling Products
    top_selling = (
        db.query(
            FarmProducts.productName,
            (FarmProducts.initial_quantity - FarmProducts.quantity_available).label("total_sold")
        )
        .join(FarmDetails, FarmDetails.id == FarmProducts.farm_id)
        .filter(FarmDetails.user_id == user_id)
        .order_by(desc("total_sold"))
        .limit(4)
        .all()
    )
    
    final_top_selling = {product.productName: product.total_sold for product in top_selling}
    
    
    sales_by_category = (
        db.query(
            FarmProducts.category,
            func.sum(FarmProducts.initial_quantity - FarmProducts.quantity_available).label("total_sold")
        )
        .join(FarmDetails, FarmDetails.id == FarmProducts.farm_id)
        .filter(FarmDetails.user_id == user_id)
        .group_by(FarmProducts.category)
        .all()
    )
    
    total_sales = sum(sold for _, sold in sales_by_category)
    
    sales_by_cat = {category: (sold / total_sales) * 100 for category, sold in sales_by_category} if total_sales else {}
    
    # Unprocessed Orders and Processed orders
    order_counts = (
        db.query(
            OrderItemsModel.order_status,
            func.count(OrderItemsModel.id).label("OrderStatus_Count")
        )
        .join(FarmProducts, OrderItemsModel.product_id == FarmProducts.id)
        .join(FarmDetails, FarmProducts.farm_id == FarmDetails.id)
        .filter(FarmDetails.user_id == user_id)
        .group_by(OrderItemsModel.order_status)
        .all()
    )
    
    order_types = {status: count for status, count in order_counts}
    
    
    
    # New Customers who bought from the week
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    total_customers = (
        db.query(func.count(func.distinct(OrderItemsModel.consumer)))
        .join(FarmProducts, OrderItemsModel.product_id == FarmProducts.id)  
        .join(FarmDetails, FarmProducts.farm_id == FarmDetails.id)  
        .filter(FarmDetails.user_id == user_id)  
        .filter(OrderItemsModel.created_at >= week_ago)  # Filter for past week
        .scalar()
    )
    
    # Cumulative profit for the week
    
    monthly_profit = (
            db.query(
            extract('month', OrderItemsModel.created_at).label('month'),
            func.sum(OrderItemsModel.price_of_purchased_quantity).label('profit')
        )
        .join(FarmProducts, OrderItemsModel.product_id == FarmProducts.id)
        .join(FarmDetails, FarmProducts.farm_id == FarmDetails.id)
        .filter(models.FarmDetails.user_id == user_id)  # Filter by farmer's user_id
        .group_by('month')
        .order_by('month')
        .all()
    )

    # Convert to a dictionary for a chart
    profit_chart_data = {f"{month:02d}": profit for month, profit in monthly_profit}

    #average rating
    # He will make it a dummy data
    

    
    return {
        "Balance": user_balance.balance if user_balance.balance else 0,
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


async def newReviews(farm_id: int, user_id: int, rating: int, content: str):
    pass




async def consumerPage(user_id: int, db: orm.Session):
    logged_in_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if logged_in_user.role != "CONSUMER":
        raise HTTPException(status_code=401, detail="Sorry please log in as a Consumer to access available Products")
    
    _products = (
        db.query(FarmProducts)
        .order_by((FarmProducts.initial_quantity - FarmProducts.quantity_available).desc())
        .all()
    )
    
    return [product for product in _products]



async def placeOrder(data: sma.PlaceOrderPost, db: orm.Session, user_id: int):
    order = OrderModel(
        consumer_id=user_id,
        order_status=data.order_status,
        shipping_address=data.address,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    items = data.cart_items
    
    new_orders = OrderItemsModel(
        order_id=order.id,
        consumer=user_id,
        product_id=items.product_id,
        order_status=items.order_status,
        quantity_purchased=items.quantity_purchased,
        price_of_purchased_quantity=items.quantity_purchased_price
        
    )
    db.add(new_orders)
    db.commit()
    db.refresh(new_orders)
    
    return {"order": order, "order_item": new_orders}
    
    
    # parameters -> farmId, ProductID, ConsumerID, Quantity, address, order_status, total price
    # Orders Come in then we will create a new order for the ordersModel Instance
    # the we will through the items in the order then we will and save it in the database
    
    # So the list will contain something like ProductId
    
    # return back to this side
    pass