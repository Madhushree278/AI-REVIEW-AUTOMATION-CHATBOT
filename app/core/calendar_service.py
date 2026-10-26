import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.config import settings
from app.models.entities import ReviewSchedule

GOOGLE_MEET_REGEX = re.compile(r"^https?://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}$", re.IGNORECASE)

def validate_google_meet_link(link: str) -> bool:
    """Checks whether the provided URL matches a valid Google Meet link format."""
    if not link:
        return False
    return bool(GOOGLE_MEET_REGEX.match(link.strip())) or "meet.google.com" in link.lower()

def check_mentor_schedule_conflict(
    db: Session,
    mentor_id: int,
    review_date: datetime,
    start_time: str,
    end_time: str,
    exclude_review_id: Optional[int] = None
) -> Optional[ReviewSchedule]:
    """
    Checks if the mentor already has a scheduled review during the same time slot.
    Avoids overlapping appointments.
    """
    # Query reviews for this mentor on the same date
    target_date = review_date.date()
    query = db.query(ReviewSchedule).filter(
        ReviewSchedule.mentor_id == mentor_id,
        ReviewSchedule.status.in_(["Scheduled", "SCHEDULED"])
    )
    if exclude_review_id:
        query = query.filter(ReviewSchedule.id != exclude_review_id)
        
    existing_reviews = query.all()
    for rev in existing_reviews:
        if rev.review_date.date() == target_date:
            # Overlap check between [start_time, end_time] and [rev.start_time, rev.end_time]
            if start_time < rev.end_time and end_time > rev.start_time:
                return rev
    return None

def create_google_calendar_event(
    mentor_email: str,
    intern_email: str,
    summary: str,
    description: str,
    start_dt: datetime,
    end_dt: datetime,
    timezone: str = "Asia/Kolkata"
) -> Dict[str, Any]:
    """
    Creates an event on Google Calendar and requests Google Meet conference data
    using OAuth 2.0 refresh credentials if configured.
    If not configured, returns clear unconfigured status without inventing fake links.
    """
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET and settings.GOOGLE_REFRESH_TOKEN):
        return {
            "success": False,
            "error": "Google Calendar API OAuth2 credentials are not configured. Please supply a Google Meet link manually.",
            "meet_link": None,
            "event_id": None
        }

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=None,
            refresh_token=settings.GOOGLE_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        service = build("calendar", "v3", credentials=creds)

        event_body = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": timezone,
            },
            "attendees": [
                {"email": mentor_email},
                {"email": intern_email}
            ],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-rev-{int(datetime.utcnow().timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        }

        created = service.events().insert(
            calendarId="primary",
            body=event_body,
            conferenceDataVersion=1
        ).execute()

        meet_link = created.get("hangoutLink")
        event_id = created.get("id")

        return {
            "success": True,
            "error": None,
            "meet_link": meet_link,
            "event_id": event_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Google Calendar API invocation failed: {str(e)}",
            "meet_link": None,
            "event_id": None
        }
