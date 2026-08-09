from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import csv
import io
import math
import statistics
import json
import jwt
import base64
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from ..database import get_db
from .. import models, schemas
from ..dependencies import SECRET_KEY, ALGORITHM
from ..services.gradebook import refresh_exam_gradebook
from ..services.moodle_ags import push_exam_grades_to_moodle, push_submission_grade_to_moodle

router = APIRouter(
    prefix="/api/launch",
    tags=["lti"],
)

BASE_DIR = Path(__file__).resolve().parents[2]
PRIVATE_KEY_PATH = BASE_DIR / "private.key"
PUBLIC_KEY_PATH = BASE_DIR / "public.key"


def _ensure_keypair() -> None:
    if PRIVATE_KEY_PATH.exists() and PUBLIC_KEY_PATH.exists():
        return

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    PRIVATE_KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    PUBLIC_KEY_PATH.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def _read_private_key() -> bytes:
    _ensure_keypair()
    return PRIVATE_KEY_PATH.read_bytes()


def _read_public_key() -> bytes:
    _ensure_keypair()
    return PUBLIC_KEY_PATH.read_bytes()


def _decode_launch_token(id_token: str) -> dict:
    try:
        return jwt.decode(id_token, options={"verify_signature": False})
    except jwt.DecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JWT payload") from exc


def _is_instructor_launch(payload: dict) -> bool:
    roles = payload.get("https://purl.imsglobal.org/spec/lti/claim/roles", [])
    if isinstance(roles, str):
        roles = [roles]
    instructor_tokens = ("Instructor", "TeachingAssistant", "ContentDeveloper", "Administrator")
    return any(any(token in role for token in instructor_tokens) for role in roles)

@router.post("/deep-link", response_class=HTMLResponse)
def deep_link_selection(id_token: str = Form(...), db: Session = Depends(get_db)):
    """
    Called by the LMS to initiate the deep linking (resource selection) process.
    We receive the id_token, validate it, and display a list of exams to the instructor.
    """
    try:
        # 1. Decode the LTI Deep Linking request (disabling verification for prototype handshake)
        payload = jwt.decode(id_token, options={"verify_signature": False})
        
        # Verify it's a deep linking request
        message_type = payload.get("https://purl.imsglobal.org/spec/lti/claim/message_type")
        if message_type != "LtiDeepLinkingRequest":
            raise HTTPException(status_code=400, detail="Invalid message type. Expected LtiDeepLinkingRequest.")

        # 2. Get available exams from the database
        exams = db.query(models.Exam).all()
        
        # 3. Render a simple HTML form for the instructor to select an exam
        # In a real app, this might be a React frontend route, but HTML is simplest for the deep linking bridge.
        
        from .lti_dashboard_template import get_instructor_dashboard_html
        html_content = get_instructor_dashboard_html(id_token, exams)
        return HTMLResponse(content=html_content)

    except jwt.DecodeError:
        raise HTTPException(status_code=400, detail="Invalid JWT payload")


@router.post("/deep-link/submit", response_class=HTMLResponse)
def deep_link_submit(id_token: str = Form(...), exam_id: int = Form(...), db: Session = Depends(get_db)):
    """
    Handles the form submission from the instructor.
    Builds the LtiDeepLinkingResponse and auto-submits it back to the LMS.
    """
    try:
        # 1. Decode the original request to get return URLs and issuer details
        request_payload = jwt.decode(id_token, options={"verify_signature": False})
        
        dl_settings = request_payload.get("https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings", {})
        return_url = dl_settings.get("deep_link_return_url")
        if not return_url:
            raise HTTPException(status_code=400, detail="Missing deep_link_return_url in original request")

        # 2. Fetch the exam details
        exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        # 3. Construct the response payload
        client_id = request_payload.get("aud")
        if isinstance(client_id, list):
            client_id = client_id[0]
            
        now = int(time.time())
        response_payload = {
            "iss": request_payload.get("aud"), # The Tool is now the issuer
            "aud": request_payload.get("iss"), # The LMS is the audience
            "iat": now,
            "exp": now + 300, # 5 minutes
            "nonce": request_payload.get("nonce", "nonce-" + str(now)),
            "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiDeepLinkingResponse",
            "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
            "https://purl.imsglobal.org/spec/lti/claim/deployment_id": request_payload.get("https://purl.imsglobal.org/spec/lti/claim/deployment_id"),
            "https://purl.imsglobal.org/spec/lti-dl/claim/data": dl_settings.get("data"),
            "https://purl.imsglobal.org/spec/lti-dl/claim/content_items": [
                {
                    "type": "ltiResourceLink",
                    "title": exam.title,
                    "text": exam.description,
                    "url": f"http://localhost:8000/api/launch/validate", # The target launch URL
                    "custom": {
                        "exam_id": str(exam.exam_id)
                    }
                }
            ]
        }

        # 4. Sign the response payload using our Private RSA Key (RS256)
        private_key = _read_private_key()
            
        signed_response = jwt.encode(
            response_payload, 
            private_key, 
            algorithm="RS256", 
            headers={"kid": "proctoride-key-1"}
        )

        # 5. Render an auto-submitting form to POST back to the LMS
        html_content = f"""
        <html>
            <head><title>Returning to LMS...</title></head>
            <body onload="document.getElementById('auto_submit').submit();">
                <form id="auto_submit" action="{return_url}" method="POST">
                    <input type="hidden" name="JWT" value="{signed_response}" />
                    <noscript>
                        <p>JavaScript is disabled. Please click the button below to return to the LMS.</p>
                        <button type="submit">Return</button>
                    </noscript>
                </form>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except jwt.DecodeError:
        raise HTTPException(status_code=400, detail="Invalid JWT payload")


@router.post("/results", response_class=HTMLResponse)
def instructor_results(id_token: str = Form(...), exam_id: int = Form(...), db: Session = Depends(get_db)):
    """
    Render a Moodle-facing results page for the lecturer using the launch token for authorization.
    """
    payload = _decode_launch_token(id_token)
    if not _is_instructor_launch(payload):
        raise HTTPException(status_code=403, detail="Instructor privileges required")

    return _render_results_page(db, exam_id, id_token, refresh=False, push=False)


@router.post("/results/push", response_class=HTMLResponse)
def instructor_results_push(id_token: str = Form(...), exam_id: int = Form(...), db: Session = Depends(get_db)):
    payload = _decode_launch_token(id_token)
    if not _is_instructor_launch(payload):
        raise HTTPException(status_code=403, detail="Instructor privileges required")

    return _render_results_page(db, exam_id, id_token, refresh=True, push=True)


@router.post("/results/refresh", response_class=HTMLResponse)
def instructor_results_refresh(id_token: str = Form(...), exam_id: int = Form(...), db: Session = Depends(get_db)):
    payload = _decode_launch_token(id_token)
    if not _is_instructor_launch(payload):
        raise HTTPException(status_code=403, detail="Instructor privileges required")

    return _render_results_page(db, exam_id, id_token, refresh=True, push=False)


def _render_results_page(db: Session, exam_id: int, id_token: str, refresh: bool = False, push: bool = False) -> HTMLResponse:
    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if refresh:
        refresh_exam_gradebook(db, exam_id)

    push_result = push_exam_grades_to_moodle(db, exam_id) if push else None

    assignments = db.query(models.ExamAssignment, models.UserAccount).join(
        models.UserAccount, models.ExamAssignment.account_id == models.UserAccount.account_id
    ).filter(models.ExamAssignment.exam_id == exam_id).all()

    submissions = db.query(models.Submission).filter(models.Submission.exam_id == exam_id).all()
    sessions = db.query(models.ExamSession).filter(models.ExamSession.exam_id == exam_id).all()
    unique_students = len(assignments)
    completed_students = sum(1 for assignment, _user in assignments if assignment.status == 1)
    score_values = [assignment.score or 0.0 for assignment, _user in assignments]
    average_score = round(sum(score_values) / len(score_values), 2) if score_values else 0.0
    highest_score = round(max(score_values), 2) if score_values else 0.0
    lowest_score = round(min(score_values), 2) if score_values else 0.0
    synced_sessions = sum(1 for session in sessions if session.ags_push_status == "pushed")

    rows_html = ""
    if assignments:
        for assignment, user in assignments:
            student_name = f"{user.first_name} {user.last_name}".strip()
            sync_state = "Complete" if assignment.status == 1 else "In progress"
            sync_badge = "bg-emerald-100 text-emerald-700" if assignment.status == 1 else "bg-amber-100 text-amber-700"
            rows_html += f"""
                <tr class=\"border-t border-gray-200\">
                    <td class=\"px-4 py-3\">{student_name}</td>
                    <td class=\"px-4 py-3\">{user.email}</td>
                    <td class=\"px-4 py-3\">{assignment.score if assignment.score is not None else 0}</td>
                    <td class=\"px-4 py-3\"><span class=\"inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold {sync_badge}\">{sync_state}</span></td>
                    <td class=\"px-4 py-3\">{assignment.date_completed if assignment.date_completed else 'Pending'}</td>
                </tr>
            """
    else:
        rows_html = """
            <tr>
                <td colspan=\"5\" class=\"px-4 py-6 text-center text-gray-500\">No gradebook rows have been recorded for this exam yet.</td>
            </tr>
        """

    refresh_message = "Gradebook refreshed from latest submissions." if refresh else "Gradebook is showing the current saved lecturer view."
    if push_result:
        refresh_message = f"Moodle sync attempted: {push_result['pushed']} pushed, {push_result['failed']} failed, {push_result['skipped']} skipped."

    session_rows_html = ""
    if sessions:
        for session in sessions:
            session_rows_html += f"""
                <tr class=\"border-t border-gray-200\">
                    <td class=\"px-4 py-3\">{session.id}</td>
                    <td class=\"px-4 py-3\">{session.user_id}</td>
                    <td class=\"px-4 py-3\">{session.ags_push_status or 'not_synced'}</td>
                    <td class=\"px-4 py-3\">{session.ags_last_push_message or '—'}</td>
                    <td class=\"px-4 py-3\">{session.ags_last_pushed_at or '—'}</td>
                </tr>
            """
    else:
        session_rows_html = """
            <tr>
                <td colspan=\"5\" class=\"px-4 py-6 text-center text-gray-500\">No launch sessions available.</td>
            </tr>
        """

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>ProctorIDE Results - {exam.title}</title>
        <script src=\"https://cdn.tailwindcss.com\"></script>
    </head>
    <body class=\"bg-gray-50 min-h-screen\">
        <div class=\"max-w-6xl mx-auto px-6 py-8\">
            <div class=\"bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden\">
                <div class=\"px-6 py-5 border-b border-gray-200 bg-slate-900 text-white\">
                    <h1 class=\"text-2xl font-bold\">Lecturer Results</h1>
                    <p class=\"text-slate-300 mt-1\">{exam.title}</p>
                </div>
                <div class=\"p-6 space-y-6\">
                    <div class=\"grid grid-cols-1 md:grid-cols-3 gap-4\">
                        <div class=\"rounded-xl border border-gray-200 p-4 bg-slate-50\">
                            <div class=\"text-sm text-gray-500\">Exam ID</div>
                            <div class=\"text-xl font-semibold\">{exam.exam_id}</div>
                        </div>
                        <div class=\"rounded-xl border border-gray-200 p-4 bg-slate-50\">
                            <div class=\"text-sm text-gray-500\">Gradebook Rows</div>
                            <div class=\"text-xl font-semibold\">{unique_students}</div>
                        </div>
                        <div class=\"rounded-xl border border-gray-200 p-4 bg-slate-50\">
                            <div class=\"text-sm text-gray-500\">Submissions</div>
                            <div class=\"text-xl font-semibold\">{len(submissions)}</div>
                        </div>
                    </div>

                    <div class=\"grid grid-cols-1 md:grid-cols-4 gap-4\">
                        <div class=\"rounded-xl border border-gray-200 p-4 bg-white\">
                            <div class=\"text-sm text-gray-500\">Average Score</div>
                            <div class=\"text-xl font-semibold\">{average_score}%</div>
                        </div>
                        <div class=\"rounded-xl border border-gray-200 p-4 bg-white\">
                            <div class=\"text-sm text-gray-500\">Highest</div>
                            <div class=\"text-xl font-semibold\">{highest_score}%</div>
                        </div>
                        <div class=\"rounded-xl border border-gray-200 p-4 bg-white\">
                            <div class=\"text-sm text-gray-500\">Lowest</div>
                            <div class=\"text-xl font-semibold\">{lowest_score}%</div>
                        </div>
                        <div class=\"rounded-xl border border-gray-200 p-4 bg-white\">
                            <div class=\"text-sm text-gray-500\">Completed Students</div>
                            <div class=\"text-xl font-semibold\">{completed_students}</div>
                        </div>
                    </div>

                    <div class=\"grid grid-cols-1 md:grid-cols-4 gap-4\">
                        <div class=\"rounded-xl border border-gray-200 p-4 bg-white\">
                            <div class=\"text-sm text-gray-500\">Moodle Sync</div>
                            <div class=\"text-xl font-semibold\">{synced_sessions}/{len(sessions)}</div>
                        </div>
                        <div class=\"md:col-span-3 rounded-xl border border-slate-200 bg-slate-50 p-4 flex items-center justify-between gap-4\">
                            <div>
                                <div class=\"text-sm font-semibold text-slate-900\">Gradebook status</div>
                                <div class=\"text-sm text-slate-600\">{refresh_message}</div>
                            </div>
                            <div class=\"flex flex-wrap gap-3 shrink-0\">
                                <form action=\"/api/launch/results/refresh\" method=\"POST\" class=\"shrink-0\">
                                    <input type=\"hidden\" name=\"id_token\" value=\"{id_token}\" />
                                    <input type=\"hidden\" name=\"exam_id\" value=\"{exam_id}\" />
                                    <button type=\"submit\" class=\"inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800\">Refresh Gradebook</button>
                                </form>
                                <form action=\"/api/launch/results/push\" method=\"POST\" class=\"shrink-0\">
                                    <input type=\"hidden\" name=\"id_token\" value=\"{id_token}\" />
                                    <input type=\"hidden\" name=\"exam_id\" value=\"{exam_id}\" />
                                    <button type=\"submit\" class=\"inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500\">Push to Moodle</button>
                                </form>
                            </div>
                        </div>
                    </div>

                    <div class=\"overflow-x-auto border border-gray-200 rounded-xl\">
                        <table class=\"min-w-full text-sm\">
                            <thead class=\"bg-gray-100 text-gray-700\">
                                <tr>
                                    <th class=\"text-left font-semibold px-4 py-3\">Student</th>
                                    <th class=\"text-left font-semibold px-4 py-3\">Email</th>
                                    <th class=\"text-left font-semibold px-4 py-3\">Score</th>
                                    <th class=\"text-left font-semibold px-4 py-3\">Sync Status</th>
                                    <th class=\"text-left font-semibold px-4 py-3\">Last Updated</th>
                                </tr>
                            </thead>
                            <tbody class=\"bg-white\">
                                {rows_html}
                            </tbody>
                        </table>
                    </div>

                    <div class=\"overflow-x-auto border border-gray-200 rounded-xl\">
                        <table class=\"min-w-full text-sm\">
                            <thead class=\"bg-gray-100 text-gray-700\">
                                <tr>
                                    <th class=\"text-left font-semibold px-4 py-3\">Session</th>
                                    <th class=\"text-left font-semibold px-4 py-3\">LTI User</th>
                                    <th class=\"text-left font-semibold px-4 py-3\">AGS Status</th>
                                    <th class=\"text-left font-semibold px-4 py-3\">Message</th>
                                    <th class=\"text-left font-semibold px-4 py-3\">Last Push</th>
                                </tr>
                            </thead>
                            <tbody class=\"bg-white\">
                                {session_rows_html}
                            </tbody>
                        </table>
                    </div>

                    <div class=\"flex justify-end gap-3\">
                        <a class=\"inline-flex items-center rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50\" href=\"javascript:history.back()\">Back</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@router.post("/validate")
def validate_launch(id_token: str = Form(...), state: str = Form(None), db: Session = Depends(get_db)):
    try:
        # Decode the JWT (Disabling signature verification for prototype proxy)
        payload = jwt.decode(id_token, options={"verify_signature": False})
        
        # Extract LTI 1.3 standard claims (these keys depend on the exact Moodle/LTI payload)
        # Using typical LTI 1.3 claims as an example:
        context_id = payload.get("https://purl.imsglobal.org/spec/lti/claim/context", {}).get("id", "unknown_context")
        resource_link_id = payload.get("https://purl.imsglobal.org/spec/lti/claim/resource_link", {}).get("id", "unknown_resource")
        user_id = payload.get("sub", "unknown_user")
        issuer = payload.get("iss")
        client_id = payload.get("aud")
        if isinstance(client_id, list):
            client_id = client_id[0] if client_id else None
        deployment_id = payload.get("https://purl.imsglobal.org/spec/lti/claim/deployment_id")
        ags_endpoint = payload.get("https://purl.imsglobal.org/spec/lti-ags/claim/endpoint", {})
        ags_lineitem_url = ags_endpoint.get("lineitem")
        ags_lineitems_url = ags_endpoint.get("lineitems")
        ags_scopes = ags_endpoint.get("scope", [])
        if isinstance(ags_scopes, str):
            ags_scopes = [ags_scopes]
        
        # Extract custom parameters configured during Deep Linking
        custom_params = payload.get("https://purl.imsglobal.org/spec/lti/claim/custom", {})
        exam_id_str = custom_params.get("exam_id")
        exam_id = int(exam_id_str) if exam_id_str and str(exam_id_str).isdigit() else None

        exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first() if exam_id else None
        if not exam:
            exam = db.query(models.Exam).filter(models.Exam.status == 1).first()
        if not exam:
            exam = db.query(models.Exam).first()
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        exam_id = exam.exam_id

        now = datetime.now(timezone.utc)
        
        existing_session = (
            db.query(models.ExamSession)
            .filter(
                models.ExamSession.context_id == context_id,
                models.ExamSession.resource_link_id == resource_link_id,
                models.ExamSession.user_id == user_id,
                models.ExamSession.exam_id == exam_id,
                models.ExamSession.status != "submitted",
            )
            .order_by(models.ExamSession.updated_at.desc().nullslast(), models.ExamSession.id.desc())
            .first()
        )

        if existing_session:
            if existing_session.started_at is None:
                existing_session.started_at = now
            if existing_session.duration is None:
                existing_session.duration = (exam.duration or 0) * 60
            existing_session.updated_at = now
            db.commit()
            db.refresh(existing_session)
            db_session = existing_session
        else:
            # Create a new exam session record
            db_session = models.ExamSession(
                context_id=context_id,
                resource_link_id=resource_link_id,
                user_id=user_id,
                exam_id=exam_id,
                raw_jwt=id_token,
                lti_user_sub=user_id,
                lti_issuer=issuer,
                lti_client_id=client_id,
                lti_deployment_id=deployment_id,
                ags_lineitem_url=ags_lineitem_url,
                ags_lineitems_url=ags_lineitems_url,
                ags_scopes_json=json.dumps(ags_scopes),
                started_at=now,
                duration=(exam.duration or 0) * 60,
                status="initialized"
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)

        cache_seed_material = "|".join(
            [
                str(db_session.id),
                str(exam_id),
                str(context_id),
                str(resource_link_id),
                str(user_id),
                str(issuer or ""),
                str(client_id or ""),
                str(deployment_id or ""),
                id_token,
            ]
        )
        cache_seed = base64.urlsafe_b64encode(hashlib.sha256(cache_seed_material.encode("utf-8")).digest()).decode("ascii").rstrip("=")
        
        # Render a simple HTML response for the IDE inside the iFrame
        proctoride_url = f"proctoride://launch?session_id={db_session.id}&exam_id={exam_id}&cache_seed={cache_seed}"
        
        html_content = f"""
        <html>
            <head>
                <title>Launching ProctorIDE...</title>
                <style>
                    body {{ font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; background-color: #f4f4f5; }}
                    .card {{ background: white; padding: 3rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }}
                    h2 {{ color: #1e3a8a; }}
                    a.btn {{ display: inline-block; margin-top: 1.5rem; padding: 1rem 2rem; background-color: #2563eb; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 1.1rem; transition: background-color 0.2s; }}
                    a.btn:hover {{ background-color: #1d4ed8; }}
                </style>
                # <script>
            
                #     // Attempt to launch the deep link automatically
                #     window.onload = function() {{
                #         window.location.href = "{proctoride_url}";
                #     }};
                # </script>
            </head>
            <body>
                <div class="card">
                    <h2>Exam Authorization Successful!</h2>
                    <p>Session ID: <b>{db_session.id}</b></p>
                    <p>Click the button to launch the examination.</p>
                    <a href="{proctoride_url}" class="btn">Launch ProctorIDE</a>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except jwt.DecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JWT payload")
    except Exception as e:
        # Catch-all for database errors or missing payload data during this prototype phase
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal Server Error: {str(e)}")


@router.post("/session/{session_id}/ags-config")
def set_session_ags_config(session_id: int, payload: dict, db: Session = Depends(get_db)):
    """
    Set AGS-related configuration for a specific ExamSession and optionally trigger a push.
    Payload example:
    {
      "lti_issuer": "https://lms.example.edu",
      "lti_client_id": "client-id",
      "ags_lineitem_url": "https://lms.example.edu/asm/lineitems/123",
      "ags_lineitems_url": "https://lms.example.edu/asm/lineitems",
      "ags_scopes": ["https://purl.imsglobal.org/spec/lti-ags/scope/score"],
      "ags_grading_user_override": "3",  # Optional: override which Moodle user ID to grade (e.g., if teacher is launching)
      "push": true
    }
    """
    session = db.query(models.ExamSession).filter(models.ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="ExamSession not found")

    # Update provided fields
    if payload.get("lti_issuer"):
        session.lti_issuer = payload.get("lti_issuer")
    if payload.get("lti_client_id"):
        session.lti_client_id = payload.get("lti_client_id")
    if payload.get("lti_deployment_id"):
        session.lti_deployment_id = payload.get("lti_deployment_id")
    if payload.get("token_endpoint"):
        session.ags_token_endpoint = payload.get("token_endpoint")
    if payload.get("ags_lineitem_url"):
        session.ags_lineitem_url = payload.get("ags_lineitem_url")
    if payload.get("ags_lineitems_url"):
        session.ags_lineitems_url = payload.get("ags_lineitems_url")
    if payload.get("ags_scopes") is not None:
        try:
            session.ags_scopes_json = json.dumps(payload.get("ags_scopes"))
        except Exception:
            session.ags_scopes_json = json.dumps([])
    if payload.get("ags_grading_user_override"):
        session.ags_grading_user_override = payload.get("ags_grading_user_override")

    db.add(session)
    db.commit()
    db.refresh(session)

    result = None
    if payload.get("push"):
        # Trigger push for the exam this session belongs to
        try:
            result = push_exam_grades_to_moodle(db, session.exam_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Push failed: {exc}")

    response_body = {
        "session_id": session.id,
        "exam_id": session.exam_id,
        "ags_configured": True,
        "token_endpoint": session.ags_token_endpoint,
        "grading_user_override": session.ags_grading_user_override,
        "push_result": result,
    }
    return JSONResponse(response_body)

# ================= Moodle LTI 1.3 Advantage Integration =================

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

OIDC_SESSIONS = {}


@router.api_route("/login", methods=["GET", "POST"])
async def oidc_login(request: Request):
    """
    Step 1: Moodle hits this endpoint to initiate the login.
    We redirect back to Moodle's authorization endpoint with a state and nonce.
    """
    if request.method == "POST":
        form = await request.form()
        iss = form.get("iss")
        login_hint = form.get("login_hint")
        target_link_uri = form.get("target_link_uri")
        lti_message_hint = form.get("lti_message_hint")
        client_id = form.get("client_id")
    else:
        iss = request.query_params.get("iss")
        login_hint = request.query_params.get("login_hint")
        target_link_uri = request.query_params.get("target_link_uri")
        lti_message_hint = request.query_params.get("lti_message_hint")
        client_id = request.query_params.get("client_id")
    import uuid
    state = str(uuid.uuid4())
    nonce = str(uuid.uuid4())
 
    
    # Normally store state in session
    OIDC_SESSIONS[state] = nonce
    
    # Replace this with the actual Moodle authorization URL provided
    moodle_auth_url = "http://localhost/mod/lti/auth.php" 
    
    import urllib.parse
    params = {
        "response_type": "id_token",
        "client_id": client_id,
        "redirect_uri": target_link_uri,
        "login_hint": login_hint,
        "state": state,
        "nonce": nonce,
        "response_mode": "form_post",
        "scope": "openid",
        "prompt": "none"
    }
    if lti_message_hint:
        params["lti_message_hint"] = lti_message_hint
        
    redirect_url = f"{moodle_auth_url}?{urllib.parse.urlencode(params)}"
    print(f"REDIRECT URL: {redirect_url} \n {params}")
        
    # MUST be 302 or 303 so the browser makes a GET to Moodle's auth.php, not a POST
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

@router.get("/jwks")
def jwks():
    """
    Provides the public key in JWK format so Moodle can verify our Deep Linking responses.
    """
    from cryptography.hazmat.primitives import serialization
    from jwt.algorithms import RSAAlgorithm
    import json
    
    public_key = serialization.load_pem_public_key(_read_public_key())
        
    jwk_str = RSAAlgorithm.to_jwk(public_key)
    if isinstance(jwk_str, str):
        jwk = json.loads(jwk_str)
    else:
        jwk = jwk_str
        
    jwk['kid'] = "proctoride-key-1"
    jwk['use'] = "sig"
    jwk['alg'] = "RS256"
    
    return JSONResponse({"keys": [jwk]})



from ..schemas import (
    ExamResponse,
    ExamSummaryResponse,
    ExamUpdate,
    QuestionCreate,
    QuestionDetailResponse,
    QuestionResponse,
    QuestionUpdate,
    TestCaseCreate,
    TestCaseResponse,
    TestCaseUpdate,
)
from ..grading.rule_registry import is_rule_supported_for_language

lti_mgmt_router = APIRouter(
    prefix="/lti",
    tags=["lti-management"],
)


@router.post("/api/exam", response_model=ExamResponse)
def create_exam_from_lti(exam_data: dict, db: Session = Depends(get_db)):
    new_exam = models.Exam(
        title=exam_data.get("title"),
        description=exam_data.get("description"),
        language=exam_data.get("language", "python"),
        duration=exam_data.get("duration", 60),
        status=1,
    )
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)
    return new_exam


@router.post("/api/question", response_model=QuestionResponse)
def create_question_from_lti(question_data: QuestionCreate, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == question_data.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    for static_rule in question_data.static_rules:
        if not is_rule_supported_for_language(static_rule.rule_type, question_data.language):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Rule '{static_rule.rule_type}' is not supported "
                    f"for language '{question_data.language}'."
                ),
            )

    new_question = models.Question(
        exam_id=question_data.exam_id,
        title=question_data.title,
        description=question_data.description,
        diff_level=question_data.diff_level,
        language=question_data.language,
        functional_weight=question_data.functional_weight,
        static_weight=question_data.static_weight,
        default_code=question_data.default_code or "def solution():\n    pass",
    )
    db.add(new_question)
    db.flush()

    for static_rule in question_data.static_rules:
        db.add(
            models.QuestionStaticRule(
                question_id=new_question.question_id,
                rule_type=static_rule.rule_type,
                expected_value=static_rule.expected_value,
                weight=static_rule.weight,
                required=static_rule.required,
            )
        )

    db.commit()
    db.refresh(new_question)
    return new_question


@router.post("/api/testcase", response_model=TestCaseResponse)
def create_testcase_from_lti(tc_data: dict, db: Session = Depends(get_db)):
    question_id = tc_data.get("question_id")
    if not question_id:
        raise HTTPException(status_code=400, detail="Missing question_id")

    question = db.query(models.Question).filter(models.Question.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    new_tc = models.TestCase(
        question_id=question_id,
        input_data=tc_data.get("input_data"),
        expected_output=tc_data.get("expected_output"),
        is_hidden=tc_data.get("is_hidden", True),
        weight=tc_data.get("weight", 1.0)
    )
    db.add(new_tc)
    db.commit()
    db.refresh(new_tc)
    return new_tc


# ================= Management REST Endpoints (/lti) =================

@lti_mgmt_router.get("/exams", response_model=List[ExamSummaryResponse])
def get_all_exams(db: Session = Depends(get_db)):
    exams = db.query(models.Exam).all()
    summary = []
    for exam in exams:
        summary.append(
            ExamSummaryResponse(
                exam_id=exam.exam_id,
                title=exam.title,
                description=exam.description or "",
                duration=exam.duration,
                language=exam.language or "python",
                question_count=len(exam.questions),
                submission_count=len(exam.submissions),
                published=exam.published,
            )
        )
    return summary


@lti_mgmt_router.get("/exams/{exam_id}", response_model=ExamResponse)
def get_exam_by_id(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@lti_mgmt_router.put("/exams/{exam_id}", response_model=ExamResponse)
def update_exam(exam_id: int, exam_data: ExamUpdate, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    target_published = exam_data.published if exam_data.published is not None else exam.published
    if target_published:
        if not exam.questions:
            raise HTTPException(
                status_code=400,
                detail="Exam cannot be published because it has no questions."
            )
        for question in exam.questions:
            if not question.test_cases:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exam cannot be published because Question '{question.title}' has no test cases."
                )

    exam.title = exam_data.title
    exam.description = exam_data.description or ""
    exam.duration = exam_data.duration
    if exam_data.published is not None:
        exam.published = exam_data.published

    db.commit()
    db.refresh(exam)
    return exam


@lti_mgmt_router.delete("/exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Submission Safety Protection: Block deletion if student submissions exist for this exam
    submission_exists = db.query(models.Submission).filter(models.Submission.exam_id == exam_id).first()
    if submission_exists:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an examination that already contains student submissions."
        )

    try:
        # Delete associated exam sessions, snapshots, & AGS metadata records
        sessions = db.query(models.ExamSession).filter(models.ExamSession.exam_id == exam_id).all()
        for session in sessions:
            db.query(models.CodeSnapshot).filter(models.CodeSnapshot.session_id == session.id).delete(synchronize_session=False)
            db.delete(session)

        # Delete the exam (cascades to questions, static rules, test cases, and assignments)
        db.delete(exam)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete exam: {str(exc)}")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@lti_mgmt_router.get("/questions/{question_id}", response_model=QuestionDetailResponse)
def get_question_detail(question_id: int, db: Session = Depends(get_db)):
    question = db.query(models.Question).filter(models.Question.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@lti_mgmt_router.put("/questions/{question_id}", response_model=QuestionDetailResponse)
def update_question(question_id: int, question_data: QuestionUpdate, db: Session = Depends(get_db)):
    question = db.query(models.Question).filter(models.Question.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    for static_rule in question_data.static_rules:
        if not is_rule_supported_for_language(static_rule.rule_type, question_data.language):
            raise HTTPException(
                status_code=400,
                detail=f"Rule '{static_rule.rule_type}' is not supported for language '{question_data.language}'."
            )

    question.title = question_data.title
    question.description = question_data.description
    question.diff_level = question_data.diff_level
    question.language = question_data.language
    question.functional_weight = question_data.functional_weight
    question.static_weight = question_data.static_weight
    question.default_code = question_data.default_code or ""

    # Smart differential static rule sync
    existing_rules_by_id = {r.rule_id: r for r in question.static_rules}
    updated_rule_ids = set()

    for rule_data in question_data.static_rules:
        if rule_data.rule_id and rule_data.rule_id in existing_rules_by_id:
            existing_rule = existing_rules_by_id[rule_data.rule_id]
            existing_rule.rule_type = rule_data.rule_type
            existing_rule.expected_value = rule_data.expected_value
            existing_rule.weight = rule_data.weight
            existing_rule.required = rule_data.required
            updated_rule_ids.add(rule_data.rule_id)
        else:
            new_rule = models.QuestionStaticRule(
                question_id=question.question_id,
                rule_type=rule_data.rule_type,
                expected_value=rule_data.expected_value,
                weight=rule_data.weight,
                required=rule_data.required,
            )
            db.add(new_rule)

    for rule_id, existing_rule in existing_rules_by_id.items():
        if rule_id not in updated_rule_ids:
            db.delete(existing_rule)

    db.commit()
    db.refresh(question)
    return question


@lti_mgmt_router.delete("/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(models.Question).filter(models.Question.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(question)
    db.commit()
    return {"message": "Question deleted successfully"}


@lti_mgmt_router.post("/testcases", response_model=TestCaseResponse)
def create_testcase(tc_data: TestCaseCreate, db: Session = Depends(get_db)):
    question = db.query(models.Question).filter(models.Question.question_id == tc_data.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    new_tc = models.TestCase(
        question_id=tc_data.question_id,
        input_data=tc_data.input_data,
        expected_output=tc_data.expected_output,
        is_hidden=tc_data.is_hidden,
        weight=tc_data.weight or 1.0,
    )
    db.add(new_tc)
    db.commit()
    db.refresh(new_tc)
    return new_tc


@lti_mgmt_router.put("/testcases/{testcase_id}", response_model=TestCaseResponse)
def update_testcase(testcase_id: int, tc_data: TestCaseUpdate, db: Session = Depends(get_db)):
    tc = db.query(models.TestCase).filter(models.TestCase.test_case_id == testcase_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="TestCase not found")

    tc.input_data = tc_data.input_data
    tc.expected_output = tc_data.expected_output
    tc.is_hidden = tc_data.is_hidden
    tc.weight = tc_data.weight or 1.0

    db.commit()
    db.refresh(tc)
    return tc


@lti_mgmt_router.delete("/testcases/{testcase_id}")
def delete_testcase(testcase_id: int, db: Session = Depends(get_db)):
    tc = db.query(models.TestCase).filter(models.TestCase.test_case_id == testcase_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="TestCase not found")

    db.delete(tc)
    db.commit()
    return {"message": "TestCase deleted successfully"}


# ================= Lecturer Results & Assessment Analytics Endpoints =================

@lti_mgmt_router.get("/results/{exam_id}")
def get_exam_results_paginated(
    exam_id: int,
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    status_filter: str = "all",
    sort_by: str = "submitted_at_desc",
    db: Session = Depends(get_db),
):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    query = db.query(models.Submission).filter(models.Submission.exam_id == exam_id)
    submissions = query.all()

    enriched_items = []
    for sub in submissions:
        student_name = "Student"
        student_email = f"student_{sub.user_id}@example.com"
        if sub.user_account:
            fn = sub.user_account.first_name or ""
            ln = sub.user_account.last_name or ""
            name = f"{fn} {ln}".strip()
            student_name = name if name else (sub.user_account.email or f"User #{sub.user_id}")
            if sub.user_account.email:
                student_email = sub.user_account.email
        elif sub.session and sub.session.lti_user_sub:
            student_name = sub.session.lti_user_sub

        item = {
            "submission_id": sub.submission_id,
            "session_id": sub.session_id,
            "user_id": sub.user_id,
            "student_name": student_name,
            "student_email": student_email,
            "question_id": sub.question_id,
            "final_score": sub.final_score if sub.final_score is not None else (sub.score or 0.0),
            "functional_score": sub.functional_score or 0.0,
            "static_score": sub.static_score or 0.0,
            "status": sub.status,
            "status_label": sub.status_label or ("Passed" if sub.status == 1 else "Failed"),
            "sync_status": sub.sync_status or "pending",
            "sync_message": sub.sync_message,
            "synced_at": sub.synced_at.isoformat() if sub.synced_at else None,
            "grading_duration_ms": sub.grading_duration_ms or 0.0,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        }
        enriched_items.append(item)

    if search.strip():
        term = search.strip().lower()
        enriched_items = [
            x for x in enriched_items
            if term in x["student_name"].lower()
            or term in x["student_email"].lower()
            or term in str(x["submission_id"])
        ]

    if status_filter == "passed":
        enriched_items = [x for x in enriched_items if x["status"] == 1 or x["status_label"] == "Passed"]
    elif status_filter == "failed":
        enriched_items = [x for x in enriched_items if x["status"] == 0 or x["status_label"] != "Passed"]
    elif status_filter == "not_synced":
        enriched_items = [x for x in enriched_items if x["sync_status"] != "synced"]

    if sort_by == "name_asc":
        enriched_items.sort(key=lambda x: x["student_name"].lower())
    elif sort_by == "name_desc":
        enriched_items.sort(key=lambda x: x["student_name"].lower(), reverse=True)
    elif sort_by == "score_desc":
        enriched_items.sort(key=lambda x: x["final_score"], reverse=True)
    elif sort_by == "score_asc":
        enriched_items.sort(key=lambda x: x["final_score"])
    elif sort_by == "submitted_at_asc":
        enriched_items.sort(key=lambda x: x["submitted_at"] or "")
    elif sort_by == "duration_desc":
        enriched_items.sort(key=lambda x: x["grading_duration_ms"], reverse=True)
    elif sort_by == "sync_status":
        enriched_items.sort(key=lambda x: x["sync_status"])
    else:
        enriched_items.sort(key=lambda x: x["submitted_at"] or "", reverse=True)

    total_items = len(enriched_items)
    page_size = max(1, page_size)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = enriched_items[start_idx:end_idx]

    return {
        "exam_id": exam_id,
        "exam_title": exam.title,
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "submissions": paginated_items,
    }


@lti_mgmt_router.get("/results/{exam_id}/analytics")
def get_exam_analytics(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    submissions = db.query(models.Submission).filter(models.Submission.exam_id == exam_id).all()
    sessions = db.query(models.ExamSession).filter(models.ExamSession.exam_id == exam_id).all()

    total_submissions = len(submissions)
    unique_students = len({sub.user_id for sub in submissions if sub.user_id})

    scores = [sub.final_score if sub.final_score is not None else (sub.score or 0.0) for sub in submissions]
    functional_scores = [sub.functional_score or 0.0 for sub in submissions]
    static_scores = [sub.static_score or 0.0 for sub in submissions]

    avg_score = round(statistics.mean(scores), 2) if scores else 0.0
    median_score = round(statistics.median(scores), 2) if scores else 0.0
    highest_score = round(max(scores), 2) if scores else 0.0
    lowest_score = round(min(scores), 2) if scores else 0.0
    std_dev = round(statistics.stdev(scores), 2) if len(scores) > 1 else 0.0

    passed_count = sum(1 for sub in submissions if (sub.status == 1 or sub.status_label == "Passed"))
    pass_rate_pct = round((passed_count / total_submissions * 100), 1) if total_submissions > 0 else 0.0

    synced_count = sum(1 for sub in submissions if sub.sync_status == "synced")
    failed_sync_count = sum(1 for sub in submissions if sub.sync_status == "failed")

    avg_functional = round(statistics.mean(functional_scores), 2) if functional_scores else 0.0
    avg_static = round(statistics.mean(static_scores), 2) if static_scores else 0.0

    histogram = {
        "score_100": sum(1 for s in scores if s == 100),
        "score_90_99": sum(1 for s in scores if 90 <= s < 100),
        "score_80_89": sum(1 for s in scores if 80 <= s < 90),
        "score_70_79": sum(1 for s in scores if 70 <= s < 80),
        "score_below_70": sum(1 for s in scores if s < 70),
    }

    rule_stats: dict[str, dict[str, Any]] = {}
    for sub in submissions:
        rules = sub.static_analysis or []
        if isinstance(rules, list):
            for rule in rules:
                if isinstance(rule, dict):
                    rule_name = rule.get("rule_type") or rule.get("label") or "Unknown Rule"
                    if rule_name not in rule_stats:
                        rule_stats[rule_name] = {"rule_name": rule_name, "total_evaluations": 0, "failed_count": 0}
                    rule_stats[rule_name]["total_evaluations"] += 1
                    if not rule.get("passed", False):
                        rule_stats[rule_name]["failed_count"] += 1

    rule_heatmap = sorted(rule_stats.values(), key=lambda r: r["failed_count"], reverse=True)

    return {
        "exam_id": exam_id,
        "exam_title": exam.title,
        "total_submissions": total_submissions,
        "unique_students": unique_students,
        "total_sessions": len(sessions),
        "overview": {
            "average_score": avg_score,
            "median_score": median_score,
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "std_dev": std_dev,
            "pass_rate_pct": pass_rate_pct,
            "avg_functional_score": avg_functional,
            "avg_static_score": avg_static,
            "synced_count": synced_count,
            "failed_sync_count": failed_sync_count,
        },
        "histogram": histogram,
        "rule_heatmap": rule_heatmap,
    }


@lti_mgmt_router.get("/submissions/{submission_id}")
def get_submission_detail(submission_id: int, db: Session = Depends(get_db)):
    sub = db.query(models.Submission).filter(models.Submission.submission_id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    exam = db.query(models.Exam).filter(models.Exam.exam_id == sub.exam_id).first()
    question = db.query(models.Question).filter(models.Question.question_id == sub.question_id).first()

    student_name = "Student"
    student_email = f"student_{sub.user_id}@example.com"
    if sub.user_account:
        fn = sub.user_account.first_name or ""
        ln = sub.user_account.last_name or ""
        name = f"{fn} {ln}".strip()
        student_name = name if name else (sub.user_account.email or f"User #{sub.user_id}")
        if sub.user_account.email:
            student_email = sub.user_account.email

    snapshots = []
    if sub.session_id and sub.question_id:
        snap_records = db.query(models.CodeSnapshot).filter(
            models.CodeSnapshot.session_id == sub.session_id,
            models.CodeSnapshot.question_id == sub.question_id,
        ).order_by(models.CodeSnapshot.version.asc()).all()
        for snap in snap_records:
            snapshots.append({
                "snapshot_id": snap.snapshot_id,
                "version": snap.version,
                "saved_at": snap.saved_at.isoformat() if snap.saved_at else None,
                "code": snap.code,
            })

    timeline = []
    if sub.session and sub.session.started_at:
        timeline.append({"time": sub.session.started_at.isoformat(), "event": "Exam Started"})
    if snapshots:
        timeline.append({"time": snapshots[0]["saved_at"], "event": f"Code snapshots created ({len(snapshots)} saved)"})
    if sub.submitted_at:
        timeline.append({"time": sub.submitted_at.isoformat(), "event": "Final Code Submitted"})
    if sub.graded_at:
        timeline.append({"time": sub.graded_at.isoformat(), "event": f"Graded in {sub.grading_duration_ms or 0} ms"})
    if sub.synced_at:
        timeline.append({"time": sub.synced_at.isoformat(), "event": f"Moodle Sync ({sub.sync_status}): {sub.sync_message or ''}"})

    return {
        "submission_id": sub.submission_id,
        "session_id": sub.session_id,
        "student_name": student_name,
        "student_email": student_email,
        "exam_title": exam.title if exam else "Exam",
        "question_title": question.title if question else "Question",
        "language": question.language if question else "python",
        "submitted_code": sub.submitted_code or "",

        "final_score": sub.final_score if sub.final_score is not None else (sub.score or 0.0),
        "functional_score": sub.functional_score or 0.0,
        "static_score": sub.static_score or 0.0,
        "functional_weight": question.functional_weight if question else 80.0,
        "static_weight": question.static_weight if question else 20.0,

        "status_label": sub.status_label or ("Passed" if sub.status == 1 else "Failed"),
        "functional_results": sub.functional_results or [],
        "static_analysis": sub.static_analysis or [],

        "grading_duration_ms": sub.grading_duration_ms or 0.0,
        "grading_version": sub.grading_version or "v1",
        "submission_hash": sub.submission_hash,

        "sync_status": sub.sync_status or "pending",
        "sync_message": sub.sync_message,
        "synced_at": sub.synced_at.isoformat() if sub.synced_at else None,

        "snapshots": snapshots,
        "timeline": timeline,
    }


@lti_mgmt_router.post("/sync/retry/{submission_id}")
def retry_moodle_sync(submission_id: int, db: Session = Depends(get_db)):
    result = push_submission_grade_to_moodle(db, submission_id)
    return {
        "submission_id": submission_id,
        "sync_status": result.get("sync_status", "failed"),
        "message": result.get("message", "Retry attempted"),
    }


@lti_mgmt_router.get("/results/{exam_id}/export")
def export_exam_results(
    exam_id: int,
    format: str = "csv",
    db: Session = Depends(get_db),
):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    submissions = db.query(models.Submission).filter(models.Submission.exam_id == exam_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Submission ID", "Student Name", "Student Email", "Final Score (%)",
        "Functional Score", "Static Score", "Status", "Sync Status",
        "Grading Duration (ms)", "Submitted At"
    ])

    for sub in submissions:
        student_name = "Student"
        student_email = f"student_{sub.user_id}@example.com"
        if sub.user_account:
            fn = sub.user_account.first_name or ""
            ln = sub.user_account.last_name or ""
            name = f"{fn} {ln}".strip()
            student_name = name if name else (sub.user_account.email or f"User #{sub.user_id}")
            if sub.user_account.email:
                student_email = sub.user_account.email

        writer.writerow([
            sub.submission_id,
            student_name,
            student_email,
            sub.final_score if sub.final_score is not None else (sub.score or 0.0),
            sub.functional_score or 0.0,
            sub.static_score or 0.0,
            sub.status_label or ("Passed" if sub.status == 1 else "Failed"),
            sub.sync_status or "pending",
            sub.grading_duration_ms or 0.0,
            sub.submitted_at.isoformat() if sub.submitted_at else "",
        ])

    csv_data = output.getvalue()
    filename = f"exam_{exam_id}_results.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@lti_mgmt_router.post("/sync/retry/{submission_id}")
def retry_submission_moodle_sync(submission_id: int, db: Session = Depends(get_db)):
    from ..services.moodle_ags import push_submission_grade_to_moodle
    result = push_submission_grade_to_moodle(db, submission_id)
    return result


@lti_mgmt_router.post("/sync/retry-exam/{exam_id}")
def retry_exam_moodle_sync(exam_id: int, db: Session = Depends(get_db)):
    from ..services.moodle_ags import push_exam_grades_to_moodle
    result = push_exam_grades_to_moodle(db, exam_id)
    return result

