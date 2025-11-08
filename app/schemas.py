# Scanno_auth/app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import List
from datetime import datetime

class APIKeyCreate(BaseModel):
    api_key: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class HistoryCreate(BaseModel):
    chat_data: str

class HistoryResponse(BaseModel):
    id: int
    engineer_email: str
    chat_data: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    message: str
    
class AnalysisResponse(BaseModel):
    session_id: str
    file: str
    report: dict

class FullSessionHistory(BaseModel):
    session_id: str
    messages: List[ChatMessage]