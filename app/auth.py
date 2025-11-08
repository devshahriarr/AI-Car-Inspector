# Scanno_auth/app/auth.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Union
from jose import jwt, JWTError

from app.config import JWT_SECRET_KEY, ROLE_ADMIN, ROLE_ENGINEER, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app import crud

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login") 

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Union[timedelta, None] = None):
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)  
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        
        email: str = payload.get("sub")
        role: int = payload.get("role")
        
        if email is None or role is None:
            raise credentials_exception
            
        return {"email": email, "role": role}
        
    except JWTError:
        raise credentials_exception

def get_current_user(token: str = Security(oauth2_scheme), db: Session = Depends(get_db)):
    token_data = verify_token(token)
    email = token_data['email']
    role = token_data['role']
    
    return {"email": email, "role": role}

def get_current_admin(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user['role'] != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
        
    db_admin = crud.get_admin_by_email(db, current_user['email'])
    
    if db_admin is None:
        raise HTTPException(status_code=404, detail="Admin user not found in database")
        
    return {"email": db_admin.email, "role": current_user['role']}

def get_current_engineer(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user['role'] != ROLE_ENGINEER:
        raise HTTPException(status_code=403, detail="Engineer privileges required")
        
    db_engineer = crud.get_engineer_by_email(db, current_user['email'])
    
    if db_engineer is None:
        raise HTTPException(status_code=404, detail="Engineer user not found in database")
        
    return {"email": db_engineer.email, "role": current_user['role']}