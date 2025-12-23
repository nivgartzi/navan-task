from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
from app.services.llm_engine import LLMEngine
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# Debug: Check if API key is loaded (show first 10 chars only for security)
import os
api_key = os.getenv("OPEN_AI_API_KEY") or os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"✓ API Key loaded: {api_key[:10]}...{api_key[-4:]} (length: {len(api_key)})")
else:
    print("✗ ERROR: API Key not found in environment variables!")
    print("   Make sure your .env file has: OPENAI_API_KEY=your_key_here")

app = FastAPI(title="Booking Hotels Assistant")
try:
    engine = LLMEngine()
except ValueError as e:
    print(f"✗ ERROR: {e}")
    raise

# Serve static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        response = await engine.chat(request.message, request.history)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8015)
