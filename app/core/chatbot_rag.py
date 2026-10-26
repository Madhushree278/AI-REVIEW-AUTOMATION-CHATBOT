import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.config import settings
from app.models.entities import InternProfile, Submission, ReviewSchedule, Evaluation, Task, User

def build_intern_grounded_context(profile: InternProfile, db: Session) -> Dict[str, Any]:
    """
    Constructs a structured, safe context snapshot strictly for the authenticated intern.
    """
    user: User = profile.user
    mentor: Optional[User] = profile.mentor
    assigned_task: Optional[Task] = profile.assigned_task
    
    # Latest submission and evaluation
    latest_sub: Optional[Submission] = None
    sub_count = 0
    if profile.submissions:
        sub_count = len(profile.submissions)
        latest_sub = profile.submissions[0]  # ordered by version desc

    latest_eval: Optional[Evaluation] = None
    if latest_sub and latest_sub.evaluation:
        latest_eval = latest_sub.evaluation

    # Next upcoming review
    upcoming_review: Optional[ReviewSchedule] = None
    for rev in profile.reviews:
        if rev.status in ["Scheduled", "SCHEDULED"]:
            upcoming_review = rev
            break

    context = {
        "intern": {
            "name": user.full_name,
            "intern_id": profile.intern_id,
            "email": user.email,
            "department": profile.department,
            "status": profile.status,
            "mentor_name": mentor.full_name if mentor else "Not yet assigned",
            "mentor_email": mentor.email if mentor else None
        },
        "task": {
            "assigned": bool(assigned_task),
            "title": assigned_task.title if assigned_task else "No task currently assigned",
            "description": assigned_task.description if assigned_task else None,
            "deliverables": assigned_task.deliverables if assigned_task else None,
            "submission_format": assigned_task.submission_format if assigned_task else None,
            "deadline": profile.task_deadline.strftime("%Y-%m-%d %H:%M") if profile.task_deadline else (
                assigned_task.deadline.strftime("%Y-%m-%d %H:%M") if assigned_task and assigned_task.deadline else "No deadline set"
            ),
            "max_marks": assigned_task.max_marks if assigned_task else 100
        },
        "submission": {
            "has_submitted": bool(latest_sub),
            "submission_count": sub_count,
            "latest_version": latest_sub.version if latest_sub else 0,
            "latest_submitted_at": latest_sub.submitted_at.strftime("%Y-%m-%d %H:%M") if latest_sub else None,
            "latest_file_name": latest_sub.file_name if latest_sub else None,
            "status": latest_sub.status if latest_sub else "Not Submitted"
        },
        "evaluation": {
            "has_evaluation": bool(latest_eval),
            "is_provisional": latest_eval.is_provisional if latest_eval else True,
            "mentor_approved": latest_eval.mentor_approved if latest_eval else False,
            "completion_percentage": latest_eval.completion_percentage if latest_eval else None,
            "overall_score": latest_eval.overall_score if latest_eval else None,
            "mentor_notes": latest_eval.mentor_notes if latest_eval else None,
            "missing_items": json.loads(latest_eval.missing_items) if latest_eval and latest_eval.missing_items else [],
            "suggested_corrections": json.loads(latest_eval.suggested_corrections) if latest_eval and latest_eval.suggested_corrections else []
        },
        "corrections": {
            "corrections_required": profile.status == "Corrections Required",
            "checklist": profile.correction_checklist,
            "resubmission_deadline": profile.resubmission_deadline.strftime("%Y-%m-%d %H:%M") if profile.resubmission_deadline else None
        },
        "review_meeting": {
            "has_scheduled_review": bool(upcoming_review),
            "date": upcoming_review.review_date.strftime("%Y-%m-%d") if upcoming_review else None,
            "time": f"{upcoming_review.start_time} - {upcoming_review.end_time} ({upcoming_review.timezone})" if upcoming_review else None,
            "google_meet_link": upcoming_review.google_meet_link if upcoming_review else profile.google_meet_link
        }
    }
    return context

def answer_with_deterministic_grounding(question: str, ctx: Dict[str, Any]) -> str:
    """
    Deterministic query responder matching common intern queries against verified DB context.
    Ensures immediate, accurate responses even without active LLM API credentials.
    """
    q_low = question.lower()
    intern = ctx["intern"]
    task = ctx["task"]
    sub = ctx["submission"]
    ev = ctx["evaluation"]
    rev = ctx["review_meeting"]
    corr = ctx["corrections"]

    # Check for security / privacy violation attempts
    if any(k in q_low for k in ["other intern", "all interns", "another intern", "someone else", "list of interns", "database dump"]):
        return (
            "I cannot provide information about other interns or company-wide records due to privacy and data isolation policies. "
            "I am only authorized to assist you with your own assignments and reviews."
        )

    # 1. Submission deadline (Check deadline first so "submission deadline" is not confused with submission status)
    if any(k in q_low for k in ["deadline", "due date", "when to submit", "when is it due", "submission date", "last date"]):
        if corr["corrections_required"] and corr["resubmission_deadline"]:
            return f"Your current status is **Corrections Required**. Your resubmission deadline is: **{corr['resubmission_deadline']}**."
        return f"The deadline for your assigned task (**{task['title']}**) is: **{task['deadline']}**."

    # 2. Have I submitted my task?
    if any(k in q_low for k in ["have i submitted", "submission status", "did i submit", "is my task submitted", "has my task been submitted", "submitted my task", "status of my submission"]):
        if sub["has_submitted"]:
            return (
                f"Yes, you have submitted **Version {sub['latest_version']}** on **{sub['latest_submitted_at']}**.\n\n"
                f"**File Name:** {sub['latest_file_name']}\n"
                f"**Status:** {sub['status']}\n"
                f"**Overall Internship Status:** {intern['status']}"
            )
        return "You have not submitted any deliverables yet. Please complete your work and upload it through the submission form on your portal."

    # 3. Assigned task
    if any(k in q_low for k in ["what task", "assigned to me", "task assigned", "what is my task", "task title", "which task", "my assigned task"]):
        if not task["assigned"]:
            return f"Hello {intern['name']}, you currently do not have any task assigned. Please contact your mentor ({intern['mentor_name']})."
        return (
            f"You have been assigned the task: **{task['title']}**.\n\n"
            f"**Description:** {task['description']}\n\n"
            f"**Expected Deliverables:** {task['deliverables']}\n"
            f"**Submission Format:** {task['submission_format']}\n"
            f"**Deadline:** {task['deadline']}"
        )

    # 4. Next review / meeting date
    if any(k in q_low for k in ["next review", "when is my review", "review schedule", "review meeting", "review date", "when will i be reviewed"]):
        if rev["has_scheduled_review"]:
            return (
                f"Your next review meeting is scheduled for **{rev['date']}** at **{rev['time']}** with your mentor **{intern['mentor_name']}**.\n\n"
                f"**Google Meet Link:** [{rev['google_meet_link']}]({rev['google_meet_link']})"
            )
        return "You do not have a review scheduled yet. Your mentor will schedule one once your task deliverables are reviewed."

    # 5. Where can I join my review meeting?
    if any(k in q_low for k in ["where can i join", "join my review", "meet link", "google meet", "meeting link", "join meeting"]):
        if rev["google_meet_link"]:
            return (
                f"You can join your Google Meet review meeting using this link:\n\n"
                f"🔗 [{rev['google_meet_link']}]({rev['google_meet_link']})\n\n"
                f"**Scheduled Time:** {rev['date'] or 'Upcoming'} at {rev['time'] or 'Check Portal'}"
            )
        return "No Google Meet link has been generated yet for your review. Your mentor will provide one prior to your session."

    # 6. What corrections should I make?
    if any(k in q_low for k in ["what correction", "corrections", "mentor feedback", "what should i fix", "what went wrong", "changes needed"]):
        if corr["corrections_required"]:
            return (
                f"Your mentor has requested corrections for your submission:\n\n"
                f"**Correction Checklist:**\n{corr['checklist']}\n\n"
                f"**Resubmission Deadline:** {corr['resubmission_deadline']}"
            )
        if ev["has_evaluation"]:
            feedback = f"Your latest AI evaluation is **{ev['completion_percentage']}% complete**"
            if ev["overall_score"] is not None:
                feedback += f" with a score of {ev['overall_score']}"
            if ev["mentor_notes"]:
                feedback += f".\n\n**Mentor Feedback:** {ev['mentor_notes']}"
            if ev["suggested_corrections"]:
                feedback += f"\n\n**Suggested Improvements:**\n- " + "\n- ".join(ev["suggested_corrections"])
            return feedback
        return "No specific corrections or evaluations are currently recorded. Ensure your deliverables cover all task requirements."

    # 7. Can I resubmit my task?
    if any(k in q_low for k in ["can i resubmit", "allow resubmit", "resubmission", "upload again", "submit again"]):
        if corr["corrections_required"]:
            return (
                f"Yes! Resubmission is explicitly permitted and requested. Please review your correction checklist and upload Version {sub['latest_version'] + 1} before **{corr['resubmission_deadline']}**."
            )
        if intern["status"] in ["Task Assigned", "In Progress", "Submitted"]:
            return "Yes, you can upload updated deliverables on your intern portal as needed before mentor review completion."
        if intern["status"] == "Approved":
            return "Your task has already been officially approved by your mentor. Resubmission is not required."
        return "You may submit updated deliverables directly through the upload section on your portal."

    # General greeting or overview
    return (
        f"Hello {intern['name']}! I am your AI Internship Review Assistant. Here is your current overview:\n\n"
        f"• **Assigned Task:** {task['title']}\n"
        f"• **Deadline:** {task['deadline']}\n"
        f"• **Status:** {intern['status']}\n"
        f"• **Assigned Mentor:** {intern['mentor_name']}\n"
        f"• **Upcoming Review:** {rev['date'] or 'Not scheduled yet'}\n\n"
        f"Feel free to ask me questions like 'What is my deadline?', 'Where is my Google Meet link?', or 'What corrections should I make?'."
    )

def ask_intern_chatbot(profile: InternProfile, question: str, db: Session) -> Dict[str, Any]:
    """
    Main chatbot handler for the intern.
    """
    ctx = build_intern_grounded_context(profile, db)
    
    # Try LLM if configured
    if settings.GEMINI_API_KEY and settings.LLM_PROVIDER in ["auto", "gemini"]:
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            system_prompt = f"""
You are the AI Intern Assistant for an internship program.
Answer the intern's question accurately using ONLY the grounded context provided below.
CRITICAL SECURITY:
- Only answer questions regarding this intern ({ctx['intern']['name']}, ID: {ctx['intern']['intern_id']}).
- Under NO circumstance reveal data or hypothesize about other interns or company systems.
- Be concise, supportive, professional, and clear.

GROUNDED INTERN RECORD:
{json.dumps(ctx, indent=2)}
"""
            resp = client.models.generate_content(
                model=settings.LLM_MODEL or "gemini-2.0-flash",
                contents=f"{system_prompt}\n\nIntern's Question: {question}"
            )
            if resp and resp.text:
                return {
                    "answer": resp.text.strip(),
                    "grounded_context": ctx
                }
        except Exception as e:
            print(f"[Chatbot LLM Error] {e}")

    # Fallback to intelligent deterministic grounding
    answer = answer_with_deterministic_grounding(question, ctx)
    return {
        "answer": answer,
        "grounded_context": ctx
    }
