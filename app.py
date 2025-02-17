from fastapi import FastAPI, Depends, HTTPException
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


app = FastAPI()

@app.post("/api/register")
def register_user(
    user: sma.UserRequest, db: Session = Depends(sv.get_db)
):
    newUser = sv.getUserByEmail(email=user.email, db=db)
    if newUser:
        raise HTTPException(status_code=400, detail="Email Already Exists")
    
    db_user = sv.create_user(user=user, db=db)
    return sv.create_token(user=db_user)