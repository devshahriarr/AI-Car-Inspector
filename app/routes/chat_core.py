# Scanno_auth/app/routes/chat_core.py
import os, io, json, time, logging, base64, uuid
import pdfplumber
import redis 
from typing import Optional, List 
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.schemas import ChatMessage, ChatRequest, AnalysisResponse, HistoryCreate
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB, SESSION_TTL
from app.auth import get_current_engineer
from app.database import get_db
from app import crud 

router = APIRouter(tags=["Chat Core"])

redis_client: redis.Redis = None

def set_redis_client(client: redis.Redis):
    global redis_client
    redis_client = client


def get_openai_client(db: Session = Depends(get_db)) -> OpenAI:
    api_key_record = crud.get_api_key(db)
    
    if not api_key_record or not api_key_record.key_value:
        raise HTTPException(status_code=503, detail="OpenAI service unavailable. API key not configured by admin.")
        
    return OpenAI(api_key=api_key_record.key_value)

def extract_text_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return text.strip() or None
    except Exception as e:
        logging.error(f"PDF reading failed: {e}")
        return None

def save_chat_history(session_id: str, history: List[ChatMessage]):
    if not redis_client:
        raise ConnectionError("Redis client is not initialized.")
        
    key = f"chat:session:{session_id}"
    redis_client.delete(key) 
    
    messages_json = [msg.model_dump_json() for msg in history]
    if messages_json:
        redis_client.lpush(key, *messages_json) 
    
    redis_client.expire(key, SESSION_TTL)
    logging.info(f"Session {session_id} saved with TTL set to {SESSION_TTL}s.")


def load_chat_history(session_id: str) -> Optional[List[dict]]:
    if not redis_client:
        raise ConnectionError("Redis client is not initialized.")
        
    key = f"chat:session:{session_id}"
    
    messages_json = redis_client.lrange(key, 0, -1)
    if not messages_json:
        return None
    
    redis_client.expire(key, SESSION_TTL)
    
    history = [json.loads(msg) for msg in messages_json]
    
    return history[::-1] 


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def analyze_with_gpt_vision(image_bytes: bytes, client: OpenAI) -> str:
    logging.info("Sending image to GPT-4o Vision...")
    start = time.time()
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """
You are Scanno — the official smart car inspection expert in Qatar.
You analyze vehicle inspection reports in English or Arabic.

Guidelines:
- Respond in Arabic if the report is Arabic, otherwise English.
- Be short, clear, and friendly.
- Never mention being an AI.
- Return ONLY valid JSON:

{
  "summary": "1-line car condition",
  "risk_level": "Low|Medium|High|Critical",
  "issues": ["bullet points"],
  "maintenance": ["action items"],
  "recommendation": "final advice"
}
"""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this car inspection report image and respond in JSON only."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=800,
            temperature=0.2
        )

        elapsed = time.time() - start
        logging.info(f"GPT-4o Vision responded in {elapsed:.2f}s")
        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"Vision analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Vision analysis failed: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def analyze_with_gpt_text(text: str, client: OpenAI) -> str:
    logging.info("Analyzing text-based report with GPT-4o...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are Scanno — the smart car inspection expert in Qatar."
                },
                {
                    "role": "user",
                    "content": f"Analyze this inspection report text and return JSON only:\n{text}"
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logging.error(f"Text analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Text analysis failed: {str(e)}")


@router.post("/analyze-report", response_model=AnalysisResponse)
async def analyze_report(file: UploadFile = File(...), db: Session = Depends(get_db), current_engineer: dict = Depends(get_current_engineer)):
    global redis_client 
    
    if redis_client is None:
        raise HTTPException(status_code=503, detail="AI Chat service unavailable: Redis connection failed.")

    try:
        client = get_openai_client(db=db)
        
        filename = file.filename.lower()
        file_bytes = await file.read()
        text = None
        
        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(file_bytes)
            if text:
                raw_response = analyze_with_gpt_text(text, client)
                system_content = f"You are Scanno — the smart car inspection expert in Qatar. The user has provided the following inspection report text: {text}"
            else:
                raw_response = analyze_with_gpt_vision(file_bytes, client)
                system_content = "You are Scanno — the smart car inspection expert in Qatar. The user has uploaded an image/scanned PDF of a car inspection report."
                
        elif filename.endswith((".jpg", ".jpeg", ".png")):
            raw_response = analyze_with_gpt_vision(file_bytes, client)
            system_content = "You are Scanno — the smart car inspection expert in Qatar. The user has uploaded an image of a car inspection report."
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type.")
        
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        json_str = raw_response[start:end]
        
        if not json_str:
            logging.error(f"AI response did not contain a valid JSON block: {raw_response[:100]}...")
            raise HTTPException(status_code=500, detail="Analysis failed: AI response was malformed and contained no JSON data.")
        
        report_json = json.loads(json_str)
        bot_initial_message = json.dumps(report_json, indent=2)
        
        session_id = str(uuid.uuid4())
        
        initial_history = [
            ChatMessage(role="system", content=system_content),
            ChatMessage(role="assistant", content=bot_initial_message)
        ]
        
        save_chat_history(session_id, initial_history)
        
        summary_text = report_json.get('summary', 'Summary not available in AI report.')
        
        history_log = HistoryCreate(
            chat_data=json.dumps({
                "file": filename, 
                "report_summary": summary_text 
            })
        )
        crud.create_history_entry(db, history_log, current_engineer['email'])
        
        return {
            "session_id": session_id,
            "file": filename, 
            "report": report_json
        }
        
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logging.error(f"JSON Parsing failed after AI response: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed: AI returned unparseable structured data.")
    except Exception as e:
        logging.error(f"Critical Analysis failed for engineer {current_engineer.get('email', 'Unknown')}: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {type(e).__name__} during processing.")

@router.post("/chat")
async def chat_with_report(chat_data: ChatRequest, db: Session = Depends(get_db), current_engineer: dict = Depends(get_current_engineer)):
    session_id = chat_data.session_id
    user_message = chat_data.message
    
    try:
        history = load_chat_history(session_id)
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Redis connection failed. Chat state is unavailable.")
        
    if not history:
        raise HTTPException(status_code=404, detail="Chat session expired or not found.")
    
    user_chat_message = ChatMessage(role="user", content=user_message)
    history.append(user_chat_message.model_dump())
    
    openai_messages = history
    
    logging.info(f"Session {session_id}: Sending {len(openai_messages)} messages to GPT-4o...")
    try:
        client = get_openai_client(db=db)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,
            temperature=0.7, 
            max_tokens=500 
        )
        bot_response_content = response.choices[0].message.content
        
    except HTTPException:
        raise 
    except Exception as e:
        logging.error(f"Chat completion failed for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get response from AI.")
        
    bot_chat_message = ChatMessage(role="assistant", content=bot_response_content)
    history.append(bot_chat_message.model_dump())
    
    history_to_save = [ChatMessage(**msg) for msg in history]
    save_chat_history(session_id, history_to_save)
    
    return {"session_id": session_id, "response": bot_response_content}