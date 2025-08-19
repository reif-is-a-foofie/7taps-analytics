from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import openai
import os
import json

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]

class ChatResponse(BaseModel):
    response: str

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests from the HTML interface"""
    
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Prepare conversation history
        messages = [
            {
                "role": "system",
                "content": """You are Seven, an AI analytics assistant for learning data. You help users explore their learning analytics through natural conversation.

Key capabilities:
- Query learning data (633 statements, 21 learners, 10 lessons)
- Create visualizations and charts
- Analyze engagement patterns
- Provide insights about learner behavior

Data sources:
- statements_new: Main learning activity data
- context_extensions_new: Metadata (lesson numbers, card types, etc.)
- results_new: Learner responses and outcomes

Common queries you can help with:
- Learner engagement by lesson
- Card type popularity
- Learner progression through course
- Recent activity trends

Always be helpful, conversational, and provide actionable insights. When appropriate, suggest visualizations or follow-up questions."""
            }
        ]
        
        # Add conversation history (limit to last 10 messages to avoid token limits)
        for msg in request.history[-10:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Generate response
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        return ChatResponse(response=response.choices[0].message.content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/chat/health")
async def chat_health():
    """Health check for chat service"""
    return {"status": "healthy", "service": "chat"}
