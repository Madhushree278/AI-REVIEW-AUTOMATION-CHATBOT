import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import User, UserRole, InternProfile, Task, AuditLog, WorkflowStatus
from app.schemas.schemas import TaskCreate, TaskUpdate, TaskOut, TaskAssignRequest
from app.core.security import get_current_user, require_roles
from app.core.email_service import queue_email

router = APIRouter(prefix="/api/tasks", tags=["Task Management"])

@router.get("", response_model=List[TaskOut])
def list_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return tasks

@router.post("", response_model=TaskOut)
def create_task(
    data: TaskCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MENTOR.value])),
    db: Session = Depends(get_db)
):
    rubric_json_str = json.dumps([r.model_dump() for r in data.rubric_criteria])
    
    task = Task(
        title=data.title,
        description=data.description,
        deliverables=data.deliverables,
        submission_format=data.submission_format,
        rubric_criteria=rubric_json_str,
        reference_links=data.reference_links,
        deadline=data.deadline,
        max_marks=data.max_marks,
        created_by=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    db.add(AuditLog(
        action="TASK_CREATED",
        actor_id=current_user.id,
        details=f"Created task '{task.title}' (Max marks: {task.max_marks})"
    ))
    db.commit()

    return task

@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task

@router.post("/assign")
def assign_task_to_interns(
    req: TaskAssignRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MENTOR.value])),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == req.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    deadline = req.deadline or task.deadline
    if not deadline:
        deadline = datetime.utcnow()

    assigned_count = 0
    assigned_interns = []

    for intern_id in req.intern_ids:
        intern = db.query(InternProfile).filter(InternProfile.id == intern_id).first()
        if not intern:
            continue

        intern.assigned_task_id = task.id
        intern.task_deadline = deadline
        intern.status = WorkflowStatus.TASK_ASSIGNED.value
        assigned_count += 1
        assigned_interns.append(intern)

        if req.send_email:
            review_info_html = ""
            if intern.review_date:
                review_info_html = f"<p><strong>Review Date:</strong> {intern.review_date.strftime('%Y-%m-%d %H:%M')}</p>"
                if intern.google_meet_link:
                    review_info_html += f"<p><strong>Google Meet Link:</strong> <a href='{intern.google_meet_link}'>{intern.google_meet_link}</a></p>"

            queue_email(
                recipient=intern.user.email,
                template_key="TASK_ASSIGNED",
                context={
                    "intern_name": intern.user.full_name,
                    "intern_id": intern.intern_id,
                    "task_title": task.title,
                    "task_description": task.description,
                    "deliverables": task.deliverables,
                    "submission_format": task.submission_format,
                    "deadline": deadline.strftime("%Y-%m-%d %H:%M"),
                    "review_info": review_info_html
                },
                intern_id=intern.id,
                prevent_duplicate=False
            )

    db.add(AuditLog(
        action="TASK_ASSIGNED",
        actor_id=current_user.id,
        details=f"Assigned task '{task.title}' to {assigned_count} intern(s)."
    ))
    db.commit()

    return {
        "message": f"Successfully assigned '{task.title}' to {assigned_count} intern(s).",
        "assigned_count": assigned_count
    }
