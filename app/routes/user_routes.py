# Scanno_auth/app/routes/user_routes.py
from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from typing import List 

from app import crud, models, utils
from app.database import get_db
from app.auth import create_access_token, create_refresh_token, get_current_engineer
from app.schemas import UserCreate, UserLogin, Token, HistoryCreate, HistoryResponse, FullSessionHistory, ChatMessage, PasswordChange
from app.config import ROLE_ENGINEER
from app.routes.chat_core import load_chat_history

router = APIRouter()

@router.post("/register")
def register_engineer(user: UserCreate, db: Session = Depends(get_db)):
    db_engineer = crud.get_engineer_by_email(db, user.email)
    
    if db_engineer:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = utils.hash_password(user.password)
    
    db_engineer = models.Engineer(
        email=user.email, 
        password_hash=hashed_password, 
        role=ROLE_ENGINEER 
    )
    
    db.add(db_engineer)
    db.commit()
    db.refresh(db_engineer)
    
    return {"message": "User created successfully. Please proceed to login."}

@router.post("/login", response_model=Token)
def login_engineer(user: UserLogin, db: Session = Depends(get_db)):
    db_engineer = crud.get_engineer_by_email(db, user.email)
    
    if not db_engineer or not utils.verify_password(user.password, db_engineer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": db_engineer.email, "role": ROLE_ENGINEER})
    refresh_token = create_refresh_token(data={"sub": db_engineer.email, "role": ROLE_ENGINEER})
    
    return {"access_token": access_token, "refresh_token": refresh_token}

@router.post("/history", response_model=HistoryResponse, status_code=201)
def add_chat_history(history_data: HistoryCreate, current_engineer: dict = Depends(get_current_engineer), db: Session = Depends(get_db)):
    new_history = crud.create_history_entry(
        db, 
        history=history_data, 
        engineer_email=current_engineer['email']
    )
    return new_history

@router.post("/password/change")
def change_password(passwords: PasswordChange, current_engineer: dict = Depends(get_current_engineer),db: Session = Depends(get_db)):
    engineer_email = current_engineer['email']
    db_engineer = crud.get_engineer_by_email(db, engineer_email)

    if not db_engineer:
        raise HTTPException(status_code=404, detail="Engineer not found.")
        
    if not utils.verify_password(passwords.old_password, db_engineer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid current password.")
    
    if passwords.old_password == passwords.new_password:
        raise HTTPException(status_code=400, detail="New password cannot be the same as the old password.")
    
    new_hashed_password = utils.hash_password(passwords.new_password)
    db_engineer.password_hash = new_hashed_password
    
    db.commit()
    
    return {"message": "Password updated successfully."}

@router.get("/history", response_model=List[HistoryResponse])
def get_chat_history(current_engineer: dict = Depends(get_current_engineer), db: Session = Depends(get_db)):
    history = crud.get_history_by_engineer_email(db, current_engineer['email'])
    
    if not history:
        return [] 
        
    return history

@router.delete("/history")
def delete_chat_history(current_engineer: dict = Depends(get_current_engineer), db: Session = Depends(get_db)):
    deleted_count = crud.delete_all_history_by_engineer(db, current_engineer['email'])
    
    if deleted_count == 0:
        return {"message": "No chat history found to delete."}
        
    return {"message": f"Successfully deleted {deleted_count} history entries."}

@router.get("/session/{session_id}", response_model=FullSessionHistory)
def get_session_history(session_id: str, current_engineer: dict = Depends(get_current_engineer)):
    try:
        history = load_chat_history(session_id)
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Redis connection failed. Chat state is unavailable.")
    
    if not history:
        raise HTTPException(status_code=404, detail="Chat session expired or not found.")
    
    return {
        "session_id": session_id,
        "messages": [ChatMessage(**msg) for msg in history]
    }