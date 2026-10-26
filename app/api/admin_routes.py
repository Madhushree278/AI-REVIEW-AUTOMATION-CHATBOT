import io
import re
from datetime import datetime
from typing import List, Optional
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from app.database import get_db
from app.models.entities import (
    User, UserRole, InternProfile, Task, Submission, ReviewSchedule, AuditLog, WorkflowStatus
)
from app.schemas.schemas import (
    InternCreate, InternUpdate, InternOut, BulkInternImportResult, AuditLogOut
)
from app.core.security import get_current_user, require_roles, hash_password
from app.core.email_service import queue_email

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

@router.get("/stats")
def get_admin_dashboard_stats(
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MENTOR.value])),
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    total_interns = db.query(InternProfile).count()
    not_started = db.query(InternProfile).filter(
        InternProfile.status.in_([WorkflowStatus.REGISTERED.value, WorkflowStatus.TASK_ASSIGNED.value])
    ).count()
    in_progress = db.query(InternProfile).filter(InternProfile.status == WorkflowStatus.IN_PROGRESS.value).count()
    submitted = db.query(InternProfile).filter(
        InternProfile.status.in_([
            WorkflowStatus.SUBMITTED.value,
            WorkflowStatus.AI_EVAL_PENDING.value,
            WorkflowStatus.MENTOR_APPROVAL_PENDING.value
        ])
    ).count()
    reviews_scheduled = db.query(ReviewSchedule).filter(ReviewSchedule.status == "Scheduled").count()
    reviews_completed = db.query(ReviewSchedule).filter(ReviewSchedule.status == "Completed").count()
    
    # Overdue: deadline passed and status not approved or closed
    overdue = db.query(InternProfile).filter(
        InternProfile.task_deadline < now,
        ~InternProfile.status.in_([WorkflowStatus.APPROVED.value, WorkflowStatus.CLOSED.value, WorkflowStatus.SUBMITTED.value])
    ).count()
    
    needs_another_review = db.query(InternProfile).filter(
        InternProfile.status.in_([WorkflowStatus.CORRECTIONS_REQUIRED.value, WorkflowStatus.RESUBMITTED.value])
    ).count()

    # Upcoming reviews (next 5)
    upcoming_reviews = db.query(ReviewSchedule).filter(
        ReviewSchedule.status == "Scheduled",
        ReviewSchedule.review_date >= now
    ).order_by(ReviewSchedule.review_date.asc()).limit(6).all()

    upcoming_formatted = []
    for r in upcoming_reviews:
        upcoming_formatted.append({
            "id": r.id,
            "intern_name": r.intern.user.full_name if r.intern and r.intern.user else "Unknown",
            "intern_id": r.intern.intern_id if r.intern else "Unknown",
            "mentor_name": r.mentor.full_name if r.mentor else "Unknown",
            "review_date": r.review_date.strftime("%Y-%m-%d"),
            "time": f"{r.start_time} - {r.end_time}",
            "google_meet_link": r.google_meet_link,
            "status": r.status
        })

    return {
        "total_interns": total_interns,
        "not_started": not_started,
        "in_progress": in_progress,
        "submitted_for_review": submitted,
        "reviews_scheduled": reviews_scheduled,
        "reviews_completed": reviews_completed,
        "overdue_interns": overdue,
        "needs_another_review": needs_another_review,
        "upcoming_reviews": upcoming_formatted
    }

@router.get("/interns")
def list_interns(
    search: Optional[str] = Query(None, description="Search by name, email, or intern ID"),
    department: Optional[str] = Query(None, description="Filter by department"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by workflow status"),
    mentor_id: Optional[int] = Query(None, description="Filter by assigned mentor"),
    sort_by: str = Query("created_at", description="Field to sort by: name, intern_id, department, status, deadline"),
    order: str = Query("desc", description="asc or desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(150, ge=1, le=500),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MENTOR.value])),
    db: Session = Depends(get_db)
):
    query = db.query(InternProfile).join(User, InternProfile.user_id == User.id)

    # Search filter
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_term),
                User.email.ilike(search_term),
                InternProfile.intern_id.ilike(search_term)
            )
        )

    # Department filter
    if department:
        query = query.filter(InternProfile.department == department)

    # Status filter
    if status_filter:
        query = query.filter(InternProfile.status == status_filter)

    # Mentor filter
    if mentor_id:
        query = query.filter(InternProfile.mentor_id == mentor_id)

    # Sorting
    sort_column = InternProfile.created_at
    if sort_by == "name":
        sort_column = User.full_name
    elif sort_by == "intern_id":
        sort_column = InternProfile.intern_id
    elif sort_by == "department":
        sort_column = InternProfile.department
    elif sort_by == "status":
        sort_column = InternProfile.status
    elif sort_by == "deadline":
        sort_column = InternProfile.task_deadline

    if order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    total = query.count()
    interns = query.offset(skip).limit(limit).all()

    results = []
    for ip in interns:
        task = ip.assigned_task
        mentor = ip.mentor
        results.append({
            "id": ip.id,
            "user_id": ip.user_id,
            "intern_id": ip.intern_id,
            "full_name": ip.user.full_name,
            "email": ip.user.email,
            "department": ip.department,
            "mentor_id": ip.mentor_id,
            "mentor_name": mentor.full_name if mentor else "Unassigned",
            "assigned_task_id": ip.assigned_task_id,
            "task_title": task.title if task else "None",
            "task_deadline": ip.task_deadline.isoformat() if ip.task_deadline else None,
            "review_date": ip.review_date.isoformat() if ip.review_date else None,
            "google_meet_link": ip.google_meet_link,
            "status": ip.status,
            "submission_count": len(ip.submissions),
            "created_at": ip.created_at.isoformat()
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "interns": results
    }

@router.post("/interns", response_model=InternOut)
def create_intern(
    data: InternCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    # Validate email format
    if not EMAIL_REGEX.match(data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email address format: '{data.email}'"
        )

    # Check for duplicate email
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{data.email}' already exists."
        )

    # Check for duplicate Intern ID
    if db.query(InternProfile).filter(InternProfile.intern_id == data.intern_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Intern ID '{data.intern_id}' is already registered."
        )

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password or "Intern@2026"),
        role=UserRole.INTERN.value,
        is_active=True
    )
    db.add(user)
    db.flush()

    profile = InternProfile(
        user_id=user.id,
        intern_id=data.intern_id,
        department=data.department,
        mentor_id=data.mentor_id,
        assigned_task_id=data.assigned_task_id,
        task_deadline=data.task_deadline,
        review_date=data.review_date,
        google_meet_link=data.google_meet_link,
        status=WorkflowStatus.REGISTERED.value
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Send welcome email in background
    queue_email(
        recipient=user.email,
        template_key="WELCOME",
        context={
            "intern_name": user.full_name,
            "intern_id": profile.intern_id,
            "department": profile.department,
            "default_password": data.password or "Intern@2026"
        },
        intern_id=profile.id
    )

    # Audit log
    db.add(AuditLog(
        action="INTERN_CREATED",
        actor_id=current_user.id,
        intern_id=profile.id,
        details=f"Created intern {profile.intern_id} ({user.email}) in {profile.department}"
    ))
    db.commit()

    return InternOut(
        id=profile.id,
        user_id=user.id,
        intern_id=profile.intern_id,
        full_name=user.full_name,
        email=user.email,
        department=profile.department,
        mentor_id=profile.mentor_id,
        mentor_name=profile.mentor.full_name if profile.mentor else None,
        assigned_task_id=profile.assigned_task_id,
        task_title=profile.assigned_task.title if profile.assigned_task else None,
        task_deadline=profile.task_deadline,
        review_date=profile.review_date,
        google_meet_link=profile.google_meet_link,
        status=profile.status,
        correction_checklist=profile.correction_checklist,
        resubmission_deadline=profile.resubmission_deadline,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )

@router.post("/interns/import", response_model=BulkInternImportResult)
async def bulk_import_interns(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """
    Bulk import 100+ interns from CSV or Excel (.xlsx).
    Performs email validation and deduplication against existing records.
    """
    filename = file.filename.lower()
    content = await file.read()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx) file."
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}"
        )

    # Normalize column names: strip and lowercase
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Required columns
    col_mapping = {
        "name": ["name", "full_name", "intern_name", "student_name"],
        "email": ["email", "email_address", "intern_email"],
        "id": ["intern_id", "id", "student_id", "roll_no"],
        "dept": ["department", "dept", "domain", "internship_domain"]
    }

    def resolve_col(candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    name_col = resolve_col(col_mapping["name"])
    email_col = resolve_col(col_mapping["email"])
    id_col = resolve_col(col_mapping["id"])
    dept_col = resolve_col(col_mapping["dept"])
    mentor_col = resolve_col(["mentor_email", "mentor", "assigned_mentor"])

    if not (name_col and email_col and id_col and dept_col):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns. File must contain columns for Name, Email, Intern ID, and Department. Found: {list(df.columns)}"
        )

    total_rows = len(df)
    successful = 0
    dup_emails = 0
    dup_ids = 0
    errors = []

    # Cache existing emails and IDs for fast deduplication check
    existing_emails = set(e[0].lower() for e in db.query(User.email).all())
    existing_ids = set(i[0].lower() for i in db.query(InternProfile.intern_id).all())

    # Build mentor cache
    mentor_users = {m.email.lower(): m.id for m in db.query(User).filter(User.role == UserRole.MENTOR.value).all()}
    default_mentor_id = next(iter(mentor_users.values())) if mentor_users else None

    batch_users = []
    batch_profiles = []

    for idx, row in df.iterrows():
        row_num = idx + 2
        name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
        email = str(row[email_col]).strip().lower() if pd.notna(row[email_col]) else ""
        intern_id = str(row[id_col]).strip() if pd.notna(row[id_col]) else ""
        department = str(row[dept_col]).strip() if pd.notna(row[dept_col]) else "General"
        mentor_val = str(row[mentor_col]).strip().lower() if mentor_col and pd.notna(row[mentor_col]) else ""

        if not name or not email or not intern_id:
            errors.append(f"Row {row_num}: Missing name, email, or intern ID.")
            continue

        if not EMAIL_REGEX.match(email):
            errors.append(f"Row {row_num}: Invalid email format '{email}'.")
            continue

        if email in existing_emails:
            dup_emails += 1
            continue

        if intern_id.lower() in existing_ids:
            dup_ids += 1
            continue

        existing_emails.add(email)
        existing_ids.add(intern_id.lower())

        mentor_id = mentor_users.get(mentor_val, default_mentor_id)

        user = User(
            email=email,
            full_name=name,
            hashed_password=hash_password("Intern@2026"),
            role=UserRole.INTERN.value,
            is_active=True
        )
        db.add(user)
        db.flush()

        profile = InternProfile(
            user_id=user.id,
            intern_id=intern_id,
            department=department,
            mentor_id=mentor_id,
            status=WorkflowStatus.REGISTERED.value
        )
        db.add(profile)
        db.flush()

        successful += 1

        # Queue welcome email
        queue_email(
            recipient=email,
            template_key="WELCOME",
            context={
                "intern_name": name,
                "intern_id": intern_id,
                "department": department,
                "default_password": "Intern@2026"
            },
            intern_id=profile.id
        )

    db.commit()

    db.add(AuditLog(
        action="BULK_INTERN_IMPORT",
        actor_id=current_user.id,
        details=f"Imported {successful} interns from file '{file.filename}'. Duplicates skipped: {dup_emails} emails, {dup_ids} IDs."
    ))
    db.commit()

    return BulkInternImportResult(
        total_processed=total_rows,
        successful_imports=successful,
        failed_imports=total_rows - successful - dup_emails - dup_ids,
        duplicate_emails_skipped=dup_emails,
        duplicate_ids_skipped=dup_ids,
        errors=errors[:15]  # limit error output to first 15 for readability
    )

@router.get("/interns/{intern_id}")
def get_intern_detail(
    intern_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MENTOR.value])),
    db: Session = Depends(get_db)
):
    ip = db.query(InternProfile).filter(InternProfile.id == intern_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="Intern record not found.")

    submissions_data = []
    for s in ip.submissions:
        ev_data = None
        if s.evaluation:
            import json
            ev = s.evaluation
            ev_data = {
                "id": ev.id,
                "overall_score": ev.overall_score,
                "max_score": ev.max_score,
                "completion_percentage": ev.completion_percentage,
                "ai_confidence": ev.ai_confidence,
                "is_provisional": ev.is_provisional,
                "mentor_approved": ev.mentor_approved,
                "mentor_notes": ev.mentor_notes,
                "strengths": json.loads(ev.strengths) if ev.strengths else [],
                "missing_items": json.loads(ev.missing_items) if ev.missing_items else [],
                "technical_errors": json.loads(ev.technical_errors) if ev.technical_errors else [],
                "suggested_corrections": json.loads(ev.suggested_corrections) if ev.suggested_corrections else [],
                "requirement_evaluations": json.loads(ev.requirement_evaluations) if ev.requirement_evaluations else []
            }
        submissions_data.append({
            "id": s.id,
            "version": s.version,
            "file_name": s.file_name,
            "file_type": s.file_type,
            "file_size": s.file_size,
            "status": s.status,
            "submitted_at": s.submitted_at.isoformat(),
            "description": s.description,
            "evaluation": ev_data
        })

    reviews_data = []
    for r in ip.reviews:
        reviews_data.append({
            "id": r.id,
            "review_date": r.review_date.strftime("%Y-%m-%d"),
            "start_time": r.start_time,
            "end_time": r.end_time,
            "timezone": r.timezone,
            "google_meet_link": r.google_meet_link,
            "status": r.status,
            "notes": r.notes
        })

    return {
        "id": ip.id,
        "intern_id": ip.intern_id,
        "full_name": ip.user.full_name,
        "email": ip.user.email,
        "department": ip.department,
        "mentor_id": ip.mentor_id,
        "mentor_name": ip.mentor.full_name if ip.mentor else "Unassigned",
        "assigned_task": {
            "id": ip.assigned_task.id,
            "title": ip.assigned_task.title,
            "description": ip.assigned_task.description,
            "deliverables": ip.assigned_task.deliverables,
            "submission_format": ip.assigned_task.submission_format,
            "max_marks": ip.assigned_task.max_marks
        } if ip.assigned_task else None,
        "task_deadline": ip.task_deadline.isoformat() if ip.task_deadline else None,
        "review_date": ip.review_date.isoformat() if ip.review_date else None,
        "google_meet_link": ip.google_meet_link,
        "status": ip.status,
        "correction_checklist": ip.correction_checklist,
        "resubmission_deadline": ip.resubmission_deadline.isoformat() if ip.resubmission_deadline else None,
        "submissions": submissions_data,
        "reviews": reviews_data
    }

@router.put("/interns/{intern_id}")
def update_intern_profile(
    intern_id: int,
    update_data: InternUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MENTOR.value])),
    db: Session = Depends(get_db)
):
    ip = db.query(InternProfile).filter(InternProfile.id == intern_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="Intern not found")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(ip, field, value)

    db.add(AuditLog(
        action="INTERN_UPDATED",
        actor_id=current_user.id,
        intern_id=ip.id,
        details=f"Updated intern profile fields: {list(update_data.model_dump(exclude_unset=True).keys())}"
    ))
    db.commit()
    return {"message": "Intern profile updated successfully."}

@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    results = []
    for l in logs:
        results.append(AuditLogOut(
            id=l.id,
            action=l.action,
            actor_id=l.actor_id,
            actor_name=l.actor.full_name if l.actor else "System",
            intern_id=l.intern_id,
            details=l.details,
            timestamp=l.timestamp
        ))
    return results
