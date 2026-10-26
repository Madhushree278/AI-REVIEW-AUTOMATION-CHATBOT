from app.api.auth_routes import router as auth_router
from app.api.admin_routes import router as admin_router
from app.api.task_routes import router as task_router
from app.api.intern_routes import router as intern_router
from app.api.mentor_routes import router as mentor_router
from app.api.review_routes import router as review_router
from app.api.email_routes import router as email_router
from app.api.chat_routes import router as chat_router

__all__ = [
    "auth_router", "admin_router", "task_router", "intern_router",
    "mentor_router", "review_router", "email_router", "chat_router"
]
