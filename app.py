from fastapi import FastAPI, Depends, HTTPException, security

from typing import List
from sqlalchemy.orm import Session
import service as sv
import schemas as sma
from starlette.middleware.cors import CORSMiddleware

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
def get_all_user_farms(user: sma.UserRequest = Depends(sv.current_user), db: Session = Depends(sv.get_db)):
    return sv.get_farms_by_user(user, db)


@app.get("/api/farm/{farm_id}", response_model=sma.FarmDetailsPostResponse)
def get_farm_details(farm_id: int, db : Session = Depends(sv.get_db)):
    post = sv.get_farm_details(farm_id, db)
    return post