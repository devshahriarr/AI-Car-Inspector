# Scanno_auth/app/crud.py
from sqlalchemy.orm import Session
from app import models
from app.schemas import HistoryCreate

def get_engineer_by_email(db: Session, email: str):
    return db.query(models.Engineer).filter(models.Engineer.email == email).first()

def get_admin_by_email(db: Session, email: str):
    return db.query(models.Admin).filter(models.Admin.email == email).first()

def create_or_update_api_key(db: Session, api_key: str):
    existing_api_key = db.query(models.APIKey).first()
    
    if existing_api_key:
        existing_api_key.key_value = api_key 
        db.commit()
        db.refresh(existing_api_key)
        return existing_api_key
    else:
        new_api_key = models.APIKey(key_value=api_key) 
        db.add(new_api_key)
        db.commit()
        db.refresh(new_api_key)
        return new_api_key

def get_api_key(db: Session):
    return db.query(models.APIKey).first() 

def delete_api_key(db: Session):
    db_api_key = db.query(models.APIKey).first() # only one api key
    if db_api_key:
        db.delete(db_api_key)
        db.commit()
        return True
    return False

def create_history_entry(db: Session, history: HistoryCreate, engineer_email: str):
    db_history = models.History(
        engineer_email=engineer_email,
        chat_data=history.chat_data
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history

def get_history_by_engineer_email(db: Session, engineer_email: str):
    return (
        db.query(models.History)
        .filter(models.History.engineer_email == engineer_email)
        .order_by(models.History.timestamp.desc())
        .all()
    )

def delete_all_history_by_engineer(db: Session, engineer_email: str) -> int:
    deleted_count = (
        db.query(models.History)
        .filter(models.History.engineer_email == engineer_email)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted_count