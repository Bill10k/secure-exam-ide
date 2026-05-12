from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import jwt
import time

from ..database import get_db
from .. import models, schemas
from ..dependencies import SECRET_KEY, ALGORITHM

router = APIRouter(
    prefix="/api/launch",
    tags=["lti"],
)

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
                    "url": f"http://host.docker.internal:8000/api/launch/validate", # The target launch URL
                    "custom": {
                        "exam_id": str(exam.exam_id)
                    }
                }
            ]
        }

        # 4. Sign the response payload using our Private RSA Key (RS256)
        with open("private.key", "rb") as f:
            private_key = f.read()
            
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
        
        # Extract custom parameters configured during Deep Linking
        custom_params = payload.get("https://purl.imsglobal.org/spec/lti/claim/custom", {})
        exam_id_str = custom_params.get("exam_id")
        exam_id = int(exam_id_str) if exam_id_str and exam_id_str.isdigit() else None
        
        # Create a new exam session record
        db_session = models.ExamSession(
            context_id=context_id,
            resource_link_id=resource_link_id,
            user_id=user_id,
            exam_id=exam_id,
            raw_jwt=id_token,
            status="initialized"
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        # Render a simple HTML response for the IDE inside the iFrame
        proctoride_url = f"proctoride://launch?session_id={db_session.id}&exam_id={exam_id}"
        
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
                <script>
                    // Attempt to launch the deep link automatically
                    window.onload = function() {{
                        window.location.href = "{proctoride_url}";
                    }};
                </script>
            </head>
            <body>
                <div class="card">
                    <h2>Exam Authorization Successful!</h2>
                    <p>Session ID: <b>{db_session.id}</b></p>
                    <p>If ProctorIDE does not open automatically, please click the button below:</p>
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
    moodle_auth_url = "http://localhost:8080/mod/lti/auth.php" 
    
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
    
    with open("public.key", "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
        
    jwk_str = RSAAlgorithm.to_jwk(public_key)
    if isinstance(jwk_str, str):
        jwk = json.loads(jwk_str)
    else:
        jwk = jwk_str
        
    jwk['kid'] = "proctoride-key-1"
    jwk['use'] = "sig"
    jwk['alg'] = "RS256"
    
    return JSONResponse({"keys": [jwk]})



from ..schemas import ExamResponse, QuestionResponse, TestCaseResponse

@router.post("/api/exam", response_model=ExamResponse)
def create_exam_from_lti(exam_data: dict, db: Session = Depends(get_db)):
    from datetime import datetime
    new_exam = models.Exam(
        title=exam_data.get("title"),
        description=exam_data.get("description"),
        duration=exam_data.get("duration", 60),
        status=1,
    )
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)
    return new_exam

@router.post("/api/question", response_model=QuestionResponse)
def create_question_from_lti(question_data: dict, db: Session = Depends(get_db)):
    new_question = models.Question(
        exam_id=question_data.get("exam_id"),
        title=question_data.get("title"),
        description=question_data.get("description"),
        diff_level=question_data.get("diff_level", 1),
        default_code=question_data.get("default_code", "def solution():\n    pass")
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return new_question

@router.post("/api/testcase", response_model=TestCaseResponse)
def create_testcase_from_lti(tc_data: dict, db: Session = Depends(get_db)):
    new_tc = models.TestCase(
        question_id=tc_data.get("question_id"),
        input_data=tc_data.get("input_data"),
        expected_output=tc_data.get("expected_output"),
        is_hidden=tc_data.get("is_hidden", True),
        weight=tc_data.get("weight", 1.0)
    )
    db.add(new_tc)
    db.commit()
    db.refresh(new_tc)
    return new_tc
