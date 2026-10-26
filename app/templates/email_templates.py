from typing import Dict, Any

TEMPLATES = {
    "WELCOME": {
        "subject": "Welcome to the Internship Program - Account Activation",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #4f46e5;">Welcome to {company_name}, {intern_name}!</h2>
            <p>Your intern account has been successfully created.</p>
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <p><strong>Intern ID:</strong> {intern_id}</p>
                <p><strong>Department:</strong> {department}</p>
                <p><strong>Portal Link:</strong> <a href="{portal_url}" style="color: #4f46e5;">{portal_url}</a></p>
                <p><strong>Temporary Password:</strong> {default_password}</p>
            </div>
            <p>Please log in and view your onboarding tasks.</p>
            <p>Best regards,<br>Internship Coordination Team</p>
        </div>
        """,
        "body_text": "Welcome to {company_name}, {intern_name}!\nYour Intern ID: {intern_id}\nPortal: {portal_url}\nTemporary Password: {default_password}"
    },
    "TASK_ASSIGNED": {
        "subject": "New Task Assigned: {task_title} (Intern ID: {intern_id})",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <div style="background-color: #4f46e5; color: white; padding: 12px 20px; border-radius: 6px;">
                <h2 style="margin: 0;">Task Assignment Notice</h2>
            </div>
            <p style="margin-top: 15px;">Hello <strong>{intern_name}</strong> (ID: {intern_id}),</p>
            <p>You have been assigned a new task: <strong>{task_title}</strong></p>
            
            <div style="background-color: #f8fafc; padding: 15px; border-left: 4px solid #4f46e5; margin: 15px 0;">
                <p><strong>Description:</strong> {task_description}</p>
                <p><strong>Expected Deliverables:</strong> {deliverables}</p>
                <p><strong>Submission Format:</strong> {submission_format}</p>
                <p><strong>Submission Deadline:</strong> <span style="color: #dc2626; font-weight: bold;">{deadline}</span></p>
                {review_info}
            </div>
            
            <p>Please review the rubric and submit your completed deliverables before the deadline via the portal below:</p>
            <p style="text-align: center; margin: 25px 0;">
                <a href="{portal_url}" style="background-color: #4f46e5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Submit Task Deliverables</a>
            </p>
            <p>If you have any questions, you can ask the AI assistant in your portal or contact your mentor.</p>
        </div>
        """,
        "body_text": "Hello {intern_name} (ID: {intern_id}),\n\nYou have been assigned: {task_title}\nDeadline: {deadline}\nDeliverables: {deliverables}\nPortal: {portal_url}"
    },
    "DEADLINE_REMINDER": {
        "subject": "REMINDER: Task Deadline Approaching for {task_title}",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #d97706;">Deadline Reminder: {task_title}</h3>
            <p>Dear {intern_name},</p>
            <p>This is a reminder that your task deadline is approaching on <strong>{deadline}</strong>.</p>
            <p>Please upload your deliverables on the intern portal in time to avoid marking as overdue.</p>
            <p><a href="{portal_url}" style="color: #4f46e5; font-weight: bold;">Go to Intern Portal</a></p>
        </div>
        """,
        "body_text": "Reminder: Deadline for {task_title} is {deadline}. Portal: {portal_url}"
    },
    "SUBMISSION_CONFIRMATION": {
        "subject": "Submission Received: {task_title} (Version {version})",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #16a34a;">Task Deliverable Upload Confirmed</h3>
            <p>Dear {intern_name},</p>
            <p>Your submission for <strong>{task_title}</strong> (Version {version}) has been successfully received.</p>
            <p><strong>File:</strong> {file_name} ({file_size_kb} KB)</p>
            <p>Our automated AI verification system is currently reviewing your document against the task rubric. Your assigned mentor will review the evaluation shortly.</p>
            <p><a href="{portal_url}" style="color: #4f46e5;">Check Submission Status</a></p>
        </div>
        """,
        "body_text": "Submission confirmed for {task_title} (Version {version}). File: {file_name}. Portal: {portal_url}"
    },
    "SUBMISSION_ERROR": {
        "subject": "Action Required: Error Processing Submission for {task_title}",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #dc2626;">Submission Processing Notice</h3>
            <p>Dear {intern_name},</p>
            <p>We encountered an issue reading your uploaded file for <strong>{task_title}</strong>:</p>
            <blockquote style="background-color: #fee2e2; padding: 10px; border-left: 4px solid #ef4444; color: #991b1b;">
                {error_message}
            </blockquote>
            <p>Please re-upload a readable version (PDF, DOCX, ZIP, or plain code file) via the portal.</p>
        </div>
        """,
        "body_text": "Error processing {task_title}: {error_message}. Please re-upload via portal: {portal_url}"
    },
    "REVIEW_SCHEDULED": {
        "subject": "Review Meeting Scheduled: {task_title} on {review_date}",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #4f46e5;">Internship Review Meeting Scheduled</h2>
            <p>Dear {intern_name},</p>
            <p>Your performance review for <strong>{task_title}</strong> has been scheduled with your mentor <strong>{mentor_name}</strong>.</p>
            
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <p><strong>Date:</strong> {review_date}</p>
                <p><strong>Time:</strong> {start_time} - {end_time} ({timezone})</p>
                <p><strong>Google Meet Link:</strong> <a href="{meet_link}" style="color: #2563eb; font-weight: bold;">{meet_link}</a></p>
                <p><strong>Notes:</strong> {notes}</p>
            </div>
            
            <p style="text-align: center; margin: 20px 0;">
                <a href="{meet_link}" style="background-color: #16a34a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Join Google Meet Meeting</a>
            </p>
            <p>Please ensure you are punctual and have your submitted deliverables open for presentation.</p>
        </div>
        """,
        "body_text": "Review Scheduled for {task_title}.\nDate: {review_date} {start_time}-{end_time} ({timezone})\nGoogle Meet: {meet_link}\nMentor: {mentor_name}"
    },
    "REVIEW_REMINDER": {
        "subject": "Meeting Reminder: Intern Review in {time_remaining}",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #2563eb;">Reminder: Review Meeting Starting in {time_remaining}</h3>
            <p>Dear {intern_name},</p>
            <p>Your review meeting for <strong>{task_title}</strong> is starting soon.</p>
            <p><strong>Meeting Time:</strong> {review_date} at {start_time} ({timezone})</p>
            <p><a href="{meet_link}" style="background-color: #2563eb; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">Join Google Meet Now</a></p>
        </div>
        """,
        "body_text": "Reminder: Review meeting starting in {time_remaining} at {start_time}. Google Meet: {meet_link}"
    },
    "AI_EVAL_READY": {
        "subject": "Action Needed: AI Evaluation Ready for Mentor Review ({intern_id})",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #4f46e5;">New Submission Awaiting Mentor Review</h3>
            <p>Mentor {mentor_name},</p>
            <p>Intern <strong>{intern_name}</strong> ({intern_id}) has submitted deliverables for <strong>{task_title}</strong>.</p>
            <p>The AI provisional evaluation is ready: <strong>{completion_percentage}% completion</strong> (Provisional Score: {score}/{max_score}).</p>
            <p>Please log in to your Mentor Workspace to review, edit, and approve the evaluation.</p>
        </div>
        """,
        "body_text": "New submission from {intern_name} ({intern_id}) for {task_title}. AI Completion: {completion_percentage}%. Please review."
    },
    "FEEDBACK_PUBLISHED": {
        "subject": "Feedback Published for {task_title}",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #4f46e5;">Mentor Feedback Available</h3>
            <p>Dear {intern_name},</p>
            <p>Your mentor has reviewed your submission for <strong>{task_title}</strong> and published official feedback.</p>
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <p><strong>Score:</strong> {score} / {max_score}</p>
                <p><strong>Mentor Comments:</strong></p>
                <blockquote style="margin: 0; padding-left: 10px; border-left: 3px solid #6366f1;">{mentor_notes}</blockquote>
            </div>
            <p><a href="{portal_url}" style="color: #4f46e5; font-weight: bold;">View Full Evaluation Report</a></p>
        </div>
        """,
        "body_text": "Feedback published for {task_title}. Score: {score}/{max_score}. Comments: {mentor_notes}. View at: {portal_url}"
    },
    "CORRECTIONS_REQUIRED": {
        "subject": "Corrections Required for {task_title} - Next Review Scheduled",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #e11d48;">Corrections Required for {task_title}</h2>
            <p>Dear {intern_name},</p>
            <p>Your mentor has reviewed your submission and requested the following corrections before final approval:</p>
            
            <div style="background-color: #fff1f2; padding: 15px; border-left: 4px solid #f43f5e; margin: 15px 0;">
                <p><strong>Correction Checklist:</strong></p>
                <pre style="white-space: pre-wrap; font-family: inherit;">{checklist}</pre>
                <p><strong>Resubmission Deadline:</strong> <span style="color: #e11d48; font-weight: bold;">{resubmission_deadline}</span></p>
            </div>
            {next_review_info}
            <p>Please update your work and upload a Version 2 deliverable via your intern portal.</p>
            <p><a href="{portal_url}" style="color: #4f46e5; font-weight: bold;">Open Intern Portal</a></p>
        </div>
        """,
        "body_text": "Corrections required for {task_title}.\nChecklist:\n{checklist}\nResubmission Deadline: {resubmission_deadline}\nPortal: {portal_url}"
    },
    "RESUBMISSION_CONFIRMATION": {
        "subject": "Resubmission Received: {task_title} (Version {version})",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #16a34a;">Resubmission (Version {version}) Received</h3>
            <p>Dear {intern_name},</p>
            <p>Your corrected deliverable for <strong>{task_title}</strong> has been uploaded. AI is verifying against your correction checklist.</p>
        </div>
        """,
        "body_text": "Resubmission (Version {version}) received for {task_title}."
    },
    "NEXT_REVIEW_SCHEDULED": {
        "subject": "Next Review Scheduled: {task_title}",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #4f46e5;">Follow-up Review Scheduled</h3>
            <p>Dear {intern_name},</p>
            <p>A subsequent review for <strong>{task_title}</strong> has been scheduled for <strong>{review_date}</strong> at {start_time} ({timezone}).</p>
            <p><strong>Google Meet Link:</strong> <a href="{meet_link}">{meet_link}</a></p>
        </div>
        """,
        "body_text": "Follow-up review for {task_title} scheduled on {review_date} at {start_time}. Google Meet: {meet_link}"
    },
    "TASK_APPROVED": {
        "subject": "Congratulations! Task Approved: {task_title}",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #16a34a;">Task Successfully Approved!</h2>
            <p>Dear {intern_name},</p>
            <p>Congratulations! Your mentor has approved your final submission for <strong>{task_title}</strong>.</p>
            <p><strong>Final Score:</strong> {score} / {max_score}</p>
            <p>Your task review cycle is now formally closed with honors.</p>
        </div>
        """,
        "body_text": "Congratulations! Task {task_title} has been officially approved. Final Score: {score}/{max_score}."
    },
    "OVERDUE_TASK": {
        "subject": "Urgent: Task Overdue for {task_title}",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #dc2626;">Task Submission Overdue</h3>
            <p>Dear {intern_name},</p>
            <p>The deadline for <strong>{task_title}</strong> ({deadline}) has passed without a confirmed submission.</p>
            <p>Please submit your work immediately or contact your mentor.</p>
        </div>
        """,
        "body_text": "Urgent: Task {task_title} is overdue. Please submit immediately."
    },
    "REVIEW_CANCELLED": {
        "subject": "Notice: Review Meeting Rescheduled/Cancelled for {task_title}",
        "body_html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #64748b;">Review Meeting Update</h3>
            <p>Dear {intern_name},</p>
            <p>The review meeting previously scheduled for {review_date} has been updated or rescheduled by your mentor.</p>
            <p>Please check your intern portal for the latest schedule.</p>
        </div>
        """,
        "body_text": "Review meeting for {task_title} has been updated. Check portal: {portal_url}"
    }
}

def render_email(template_key: str, context: Dict[str, Any]) -> Dict[str, str]:
    tmpl = TEMPLATES.get(template_key)
    if not tmpl:
        raise ValueError(f"Unknown email template key: {template_key}")
    
    # Fill in defaults if not provided
    full_context = {
        "company_name": "Tech Corp Internships",
        "portal_url": "http://localhost:8000",
        "review_info": "",
        "next_review_info": "",
        "notes": "",
        "default_password": "Intern@2026",
        **context
    }
    
    subject = tmpl["subject"].format(**full_context)
    body_html = tmpl["body_html"].format(**full_context)
    body_text = tmpl["body_text"].format(**full_context)
    
    return {
        "subject": subject,
        "body_html": body_html,
        "body_text": body_text
    }
