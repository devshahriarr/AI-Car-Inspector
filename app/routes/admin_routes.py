# Scanno_auth/app/routes/admin_routes.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app import crud, utils
from app.database import get_db
from app.auth import get_current_admin, create_access_token, create_refresh_token
from app.schemas import APIKeyCreate, UserLogin, Token
from app.config import ADMIN_PASSWORD, ROLE_ADMIN

router = APIRouter()

@router.post("/login", response_model=Token)
def login_admin(user: UserLogin, db: Session = Depends(get_db)):
    db_admin = crud.get_admin_by_email(db, user.email)
    
    if not db_admin or not utils.verify_password(user.password, db_admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials for Admin")
    
    access_token = create_access_token(data={"sub": db_admin.email, "role": ROLE_ADMIN})
    refresh_token = create_refresh_token(data={"sub": db_admin.email, "role": ROLE_ADMIN})
    
    return {"access_token": access_token, "refresh_token": refresh_token}

@router.post("/apikey")
def create_or_update_api_key(api_key_data: APIKeyCreate, db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    if not api_key_data.api_key.startswith("sk-"):
        raise HTTPException(status_code=400, detail="Invalid key format. Must start with 'sk-'.")
    
    updated_api_key = crud.create_or_update_api_key(db, api_key_data.api_key)
    return {"message": "OpenAI API Key saved successfully", "key_preview": updated_api_key.key_value[:8] + "..."} 

@router.get("/apikey")
def get_api_key_status(db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    api_key = crud.get_api_key(db)
    
    if not api_key or not api_key.key_value:
        return {"status": "Not set", "key_preview": None}
    
    return {"status": "Configured", "key_preview": api_key.key_value[:8] + "..."} 

@router.delete("/apikey")
def delete_api_key(db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    if not crud.delete_api_key(db): 
        raise HTTPException(status_code=404, detail="API Key not found or already deleted")
    
    return {"message": "API Key deleted successfully"}