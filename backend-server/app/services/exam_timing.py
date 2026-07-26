from datetime import datetime, timedelta, timezone

from ..models import Exam, ExamSession


def ensure_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_session_timing(session: ExamSession, exam: Exam, now: datetime | None = None) -> dict:
    current_time = ensure_aware(now) or datetime.now(timezone.utc)
    started_at = ensure_aware(session.started_at) or ensure_aware(session.created_at) or current_time
    duration_seconds = session.duration if session.duration and session.duration > 0 else (exam.duration or 0) * 60
    ends_at = started_at + timedelta(seconds=duration_seconds)
    remaining_seconds = max(int((ends_at - current_time).total_seconds()), 0)

    return {
        "server_time": current_time,
        "session_started_at": started_at,
        "session_duration_seconds": int(duration_seconds),
        "session_ends_at": ends_at,
        "remaining_seconds": remaining_seconds,
        "is_expired": current_time >= ends_at,
    }
