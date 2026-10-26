import sys
import uvicorn
from app.config import settings
from app.main import app, seed_initial_database

def main():
    print("=" * 70)
    print("  AI-POWERED INTERN REVIEW AUTOMATION SYSTEM")
    print("=" * 70)
    print(f"• App Environment:   {settings.APP_ENV}")
    print(f"• Database URL:      {settings.DATABASE_URL}")
    print(f"• Email Provider:    {settings.EMAIL_PROVIDER}")
    print(f"• LLM Provider:      {settings.LLM_PROVIDER}")
    print(f"• Server URL:        http://{settings.HOST}:{settings.PORT}")
    print(f"• API Docs:          http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 70)
    print("Seeding database...")
    seed_initial_database()
    print("Starting Uvicorn server...")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)

if __name__ == "__main__":
    main()
