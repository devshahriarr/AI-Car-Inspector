# Scanno_auth/app/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.config import ROLE_ENGINEER, ROLE_ADMIN

class Engineer(Base):
    __tablename__ = "engineer"
    
    id                  = Column(Integer, primary_key=True, index=True)
    email               = Column(String, unique=True, index=True)
    password_hash       = Column(String)
    role                = Column(Integer, default=ROLE_ENGINEER)
    created_at          = Column(DateTime, default=func.now())
    updated_at          = Column(DateTime, default=func.now(), onupdate=func.now())
    history             = relationship("History", back_populates="engineer")

class Admin(Base):
    __tablename__ = "admin"
    
    id                  = Column(Integer, primary_key=True, index=True)
    email               = Column(String, unique=True, index=True)
    password_hash       = Column(String)
    role                = Column(Integer, default=ROLE_ADMIN) 
    created_at          = Column(DateTime, default=func.now())
    updated_at          = Column(DateTime, default=func.now(), onupdate=func.now())

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id                  = Column(Integer, primary_key=True, index=True)
    key_value           = Column(String, nullable=True) 
    created_at          = Column(DateTime, default=func.now())
    updated_at          = Column(DateTime, default=func.now(), onupdate=func.now())

class History(Base):
    __tablename__ = "history"
    
    id                  = Column(Integer, primary_key=True, index=True)
    engineer_email      = Column(String, ForeignKey("engineer.email"), index=True) 
    chat_data           = Column(String)
    timestamp           = Column(DateTime, default=func.now())
    engineer            = relationship("Engineer", back_populates="history")