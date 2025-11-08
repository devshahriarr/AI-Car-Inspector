# Scanno_auth/app/config.py
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scanno_integrated.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

ACCESS_TOKEN_EXPIRE_MINUTES = 30 
ROLE_ADMIN = 1
ROLE_ENGINEER = 2

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@scanno.ai")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "supersecretadminpass")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
SESSION_TTL = 3600 # Session expiration time in seconds (1 hour)