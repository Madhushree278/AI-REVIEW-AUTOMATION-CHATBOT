import os
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app, seed_initial_database
from app.database import Base, engine, SessionLocal
from app.models.entities import User, InternProfile, Task, Submission, ReviewSchedule, EmailLog
from app.core.email_service import email_queue

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    seed_initial_database()
    yield

def get_auth_token(email: str, password: str = "Admin@2026"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]

def test_1_import_100_interns_without_duplicates():
    """Criterion 1: Import 100+ interns from CSV without duplicate records."""
    admin_token = get_auth_token("admin@company.com", "Admin@2026")
    headers = {"Authorization": f"Bearer {admin_token}"}

    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_100_interns.csv")
    assert os.path.exists(csv_path), "Sample CSV file must exist"

    with open(csv_path, "rb") as f:
        response = client.post(
            "/api/admin/interns/import",
            headers=headers,
            files={"file": ("sample_100_interns.csv", f, "text/csv")}
        )

    assert response.status_code == 200, f"Import failed: {response.text}"
    data = response.json()
    assert data["successful_imports"] >= 100, f"Expected 100+ imports, got {data['successful_imports']}"
    assert data["failed_imports"] == 0, "No rows should fail format parsing"

    # Test Deduplication: Re-uploading same file must skip duplicates
    with open(csv_path, "rb") as f2:
        dup_response = client.post(
            "/api/admin/interns/import",
            headers=headers,
            files={"file": ("sample_100_interns.csv", f2, "text/csv")}
        )
    assert dup_response.status_code == 200
    dup_data = dup_response.json()
    assert dup_data["successful_imports"] == 0, "All rows in second upload must be skipped as duplicates"
    assert dup_data["duplicate_emails_skipped"] >= 100, "All emails should be marked duplicate"

def test_2_and_3_task_creation_and_bulk_assignment_with_emails():
    """Criteria 2 & 3: Create task with rubric, assign to multiple interns, and trigger personalized emails."""
    admin_token = get_auth_token("admin@company.com", "Admin@2026")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create Task
    task_payload = {
        "title": "Cloud Microservices Security Benchmark",
        "description": "Implement authentication guards, API rate limiting, and encrypted payload parsing.",
        "deliverables": "1. Python microservice.\n2. Security benchmark report.",
        "submission_format": "PDF, DOCX, ZIP, or Code Files",
        "rubric_criteria": [
            {"requirement": "Authentication Security", "description": "JWT validation and role guards", "max_marks": 50},
            {"requirement": "Rate Limiting & Logging", "description": "Throttle limits and audit logs", "max_marks": 50}
        ],
        "max_marks": 100
    }
    task_res = client.post("/api/tasks", headers=headers, json=task_payload)
    assert task_res.status_code == 200
    task_id = task_res.json()["id"]

    # Assign to 5 interns
    interns_res = client.get("/api/admin/interns?limit=5", headers=headers)
    assert interns_res.status_code == 200
    intern_ids = [i["id"] for i in interns_res.json()["interns"][:5]]
    assert len(intern_ids) >= 3

    assign_res = client.post("/api/tasks/assign", headers=headers, json={
        "task_id": task_id,
        "intern_ids": intern_ids,
        "deadline": (datetime.utcnow() + timedelta(days=5)).isoformat(),
        "send_email": True
    })
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned_count"] == len(intern_ids)

    # Wait for background queue worker to drain
    email_queue.join()

    # Verify email logs were generated in background
    email_logs_res = client.get("/api/emails/logs?email_type=TASK_ASSIGNED", headers=headers)
    assert email_logs_res.status_code == 200
    assert len(email_logs_res.json()) >= len(intern_ids), "Personalized emails must be logged in EmailLog"

def test_4_intern_login_and_data_isolation():
    """Criterion 4: Log in as different interns and verify data isolation."""
    token_aarav = get_auth_token("aarav.patel@company.com", "Intern@2026")
    token_sneha = get_auth_token("sneha.sharma@company.com", "Intern@2026")

    headers_aarav = {"Authorization": f"Bearer {token_aarav}"}
    headers_sneha = {"Authorization": f"Bearer {token_sneha}"}

    dash_aarav = client.get("/api/intern/dashboard", headers=headers_aarav).json()
    dash_sneha = client.get("/api/intern/dashboard", headers=headers_sneha).json()

    # Verify each intern receives ONLY their own record
    assert dash_aarav["intern_info"]["email"] == "aarav.patel@company.com"
    assert dash_aarav["intern_info"]["intern_id"] == "INT-2026-001"

    assert dash_sneha["intern_info"]["email"] == "sneha.sharma@company.com"
    assert dash_sneha["intern_info"]["intern_id"] == "INT-2026-002"

    assert dash_aarav["intern_info"]["intern_id"] != dash_sneha["intern_info"]["intern_id"]

def test_5_6_7_upload_document_and_ai_evaluation():
    """Criteria 5, 6, 7: Upload deliverable, compare with rubric, and generate structured evaluation report."""
    token_aarav = get_auth_token("aarav.patel@company.com", "Intern@2026")
    headers = {"Authorization": f"Bearer {token_aarav}"}

    sub_file_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_submission_v1.py")
    assert os.path.exists(sub_file_path)

    with open(sub_file_path, "rb") as f:
        res = client.post(
            "/api/intern/submit",
            headers=headers,
            files={"file": ("sample_submission_v1.py", f, "text/x-python")},
            data={"description": "Implemented FastAPI microservice with RAG search"}
        )

    assert res.status_code == 200, f"Submission failed: {res.text}"
    data = res.json()
    assert data["version"] == 1
    ai_report = data["ai_provisional_report"]

    # Verify structured evaluation report schema
    assert "overall_score" in ai_report
    assert "completion_percentage" in ai_report
    assert "requirement_evaluations" in ai_report
    assert "completed_items" in ai_report
    assert "missing_items" in ai_report
    assert "strengths" in ai_report
    assert ai_report["is_provisional"] is True, "AI evaluation must be provisional initially"

def test_8_unreadable_and_invalid_document_handling():
    """Criterion 8: Gracefully handle unreadable, empty, or unsupported files."""
    token_aarav = get_auth_token("aarav.patel@company.com", "Intern@2026")
    headers = {"Authorization": f"Bearer {token_aarav}"}

    # Empty 0-byte file
    res_empty = client.post(
        "/api/intern/submit",
        headers=headers,
        files={"file": ("empty.txt", b"", "text/plain")},
        data={"description": "Testing empty file"}
    )
    assert res_empty.status_code == 422, "Empty file should trigger 422 Unprocessable Entity"
    assert "empty" in res_empty.json()["detail"].lower()

    # Unsupported file extension
    res_unsupported = client.post(
        "/api/intern/submit",
        headers=headers,
        files={"file": ("binary.exe", b"binary content...", "application/octet-stream")},
        data={"description": "Testing unsupported file"}
    )
    assert res_unsupported.status_code == 400
    assert "not permitted" in res_unsupported.json()["detail"].lower()

def test_9_mentor_edit_and_approve_evaluation():
    """Criterion 9: Mentor reviews, edits rubric score, and approves evaluation."""
    mentor_token = get_auth_token("mentor.sarah@company.com", "Mentor@2026")
    headers = {"Authorization": f"Bearer {mentor_token}"}

    # Check mentor workspace
    ws_res = client.get("/api/mentor/workspace", headers=headers)
    assert ws_res.status_code == 200
    pending = ws_res.json()["pending_submissions"]
    assert len(pending) > 0, "Should have pending submission from Aarav"

    eval_id = pending[0]["evaluation_id"]

    # Approve with edited score and mentor notes
    approve_res = client.post(
        f"/api/mentor/evaluations/{eval_id}/approve",
        headers=headers,
        json={
            "overall_score": 88.5,
            "mentor_notes": "Great clean modular architecture. Solid RAG implementation.",
            "approve_evaluation": True,
            "update_status_to_approved": False
        }
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "Feedback Published"
    assert approve_res.json()["score"] == 88.5

def test_10_and_11_schedule_review_and_duplicate_reminder_prevention():
    """Criteria 10 & 11: Schedule review with Google Meet and verify duplicate reminder prevention."""
    admin_token = get_auth_token("admin@company.com", "Admin@2026")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get intern profile ID for Aarav
    intern_res = client.get("/api/admin/interns?search=aarav", headers=headers)
    intern_id = intern_res.json()["interns"][0]["id"]

    # Schedule review
    review_date = (datetime.utcnow() + timedelta(days=2)).isoformat()
    rev_res = client.post("/api/reviews", headers=headers, json={
        "intern_id": intern_id,
        "mentor_id": 2,  # Mentor Sarah
        "review_date": review_date,
        "start_time": "15:00",
        "end_time": "15:45",
        "timezone": "Asia/Kolkata",
        "google_meet_link": "https://meet.google.com/qwe-rtyu-iop",
        "notes": "Discuss RAG indexing and production scaling",
        "send_invitation_email": True
    })
    assert rev_res.status_code == 200
    review_id = rev_res.json()["id"]
    assert rev_res.json()["google_meet_link"] == "https://meet.google.com/qwe-rtyu-iop"

    # Send 24h reminder
    rem1 = client.post(f"/api/reviews/{review_id}/send-reminder?reminder_type=24h", headers=headers)
    assert rem1.status_code == 200
    assert "sent successfully" in rem1.json()["message"]

    # Duplicate reminder check
    rem2 = client.post(f"/api/reviews/{review_id}/send-reminder?reminder_type=24h", headers=headers)
    assert rem2.status_code == 200
    assert "already sent" in rem2.json()["message"], "Duplicate reminder must be prevented"

def test_12_and_13_request_corrections_and_resubmission():
    """Criteria 12 & 13: Request corrections, notify intern with next review, accept Version 2."""
    mentor_token = get_auth_token("mentor.sarah@company.com", "Mentor@2026")
    headers_mentor = {"Authorization": f"Bearer {mentor_token}"}

    intern_res = client.get("/api/admin/interns?search=aarav", headers=headers_mentor)
    intern_id = intern_res.json()["interns"][0]["id"]

    # Request corrections
    corr_res = client.post(
        f"/api/mentor/interns/{intern_id}/request-corrections",
        headers=headers_mentor,
        json={
            "checklist": "1. Add structured try/except error boundary.\n2. Add automated unit test asserting output format.",
            "resubmission_deadline": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "next_review_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
            "google_meet_link": "https://meet.google.com/qwe-rtyu-iop"
        }
    )
    assert corr_res.status_code == 200
    assert corr_res.json()["status"] == "Corrections Required"

    # Intern uploads Version 2 (Corrected deliverable)
    token_aarav = get_auth_token("aarav.patel@company.com", "Intern@2026")
    headers_intern = {"Authorization": f"Bearer {token_aarav}"}

    v2_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_submission_v2_corrected.py")
    with open(v2_path, "rb") as f2:
        sub2_res = client.post(
            "/api/intern/submit",
            headers=headers_intern,
            files={"file": ("sample_submission_v2_corrected.py", f2, "text/x-python")},
            data={"description": "Version 2 addressing mentor checklist: added try/except and unit test."}
        )

    assert sub2_res.status_code == 200
    assert sub2_res.json()["version"] == 2
    # Verify correction checklist items were verified by AI
    ai_report_v2 = sub2_res.json()["ai_provisional_report"]
    assert any("Correction Resolved" in item for item in ai_report_v2["completed_items"])

def test_14_approve_and_close_task():
    """Criterion 14: Approve final submission and close task cycle."""
    mentor_token = get_auth_token("mentor.sarah@company.com", "Mentor@2026")
    headers = {"Authorization": f"Bearer {mentor_token}"}

    intern_res = client.get("/api/admin/interns?search=aarav", headers=headers)
    intern_id = intern_res.json()["interns"][0]["id"]

    close_res = client.post(f"/api/mentor/interns/{intern_id}/close-task", headers=headers)
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "Closed"

def test_15_audit_trail_and_error_handling():
    """Criterion 15: Verify complete audit trail of actions taken."""
    admin_token = get_auth_token("admin@company.com", "Admin@2026")
    headers = {"Authorization": f"Bearer {admin_token}"}

    audit_res = client.get("/api/admin/audit-logs?limit=20", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0

    actions = [l["action"] for l in logs]
    assert any(a in actions for a in ["BULK_INTERN_IMPORT", "TASK_CREATED", "TASK_ASSIGNED", "TASK_SUBMITTED", "EVALUATION_APPROVED"])
