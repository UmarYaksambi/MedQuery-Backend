from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import models, dependencies, auth_utils

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(dependencies.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect clinical credentials")

    token = auth_utils.create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role, "name": user.full_name}