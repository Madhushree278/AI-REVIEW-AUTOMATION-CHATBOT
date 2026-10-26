from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime

# ================= Auth Schemas =================
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "INTERN"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    intern_id: Optional[str] = None

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None

# ================= Task Schemas =================
class RubricItem(BaseModel):
    requirement: str
    description: str
    max_marks: float = 20.0

class TaskCreate(BaseModel):
    title: str
    description: str
    deliverables: str
    submission_format: str = "PDF, DOCX, ZIP, or Code Files"
    rubric_criteria: List[RubricItem]
    reference_links: Optional[str] = None
    deadline: Optional[datetime] = None
    max_marks: int = 100

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deliverables: Optional[str] = None
    submission_format: Optional[str] = None
    rubric_criteria: Optional[List[RubricItem]] = None
    reference_links: Optional[str] = None
    deadline: Optional[datetime] = None
    max_marks: Optional[int] = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    deliverables: str
    submission_format: str
    rubric_criteria: str
    reference_links: Optional[str]
    deadline: Optional[datetime]
    max_marks: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TaskAssignRequest(BaseModel):
    task_id: int
    intern_ids: List[int]  # List of InternProfile primary keys
    deadline: Optional[datetime] = None
    send_email: bool = True

# ================= Submission & Evaluation Schemas =================
class EvaluationOut(BaseModel):
    id: int
    submission_id: int
    task_id: int
    intern_id: int
    overall_score: float
    max_score: float
    completion_percentage: float
    requirement_evaluations: List[Dict[str, Any]]
    completed_items: List[str]
    missing_items: List[str]
    technical_errors: List[str]
    strengths: List[str]
    areas_for_improvement: List[str]
    suggested_corrections: List[str]
    recommended_next_steps: List[str]
    ai_confidence: str
    is_provisional: bool
    mentor_notes: Optional[str]
    mentor_approved: bool
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SubmissionOut(BaseModel):
    id: int
    intern_id: int
    task_id: int
    version: int
    file_name: str
    file_type: str
    file_size: int
    description: Optional[str]
    status: str
    submitted_at: datetime
    evaluation: Optional[EvaluationOut] = None

    model_config = ConfigDict(from_attributes=True)

class MentorFeedbackApproveRequest(BaseModel):
    overall_score: Optional[float] = None
    mentor_notes: str
    approve_evaluation: bool = True
    update_status_to_approved: bool = False

class CorrectionRequest(BaseModel):
    checklist: str
    resubmission_deadline: datetime
    notes: Optional[str] = None
    next_review_date: Optional[datetime] = None
    google_meet_link: Optional[str] = None

# ================= Review Schemas =================
class ReviewCreate(BaseModel):
    intern_id: int
    mentor_id: int
    review_date: datetime
    start_time: str
    end_time: str
    timezone: str = "Asia/Kolkata"
    google_meet_link: Optional[str] = None
    notes: Optional[str] = None
    use_google_calendar: bool = False
    send_invitation_email: bool = True

class ReviewUpdate(BaseModel):
    review_date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    timezone: Optional[str] = None
    google_meet_link: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class ReviewOut(BaseModel):
    id: int
    intern_id: int
    mentor_id: int
    review_date: datetime
    start_time: str
    end_time: str
    timezone: str
    google_meet_link: str
    calendar_event_id: Optional[str]
    status: str
    notes: Optional[str]
    reminder_24h_sent: bool
    reminder_1h_sent: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ================= Intern Schemas =================
class InternCreate(BaseModel):
    full_name: str
    email: EmailStr
    intern_id: str
    department: str
    mentor_id: Optional[int] = None
    assigned_task_id: Optional[int] = None
    task_deadline: Optional[datetime] = None
    review_date: Optional[datetime] = None
    google_meet_link: Optional[str] = None
    password: Optional[str] = "Intern@2026"

class InternUpdate(BaseModel):
    department: Optional[str] = None
    mentor_id: Optional[int] = None
    assigned_task_id: Optional[int] = None
    task_deadline: Optional[datetime] = None
    review_date: Optional[datetime] = None
    google_meet_link: Optional[str] = None
    status: Optional[str] = None
    correction_checklist: Optional[str] = None
    resubmission_deadline: Optional[datetime] = None

class InternOut(BaseModel):
    id: int
    user_id: int
    intern_id: str
    full_name: str
    email: str
    department: str
    mentor_id: Optional[int] = None
    mentor_name: Optional[str] = None
    assigned_task_id: Optional[int] = None
    task_title: Optional[str] = None
    task_deadline: Optional[datetime] = None
    review_date: Optional[datetime] = None
    google_meet_link: Optional[str] = None
    status: str
    correction_checklist: Optional[str] = None
    resubmission_deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BulkInternImportRow(BaseModel):
    full_name: str
    email: EmailStr
    intern_id: str
    department: str
    mentor_email: Optional[str] = None

class BulkInternImportResult(BaseModel):
    total_processed: int
    successful_imports: int
    failed_imports: int
    duplicate_emails_skipped: int
    duplicate_ids_skipped: int
    errors: List[str]

# ================= Logs & Chat =================
class EmailLogOut(BaseModel):
    id: int
    recipient: str
    intern_id: Optional[int]
    email_type: str
    subject: str
    status: str
    error_message: Optional[str]
    content_preview: Optional[str]
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AuditLogOut(BaseModel):
    id: int
    action: str
    actor_id: Optional[int]
    actor_name: Optional[str] = None
    intern_id: Optional[int]
    details: Optional[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatQueryRequest(BaseModel):
    question: str

class ChatQueryResponse(BaseModel):
    answer: str
    grounded_context: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
