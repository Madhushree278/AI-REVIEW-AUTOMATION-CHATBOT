from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import InternProfile
from app.schemas.schemas import ChatQueryRequest, ChatQueryResponse
from app.core.security import get_current_intern_profile
from app.core.chatbot_rag import ask_intern_chatbot

router = APIRouter(prefix="/api/chat", tags=["Intern AI Chatbot"])

@router.post("/ask", response_model=ChatQueryResponse)
def ask_chatbot(
    req: ChatQueryRequest,
    profile: InternProfile = Depends(get_current_intern_profile),
    db: Session = Depends(get_db)
):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = ask_intern_chatbot(profile=profile, question=req.question.strip(), db=db)
    return ChatQueryResponse(
        answer=result["answer"],
        grounded_context=result["grounded_context"],
        timestamp=datetime.utcnow()
    )
