# app/create_admin_user.py
from sqlalchemy.orm import Session
from app import models, utils
from app.database import SessionLocal, engine
from app.config import ADMIN_EMAIL, ADMIN_PASSWORD, ROLE_ADMIN

def create_admin_user():
    # Ensure tables are created before seeding
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    existing_admin = db.query(models.Admin).filter(models.Admin.email == ADMIN_EMAIL).first()
    
    if existing_admin:
        print("Admin user already exists!")
        db.close()
        return
    
    hashed_password = utils.hash_password(ADMIN_PASSWORD)
    
    admin_user = models.Admin(
        email=ADMIN_EMAIL, 
        password_hash=hashed_password, 
        role=ROLE_ADMIN
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    db.close()
    
    print("Admin user created successfully!")

# Run the script
if __name__ == "__main__":
    create_admin_user()