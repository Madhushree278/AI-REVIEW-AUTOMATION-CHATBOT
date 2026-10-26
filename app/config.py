import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "AI-Powered Intern Review Automation System"
    APP_ENV: str = "development"
    SECRET_KEY: str = "super-secret-jwt-key-intern-review-automation-2026-secure-random"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'intern_review.db'}"
    
    # AI / LLM Configuration
    LLM_PROVIDER: str = "auto"  # auto, gemini, groq, openai, heuristic
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gemini-2.0-flash"
    
    # Email Settings
    EMAIL_PROVIDER: str = "mock"  # mock, smtp, gmail
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "intern-reviews@company.com"
    SMTP_USE_TLS: bool = True
    
    # Google Calendar & Meet
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REFRESH_TOKEN: Optional[str] = None
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"
    
    # File Storage
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt,py,js,ts,html,css,java,cpp,c,zip,json,md"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
