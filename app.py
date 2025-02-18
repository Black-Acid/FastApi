from fastapi import FastAPI, Depends, HTTPException, security

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