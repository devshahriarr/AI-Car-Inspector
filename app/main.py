# Scanno_auth/app/main.py
import logging
import redis 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import engine
from app import models 
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB
from app.routes import user_routes, admin_routes, chat_core
from app.routes.chat_core import set_redis_client 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s: %(message)s",
    handlers=[logging.FileHandler("scanno_integrated.log"), logging.StreamHandler()],
)

redis_client: redis.Redis = None

app = FastAPI(title="Scanno Integrated AI Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_routes.router, prefix="/user", tags=["User Authentication"])
app.include_router(admin_routes.router, prefix="/admin", tags=["Admin (Key Management)"])
app.include_router(chat_core.router, tags=["AI Core Chat"])


@app.on_event("startup")
def startup_event():
    global redis_client
    
    try:
        models.Base.metadata.create_all(bind=engine)
        logging.info("SQLAlchemy database tables created/verified.")
    except Exception as e:
        logging.error(f"Failed to create database tables: {e}")
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        redis_client.ping()
        set_redis_client(redis_client) 
        logging.info("Successfully connected to Redis.")
    except Exception as e:
        logging.error(f"Failed to connect to Redis: {e}. AI chat state will not function.")

@app.on_event("shutdown")
def shutdown_event():
    if redis_client:
        logging.info("Application shutdown.")

@app.get("/")
async def root():
    return JSONResponse({"message": "Scanno Integrated AI Analyzer Backend is operational."})
