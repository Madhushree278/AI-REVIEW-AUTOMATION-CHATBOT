# AI-Powered Intern Review Automation System

An enterprise-grade, end-to-end automated internship task assignment, document evaluation, review scheduling, feedback management, and AI chatbot system built for organizations managing 100+ interns.

---

## 🌟 Key Features

1. **Admin Control Center**:
   - Live dashboard metrics: Total Interns (100+), Not Started, In Progress, Submitted for Review, Reviews Scheduled, Reviews Completed, Overdue Deadlines, Corrections Required.
   - Directory management with search, department filtering (AI/ML, Backend, Cloud, Data Science, Frontend, Cybersecurity), status filtering, and sorting.
   - **1-Click Bulk Import**: Upload 100+ interns via CSV or Excel (.xlsx) with instant validation, duplicate email detection, and duplicate Intern ID prevention.
   - Comprehensive audit logging of all system actions, assignments, submissions, and status transitions.

2. **Task & Rubric Management**:
   - Dynamic task authoring: Title, description, expected deliverables, submission format, maximum marks, deadline, and multi-criteria evaluation rubrics.
   - Bulk task assignment to individual interns, entire cohorts, or filtered departments.
   - Background non-blocking email dispatch with personalized task details, deadlines, and portal links.

3. **Document Verification & AI Evaluation Engine**:
   - Multi-format text extraction: PDF (`pypdf`), Word DOCX (`python-docx`), plain code/text files (`.py`, `.js`, `.ts`, `.java`, `.cpp`, `.json`, etc.), and secure ZIP archives.
   - AI Evaluation against exact assigned task rubrics (supports Gemini API, Groq, OpenAI, or smart deterministic heuristic evaluator when external API keys are not configured).
   - Structured JSON evaluation report: Completion percentage, requirement-by-requirement scoring, strengths, missing deliverables, technical errors, suggested corrections, and next steps.
   - **Human-in-the-Loop**: All AI evaluations remain strictly marked as `Provisional` until reviewed, edited, approved, or overridden by an authorized human mentor.
   - Graceful error boundary: Handles 0-byte files, corrupted archives, or unsupported formats without crashing, notifying the intern to re-upload.

4. **Review Scheduling & Google Meet Integration**:
   - Supports manual scheduling with Google Meet validation or automated Google Calendar API (OAuth 2.0).
   - Mentor schedule conflict detection (prevents overlapping meeting appointments).
   - Automated review meeting invitation emails with dates, times, timezones, and direct Google Meet join links.
   - Configurable 24-hour and 1-hour automated reminders with duplicate prevention.

5. **Multi-Cycle Revision Workflow**:
   - Mentor can request corrections by providing an explicit checklist and setting a resubmission deadline.
   - Intern portal surfaces the correction checklist and accepts Version 2+ resubmissions.
   - AI evaluates updated deliverables against original criteria + mentor's correction checklist.
   - Formally close the review cycle upon final mentor approval.

6. **Authenticated AI Intern Chatbot**:
   - Embedded interactive chatbot accessible on the intern portal.
   - Answers natural language questions grounded strictly in the authenticated intern's actual database records:
     - *"What task has been assigned to me?"*
     - *"What is my submission deadline?"*
     - *"When is my next review?"*
     - *"Where can I join my review meeting?"*
     - *"Have I submitted my task?"*
     - *"What corrections should I make?"*
     - *"Can I resubmit my task?"*
   - **Zero Data Leakage Guarantee**: Strictly enforces role isolation; refuses to reveal or hypothesize about other interns or company records.

7. **Email Automation & Duplicate Prevention**:
   - Non-blocking daemon background queue for bulk email dispatch.
   - Configurable providers: Mock/Console mode (local dev/testing), SMTP, or Gmail API.
   - 15 production-ready HTML + plaintext email templates.
   - Complete `EmailLog` database tracking with recipient, subject, status (`SENT`, `FAILED`), content preview, error diagnostics, and one-click retry.

---

## 🏛️ System Architecture

```
AI  REVIEW AUTOMATION/
├── app/
│   ├── config.py             # Environment configuration (Pydantic v2 settings)
│   ├── database.py           # SQLAlchemy engine, session maker, declarative Base
│   ├── models/
│   │   ├── __init__.py
│   │   └── entities.py       # User, InternProfile, Task, Submission, Evaluation, ReviewSchedule, EmailLog, AuditLog
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py        # Pydantic v2 request/response models with ConfigDict
│   ├── core/
│   │   ├── security.py       # Bcrypt password hashing, JWT creation/decoding, RBAC dependencies
│   │   ├── document_parser.py# Multi-format document parser (PDF, DOCX, Code, ZIP)
│   │   ├── ai_evaluator.py   # AI evaluation pipeline (Gemini, Groq, OpenAI, Heuristic fallback)
│   │   ├── email_service.py  # Background email queue, cooldown deduplication, SMTP/Mock dispatcher
│   │   ├── calendar_service.py # Google Meet validation, conflict detection, Google Calendar OAuth
│   │   └── chatbot_rag.py    # Grounded intern assistant with strict record isolation
│   ├── templates/
│   │   └── email_templates.py# 15 customizable HTML/text email templates
│   ├── api/
│   │   ├── auth_routes.py    # Login, registration, token issuance
│   │   ├── admin_routes.py   # Stats, 100+ intern CRUD, bulk CSV/Excel import, audit logs
│   │   ├── task_routes.py    # Task creation, rubric builder, bulk assignment
│   │   ├── intern_routes.py  # Intern dashboard, submission upload, version history
│   │   ├── mentor_routes.py  # Review workspace, feedback approval, correction requests, task closure
│   │   ├── review_routes.py  # Review scheduling, Google Meet validation, reminders
│   │   ├── email_routes.py   # Delivery activity logs, retry endpoint
│   │   └── chat_routes.py    # Authenticated intern chatbot endpoint
│   ├── static/
│   │   ├── index.html        # Modern responsive SPA with persona switcher, tabs, modals, chatbot
│   │   ├── css/styles.css    # Modern corporate styling, glassmorphism, responsive grid
│   │   └── js/app.js         # Reactive SPA controller, quick-switch roles, API client
│   └── main.py               # FastAPI application entrypoint, CORS, static routes, database seeder
├── data/
│   ├── sample_100_interns.csv# 105 realistic intern records across multiple domains for instant import testing
│   ├── sample_submission_v1.py # Realistic Python FastAPI + RAG deliverable
│   └── sample_submission_v2_corrected.py # Corrected Version 2 addressing mentor feedback
├── tests/
│   ├── test_full_workflow.py # Comprehensive test suite covering criteria 1 to 15
│   └── test_security_isolation.py # Data isolation and security test suite covering criterion 16
├── run.py                    # One-command startup script
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
└── README.md                 # Complete system documentation
```

---

## 🔄 Workflow Status Lifecycle

```
[Registered] ──> [Task Assigned] ──> [In Progress] ──> [Submitted]
                                                           │
                                                           ▼
                                               [AI Evaluation Pending]
                                                           │
                                                           ▼
                                             [Mentor Approval Pending]
                                                │                 │
                               (Approved / Meet)│                 │(Corrections)
                                                ▼                 ▼
                                       [Review Scheduled]  [Corrections Required]
                                                │                 │
                                                ▼                 ▼
                                       [Feedback Published] [Resubmitted (V2+)]
                                                │                 │
                                                └────────┬────────┘
                                                         │
                                                         ▼
                                                     [Approved]
                                                         │
                                                         ▼
                                                      [Closed]
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.10+
- Pip

### 2. Installation
Clone the repository or navigate to the directory:
```bash
cd "AI  REVIEW AUTOMATION"
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration (Optional)
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
*Note: The application functions out-of-the-box in local development with SQLite, Mock email logging, and intelligent semantic rubric evaluation without requiring any paid API keys! If you have a `GEMINI_API_KEY`, `GROQ_API_KEY`, or `OPENAI_API_KEY`, you can paste it in `.env` to enable cloud LLM calls.*

### 4. Running the Application
Start the server with one command:
```bash
python run.py
```
Open your browser and navigate to:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

Interactive Swagger REST API Documentation is available at:
**[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 👥 Default Demo Personas & Credentials

The application includes an instant **Persona Switcher** in the top navigation bar for rapid testing:

| Role | Name | Email | Password | Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | System Administrator | `admin@company.com` | `Admin@2026` | Full system control, 100+ intern import, task assignment, review scheduling, audit logs |
| **Mentor** | Sarah Jenkins (AI Lead) | `mentor.sarah@company.com` | `Mentor@2026` | Review workspace, rubric scoring override, feedback approval, correction requests |
| **Mentor** | Alex Rivera (Eng Manager)| `mentor.alex@company.com` | `Mentor@2026` | Mentoring backend & data science cohorts |
| **Intern** | Aarav Patel | `aarav.patel@company.com` | `Intern@2026` | AI/ML Intern: Assigned RAG task, file submission, chatbot, meeting join link |
| **Intern** | Sneha Sharma | `sneha.sharma@company.com` | `Intern@2026` | Backend Intern: Isolated records, personal submissions |

---

## 🧪 Automated Testing & Acceptance Criteria Verification

Run the complete test suite:
```bash
python -m pytest tests/ -v
```

### Acceptance Criteria Test Matrix:

| # | Acceptance Criterion | Test Function | Result |
| :---: | :--- | :--- | :---: |
| 1 | Import 100+ interns without duplicate records | `test_1_import_100_interns_without_duplicates` | **PASSED** |
| 2 | Assign tasks to multiple interns | `test_2_and_3_task_creation_and_bulk_assignment_with_emails` | **PASSED** |
| 3 | Send personalized task emails | `test_2_and_3_task_creation_and_bulk_assignment_with_emails` | **PASSED** |
| 4 | Log in as different interns and verify data isolation | `test_4_intern_login_and_data_isolation` | **PASSED** |
| 5 | Upload and submit a task document (PDF, DOCX, Code, ZIP) | `test_5_6_7_upload_document_and_ai_evaluation` | **PASSED** |
| 6 | Compare document against correct assigned task rubric | `test_5_6_7_upload_document_and_ai_evaluation` | **PASSED** |
| 7 | Generate structured evaluation report (strengths, gaps, score) | `test_5_6_7_upload_document_and_ai_evaluation` | **PASSED** |
| 8 | Gracefully handle unreadable, empty, or invalid files | `test_8_unreadable_and_invalid_document_handling` | **PASSED** |
| 9 | Human mentor can edit scores and approve AI evaluation | `test_9_mentor_edit_and_approve_evaluation` | **PASSED** |
| 10 | Schedule review and send valid Google Meet invitation | `test_10_and_11_schedule_review_and_duplicate_reminder_prevention` | **PASSED** |
| 11 | Send review reminders without duplicate sends | `test_10_and_11_schedule_review_and_duplicate_reminder_prevention` | **PASSED** |
| 12 | Request corrections and accept a new submission (V2) | `test_12_and_13_request_corrections_and_resubmission` | **PASSED** |
| 13 | Schedule subsequent review and notify correct intern | `test_12_and_13_request_corrections_and_resubmission` | **PASSED** |
| 14 | Approve and close a completed task cycle | `test_14_approve_and_close_task` | **PASSED** |
| 15 | Robust error handling, non-blocking email queue, audit logs | `test_15_audit_trail_and_error_handling` | **PASSED** |
| 16 | Strictly verify one intern's data is never leaked to another | `test_16_intern_data_isolation_between_accounts` & `test_chatbot_grounded_qa_and_privacy_guard` | **PASSED** |

---

## 🔒 Security & Privacy Implementation

- **Role-Based Access Control (RBAC)**: All endpoints are protected with JWT bearer tokens and strict role guards (`require_roles([ADMIN, MENTOR])`).
- **Data Isolation**: The `get_current_intern_profile` dependency ensures that interns cannot query or submit for any profile other than their own authenticated account.
- **AI Chatbot Privacy Guard**: The chatbot context is grounded strictly in the calling intern's database row. Any malicious prompt attempting to probe or list other interns' details is actively intercepted and rejected.
- **Upload Security**: Zip-slip path traversal prevention, file size limits (25MB), and whitelist extension checking.
- **Credential Protection**: Passwords hashed using bcrypt; secrets and API keys are stored solely in environment variables and never exposed in frontend code or logs.
