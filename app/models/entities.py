from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
import enum
from app.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MENTOR = "MENTOR"
    INTERN = "INTERN"

class WorkflowStatus(str, enum.Enum):
    REGISTERED = "Registered"
    TASK_ASSIGNED = "Task Assigned"
    IN_PROGRESS = "In Progress"
    SUBMITTED = "Submitted"
    AI_EVAL_PENDING = "AI Evaluation Pending"
    MENTOR_APPROVAL_PENDING = "Mentor Approval Pending"
    REVIEW_SCHEDULED = "Review Scheduled"
    FEEDBACK_PUBLISHED = "Feedback Published"
    CORRECTIONS_REQUIRED = "Corrections Required"
    RESUBMITTED = "Resubmitted"
    APPROVED = "Approved"
    OVERDUE = "Overdue"
    CLOSED = "Closed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.INTERN.value, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    intern_profile = relationship("InternProfile", back_populates="user", uselist=False, foreign_keys="InternProfile.user_id")
    mentored_interns = relationship("InternProfile", back_populates="mentor", foreign_keys="InternProfile.mentor_id")
    tasks_created = relationship("Task", back_populates="creator")
    reviews_mentored = relationship("ReviewSchedule", back_populates="mentor")

class InternProfile(Base):
    __tablename__ = "intern_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    intern_id = Column(String(50), unique=True, index=True, nullable=False)
    department = Column(String(100), nullable=False)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    task_deadline = Column(DateTime, nullable=True)
    review_date = Column(DateTime, nullable=True)
    google_meet_link = Column(String(255), nullable=True)
    status = Column(String(50), default=WorkflowStatus.REGISTERED.value, nullable=False)
    correction_checklist = Column(Text, nullable=True)
    resubmission_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="intern_profile", foreign_keys=[user_id])
    mentor = relationship("User", back_populates="mentored_interns", foreign_keys=[mentor_id])
    assigned_task = relationship("Task", back_populates="assigned_interns")
    submissions = relationship("Submission", back_populates="intern", order_by="desc(Submission.version)", cascade="all, delete-orphan")
    reviews = relationship("ReviewSchedule", back_populates="intern", order_by="desc(ReviewSchedule.review_date)", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="intern", cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="intern", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    deliverables = Column(Text, nullable=False)
    submission_format = Column(String(255), default="PDF, DOCX, ZIP, or Code Files")
    rubric_criteria = Column(Text, nullable=False)  # JSON string of criteria list
    reference_links = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    max_marks = Column(Integer, default=100)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    creator = relationship("User", back_populates="tasks_created")
    assigned_interns = relationship("InternProfile", back_populates="assigned_task")
    submissions = relationship("Submission", back_populates="task")
    evaluations = relationship("Evaluation", back_populates="task")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("intern_profiles.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    status = Column(String(50), default="Submitted", nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    intern = relationship("InternProfile", back_populates="submissions")
    task = relationship("Task", back_populates="submissions")
    evaluation = relationship("Evaluation", back_populates="submission", uselist=False, cascade="all, delete-orphan")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), unique=True, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    intern_id = Column(Integer, ForeignKey("intern_profiles.id"), nullable=False)
    overall_score = Column(Float, default=0.0)
    max_score = Column(Float, default=100.0)
    completion_percentage = Column(Float, default=0.0)
    requirement_evaluations = Column(Text, default="[]")  # JSON list
    completed_items = Column(Text, default="[]")          # JSON list
    missing_items = Column(Text, default="[]")            # JSON list
    technical_errors = Column(Text, default="[]")         # JSON list
    strengths = Column(Text, default="[]")                # JSON list
    areas_for_improvement = Column(Text, default="[]")    # JSON list
    suggested_corrections = Column(Text, default="[]")    # JSON list
    recommended_next_steps = Column(Text, default="[]")   # JSON list
    ai_confidence = Column(String(50), default="High (92%)")
    is_provisional = Column(Boolean, default=True)
    mentor_notes = Column(Text, nullable=True)
    mentor_approved = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    submission = relationship("Submission", back_populates="evaluation")
    task = relationship("Task", back_populates="evaluations")
    intern = relationship("InternProfile", back_populates="evaluations")
    reviewer = relationship("User")

class ReviewSchedule(Base):
    __tablename__ = "review_schedules"

    id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("intern_profiles.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    review_date = Column(DateTime, nullable=False)
    start_time = Column(String(20), nullable=False)
    end_time = Column(String(20), nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata")
    google_meet_link = Column(String(255), nullable=False)
    calendar_event_id = Column(String(255), nullable=True)
    status = Column(String(50), default="Scheduled")  # Scheduled, Completed, Rescheduled, Cancelled
    notes = Column(Text, nullable=True)
    reminder_24h_sent = Column(Boolean, default=False)
    reminder_1h_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    intern = relationship("InternProfile", back_populates="reviews")
    mentor = relationship("User", back_populates="reviews_mentored")

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String(255), nullable=False, index=True)
    intern_id = Column(Integer, ForeignKey("intern_profiles.id"), nullable=True)
    email_type = Column(String(100), nullable=False)
    subject = Column(String(255), nullable=False)
    status = Column(String(50), default="SENT")  # SENT, FAILED, QUEUED
    error_message = Column(Text, nullable=True)
    content_preview = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    intern = relationship("InternProfile", back_populates="email_logs")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    intern_id = Column(Integer, ForeignKey("intern_profiles.id"), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    actor = relationship("User")
    intern = relationship("InternProfile")
