import os
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.entities import (
    User, UserRole, InternProfile, Task, ReviewSchedule, WorkflowStatus, AuditLog
)
from app.core.security import hash_password
from app.core.email_service import queue_email
from app.api import (
    auth_router, admin_router, task_router, intern_router,
    mentor_router, review_router, email_router, chat_router
)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Automated internship task assignment, document evaluation, review scheduling, and chatbot system for 100+ interns.",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(task_router)
app.include_router(intern_router)
app.include_router(mentor_router)
app.include_router(review_router)
app.include_router(email_router)
app.include_router(chat_router)

# Mount Static Files
STATIC_DIR = Path(__file__).resolve().parent / "static"
os.makedirs(STATIC_DIR / "css", exist_ok=True)
os.makedirs(STATIC_DIR / "js", exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_home():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "AI-Powered Intern Review Automation API is active. Open /docs for Swagger documentation."}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "email_provider": settings.EMAIL_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
        "timestamp": datetime.utcnow().isoformat()
    }

def seed_initial_database():
    """Seeds default admin, mentor, tasks, and initial interns if database is empty."""
    db: Session = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.role == UserRole.ADMIN.value).first()
        if not admin:
            admin = User(
                email="admin@company.com",
                full_name="System Administrator",
                hashed_password=hash_password("Admin@2026"),
                role=UserRole.ADMIN.value,
                is_active=True
            )
            db.add(admin)

        # Check if mentor exists
        mentor = db.query(User).filter(User.email == "mentor.sarah@company.com").first()
        if not mentor:
            mentor = User(
                email="mentor.sarah@company.com",
                full_name="Sarah Jenkins (Senior AI Lead)",
                hashed_password=hash_password("Mentor@2026"),
                role=UserRole.MENTOR.value,
                is_active=True
            )
            db.add(mentor)

        mentor2 = db.query(User).filter(User.email == "mentor.alex@company.com").first()
        if not mentor2:
            mentor2 = User(
                email="mentor.alex@company.com",
                full_name="Alex Rivera (Engineering Manager)",
                hashed_password=hash_password("Mentor@2026"),
                role=UserRole.MENTOR.value,
                is_active=True
            )
            db.add(mentor2)
            
        db.flush()

        # Seed initial task
        sample_task = db.query(Task).first()
        if not sample_task:
            sample_task = Task(
                title="AI Microservice & RAG Pipeline Implementation",
                description="Develop a Python FastAPI service with RAG document retrieval, automated unit tests, and structured JSON outputs.",
                deliverables="1. Python source code (FastAPI routes & service).\n2. Automated test suite.\n3. PDF/DOCX or markdown documentation explaining architecture.",
                submission_format="PDF, DOCX, ZIP, or Code Files (.py, .zip)",
                rubric_criteria='''[
                    {"requirement": "REST API Architecture", "description": "Clean endpoint structure, proper status codes, Pydantic validation.", "max_marks": 25},
                    {"requirement": "RAG Document Retrieval", "description": "Text extraction, chunking, and similarity ranking implementation.", "max_marks": 30},
                    {"requirement": "Error Handling & Logging", "description": "Structured try/except blocks, safe fallbacks, and audit logging.", "max_marks": 25},
                    {"requirement": "Documentation & Tests", "description": "Unit tests and clear README or PDF report with instructions.", "max_marks": 20}
                ]''',
                deadline=datetime.utcnow() + timedelta(days=7),
                max_marks=100,
                created_by=admin.id
            )
            db.add(sample_task)
            db.flush()

        # Seed initial demo interns if none exist
        if db.query(InternProfile).count() == 0:
            demo_interns = [
                ("Aarav Patel", "aarav.patel@company.com", "INT-2026-001", "AI/ML", mentor.id),
                ("Sneha Sharma", "sneha.sharma@company.com", "INT-2026-002", "Backend Engineering", mentor2.id),
                ("Rohan Gupta", "rohan.gupta@company.com", "INT-2026-003", "Data Science", mentor.id),
            ]
            for name, email, i_id, dept, m_id in demo_interns:
                u = User(
                    email=email,
                    full_name=name,
                    hashed_password=hash_password("Intern@2026"),
                    role=UserRole.INTERN.value,
                    is_active=True
                )
                db.add(u)
                db.flush()
                ip = InternProfile(
                    user_id=u.id,
                    intern_id=i_id,
                    department=dept,
                    mentor_id=m_id,
                    assigned_task_id=sample_task.id,
                    task_deadline=datetime.utcnow() + timedelta(days=5),
                    google_meet_link="https://meet.google.com/abc-wxyz-qrs",
                    status=WorkflowStatus.TASK_ASSIGNED.value
                )
                db.add(ip)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database Seed Error] {e}")
    finally:
        db.close()

# Seed database on startup
seed_initial_database()
