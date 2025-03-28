from fastapi import FastAPI, Depends, HTTPException, security, UploadFile, File
from fastapi.responses import JSONResponse

from typing import List
from sqlalchemy.orm import Session
import service as sv
import schemas as sma
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

origins = ["*"]

# Add CORSMiddleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow these origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.mount("/images", StaticFiles(directory="uploads"), name="images")


@app.post("/api/register")
def register_user(
    user: sma.UserRequest, db: Session = Depends(sv.get_db)
):
    newUser = sv.getUserByEmail(email=user.email, db=db)
    if newUser:
        raise HTTPException(status_code=400, detail="Email Already Exists")
    
    db_user = sv.create_user(user=user, db=db)
    return sv.create_token(user=db_user, db=db)


@app.post("/api/login")
def login_user(
    form_data: security.OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(sv.get_db)
):
    db_user = sv.login(form_data.username, form_data.password, db)
    
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return sv.create_token(db_user, db)

@app.get("/api/current_user", response_model=sma.UserResponse)
def logged_in_user(user: sma.UserResponse = Depends(sv.current_user)):
    return user


@app.post("/api/add_farm", response_model = sma.FarmDetailsPostResponse)
def create_New_farm(
    post_request: sma.FarmDetailsPostRequest, 
    user: sma.UserRequest = Depends(sv.current_user), 
    db: Session = Depends(sv.get_db)
):
    return sv.create_farm(user=user, db=db, post_request=post_request)


@app.get("/api/all-farms/user", response_model=List[sma.FarmDetailsPostResponse])
def get_all_user_farms(user: sma.UserResponse = Depends(sv.current_user), db: Session = Depends(sv.get_db)):
    return sv.get_farms_by_user(user, db)


@app.get("/api/farm/{farm_id}", response_model=sma.FarmDetailsPostResponse)
def get_farm_details(
    farm_id: int, 
    db : Session = Depends(sv.get_db),
    user: sma.UserResponse = Depends(sv.current_user)
):
    post = sv.get_farm_details(farm_id, db)
    return post


# add a new product endpoint 

@app.post("/api/add_products")
async def add_new_products(
    user: sma.UserResponse = Depends(sv.current_user),
    db: Session = Depends(sv.get_db), 
    imageFile: UploadFile = File(...),
    data: sma.AddNewProduct = Depends(sma.AddNewProduct.as_form)
):
    try:
        return await sv.add_new_product(user.id, db, imageFile, data)
    except:
        raise HTTPException(status_code=400, detail="Unable to save the data")
    
    
@app.get("/api/farmer_dashboard")
async def farmer_dashboard(user: sma.UserResponse = Depends(sv.current_user), db: Session = Depends(sv.get_db)):
    return await sv.dashboardStuffs(user.id, db)


@app.get("/api/farmer/ordersPage")
async def farmersOrderPage(user: sma.UserResponse = Depends(sv.current_user), db: Session = Depends(sv.get_db)):
    return await sv.ordersPage(user.id, db)


@app.get("/api/consumer")
async def consummerPage(user: sma.UserResponse = Depends(sv.current_user), db: Session = Depends(sv.get_db)):
    page_content = await sv.consumerPage(user.id, db)
    
    
    for item in page_content:
        item.productImage = f"http://192.168.9.230:8000/{item.productImage}"
        
    
    return page_content



@app.post("/api/consumer/placeorder")
async def placeOrder(
    data: sma.PlaceOrderPost,
    user: sma.UserResponse = Depends(sv.current_user), 
    db: Session = Depends(sv.get_db),
):
    value = await sv.placeOrder(data, db, user.id)
    return value


@app.get("/api/farmer/statistics")
async def statistics(user: sma.UserResponse = Depends(sv.current_user), db: Session = Depends(sv.get_db)):
    return await sv.StatisticsPage(user.id, db)
    
