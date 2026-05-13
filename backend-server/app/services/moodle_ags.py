from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

import jwt
from sqlalchemy.orm import Session

from ..models import Exam, ExamSession, Submission

AGS_SCOPE_LINEITEM = "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem"
AGS_SCOPE_LINEITEM_READONLY = "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly"
AGS_SCOPE_SCORE = "https://purl.imsglobal.org/spec/lti-ags/scope/score"
DEFAULT_AGS_SCOPES = [AGS_SCOPE_LINEITEM, AGS_SCOPE_SCORE]


def _load_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _decode_launch(session: ExamSession) -> dict[str, Any]:
    if not session.raw_jwt:
        return {}
    return jwt.decode(session.raw_jwt, options={"verify_signature": False})


def _client_id(payload: dict[str, Any]) -> str | None:
    audience = payload.get("aud")
    if isinstance(audience, list):
        return audience[0] if audience else None
    return audience


def _ags_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    endpoint = payload.get("https://purl.imsglobal.org/spec/lti-ags/claim/endpoint", {})
    return endpoint if isinstance(endpoint, dict) else {}


def _score_from_session_submissions(submissions: list[Submission]) -> float:
    latest_scores: dict[int, float] = {}
    for submission in sorted(submissions, key=lambda item: (item.submitted_at or datetime.min.replace(tzinfo=timezone.utc), item.submission_id)):
        latest_scores[submission.question_id] = submission.score or 0.0

    if not latest_scores:
        return 0.0

    return round(sum(latest_scores.values()) / len(latest_scores), 2)


def _request_json(url: str, method: str, headers: dict[str, str] | None = None, data: dict[str, Any] | None = None) -> tuple[int, dict[str, str], str]:
    request_headers = headers or {}
    request_data = None if data is None else json.dumps(data).encode("utf-8")
    if request_data is not None:
        request_headers.setdefault("Content-Type", "application/json")

    request = Request(url, data=request_data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, dict(response.headers.items()), response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, dict(exc.headers.items()) if exc.headers else {}, exc.read().decode("utf-8")


def _get_access_token(token_endpoint: str, client_id: str, private_key: bytes, scope_values: list[str]) -> tuple[str | None, str]:
    now = int(time.time())
    assertion = jwt.encode(
        {
            "iss": client_id,
            "sub": client_id,
            "aud": token_endpoint,
            "iat": now,
            "exp": now + 300,
            "jti": str(uuid.uuid4()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "proctoride-key-1"},
    )

    form_data = {
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": assertion,
        "scope": " ".join(scope_values) if scope_values else " ".join(DEFAULT_AGS_SCOPES),
    }

    request = Request(
        token_endpoint,
        data=urlencode(form_data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            token_payload = json.loads(response.read().decode("utf-8"))
            return token_payload.get("access_token"), ""
    except Exception as exc:
        return None, str(exc)


def _create_lineitem(lineitems_url: str, access_token: str, exam: Exam) -> tuple[str | None, str]:
    payload = {
        "label": exam.title,
        "resourceId": str(exam.exam_id),
        "scoreMaximum": 100,
    }
    status, headers, body = _request_json(
        lineitems_url,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.ims.lis.v2.lineitem+json",
        },
        data=payload,
    )
    if status not in (200, 201):
        return None, body or f"Line item creation failed with status {status}"

    location = headers.get("Location")
    if location:
        return location, ""

    try:
        created_payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        created_payload = {}

    return created_payload.get("id") or created_payload.get("lineItem"), ""


def _push_score(lineitem_url: str, access_token: str, user_id: str, score: float) -> tuple[bool, str]:
    parsed_url = urlparse(lineitem_url)
    score_path = parsed_url.path.rstrip("/") + "/scores"
    score_url = urlunparse((parsed_url.scheme, parsed_url.netloc, score_path, parsed_url.params, parsed_url.query, parsed_url.fragment))
    payload = {
        "userId": user_id,
        "scoreGiven": round(score, 2),
        "scoreMaximum": 100,
        "activityProgress": "Completed",
        "gradingProgress": "FullyGraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "comment": "ProctorIDE automatic grade sync",
    }
    status, _headers, body = _request_json(
        score_url,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.ims.lis.v1.score+json",
        },
        data=payload,
    )
    if status not in (200, 201, 204):
        return False, body or f"Score push failed with status {status}"
    return True, "Score posted successfully"


def _resolve_gradable_user(lineitem_url: str, primary_user_id: str) -> str:
    """
    Resolve which Moodle user to grade.
    If primary_user_id is not gradable (e.g., teacher), find an actual student in the course.
    Returns the user ID to use for grading.
    """
    # Try to extract contextid from lineitem URL: /contextid/lineitems/itemid/
    # Format: http://localhost:8080/mod/lti/service/gradebookservices/lineitems/2/11/
    try:
        # Extract context ID from path
        parts = lineitem_url.split('/')
        context_id_idx = parts.index('lineitems') - 1 if 'lineitems' in parts else -1
        if context_id_idx >= 0 and context_id_idx < len(parts):
            context_id = parts[context_id_idx]
            # For now, return the primary user
            # In a full implementation, we would query Moodle's mdl_role_assignments to find
            # a student role user in the given context who CAN be graded
            # This is a known limitation: we use lti_user_sub (often the teacher) instead of the actual student
            pass
    except (ValueError, IndexError):
        pass
    
    return primary_user_id


def push_exam_grades_to_moodle(db: Session, exam_id: int) -> dict[str, Any]:
    exam = db.query(Exam).filter(Exam.exam_id == exam_id).first()
    if not exam:
        raise ValueError("Exam not found")

    pushed = 0
    failed = 0
    skipped = 0
    messages: list[str] = []

    sessions = db.query(ExamSession).filter(ExamSession.exam_id == exam_id, ExamSession.raw_jwt.isnot(None)).all()
    if not sessions:
        return {"exam_id": exam_id, "pushed": 0, "failed": 0, "skipped": 0, "messages": ["No LTI launch sessions available for grade push."]}

    for session in sessions:
        payload = _decode_launch(session)
        ags_endpoint = _ags_endpoint(payload)
        issuer = session.lti_issuer or payload.get("iss")
        client_id = session.lti_client_id or _client_id(payload)
        deployment_id = session.lti_deployment_id or payload.get("https://purl.imsglobal.org/spec/lti/claim/deployment_id")
        scope_values = []
        if session.ags_scopes_json:
            try:
                scope_values = json.loads(session.ags_scopes_json)
            except json.JSONDecodeError:
                scope_values = []
        if not scope_values:
            raw_scopes = ags_endpoint.get("scope", [])
            scope_values = raw_scopes if isinstance(raw_scopes, list) else [raw_scopes] if raw_scopes else []

        lineitem_url = session.ags_lineitem_url or ags_endpoint.get("lineitem")
        lineitems_url = session.ags_lineitems_url or ags_endpoint.get("lineitems")

        if not issuer or not client_id or (not lineitem_url and not lineitems_url):
            session.ags_push_status = "not_available"
            session.ags_last_push_message = "Missing AGS launch data."
            session.ags_last_pushed_at = datetime.now(timezone.utc)
            skipped += 1
            messages.append(f"Session {session.id}: missing AGS launch data")
            continue

        token_endpoint = session.ags_token_endpoint
        if not token_endpoint:
            openid_config_url = issuer.rstrip("/") + "/.well-known/openid-configuration"
            try:
                openid_config = _load_json(openid_config_url)
                token_endpoint = openid_config.get("token_endpoint")
                if not token_endpoint:
                    raise ValueError("Missing token endpoint in openid configuration")
            except Exception as exc:
                session.ags_push_status = "failed"
                session.ags_last_push_message = f"Unable to load Moodle OIDC config: {exc}"
                session.ags_last_pushed_at = datetime.now(timezone.utc)
                failed += 1
                messages.append(f"Session {session.id}: OIDC config error")
                continue

        private_key_path = Path(__file__).resolve().parents[2] / "private.key"
        private_key = private_key_path.read_bytes()
        access_token, token_error = _get_access_token(token_endpoint, client_id, private_key, scope_values)
        if not access_token:
            session.ags_push_status = "failed"
            session.ags_last_push_message = f"Unable to obtain AGS access token: {token_error}"
            session.ags_last_pushed_at = datetime.now(timezone.utc)
            failed += 1
            messages.append(f"Session {session.id}: token request failed")
            continue

        if not lineitem_url and lineitems_url:
            lineitem_url, lineitem_error = _create_lineitem(lineitems_url, access_token, exam)
            if not lineitem_url:
                session.ags_push_status = "failed"
                session.ags_last_push_message = lineitem_error or "Unable to create Moodle line item"
                session.ags_last_pushed_at = datetime.now(timezone.utc)
                failed += 1
                messages.append(f"Session {session.id}: line item creation failed")
                continue
            session.ags_lineitem_url = lineitem_url

        if not lineitem_url:
            session.ags_push_status = "not_available"
            session.ags_last_push_message = "No Moodle line item URL available."
            session.ags_last_pushed_at = datetime.now(timezone.utc)
            skipped += 1
            messages.append(f"Session {session.id}: no line item URL")
            continue

        session_submissions = db.query(Submission).filter(
            Submission.exam_id == exam_id,
            Submission.session_id == session.id,
        ).all()
        if not session_submissions:
            session.ags_push_status = "skipped"
            session.ags_last_push_message = "No submissions found for this launch session."
            session.ags_last_pushed_at = datetime.now(timezone.utc)
            skipped += 1
            messages.append(f"Session {session.id}: no submissions")
            continue

        score = _score_from_session_submissions(session_submissions)
        # Use override user ID if specified (e.g., when teacher launches but we want to grade a student)
        # Otherwise use lti_user_sub (JWT sub from the launch)
        graded_user_id = session.ags_grading_user_override or session.lti_user_sub or payload.get("sub") or session.user_id
        success, push_message = _push_score(lineitem_url, access_token, str(graded_user_id), score)
        session.ags_last_pushed_at = datetime.now(timezone.utc)
        session.ags_last_push_message = push_message
        if success:
            session.ags_push_status = "pushed"
            session.ags_lineitem_url = lineitem_url
            session.lti_issuer = issuer
            session.lti_client_id = client_id
            session.lti_deployment_id = deployment_id
            pushed += 1
            messages.append(f"Session {session.id}: pushed {score}%")
        else:
            session.ags_push_status = "failed"
            failed += 1
            messages.append(f"Session {session.id}: push failed")

    db.commit()
    return {
        "exam_id": exam_id,
        "pushed": pushed,
        "failed": failed,
        "skipped": skipped,
        "messages": messages,
    }
