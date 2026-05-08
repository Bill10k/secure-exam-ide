from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import CodeExecutionRequest, CodeExecutionResponse, SubmissionResponse
from ..services.sandbox import execute_code_docker, grade_submission_docker
from ..models import Submission, ExamSession, Question

router = APIRouter(prefix="/submissions", tags=["Submissions"])

@router.post("/run", response_model=CodeExecutionResponse)
async def run_code(request: CodeExecutionRequest):
    """
    Executes code interactively using Docker and returns the raw stdout/stderr output.
    Used for the terminal.
    """
    result = await execute_code_docker(request.code, request.language, getattr(request, 'custom_input', ''))
    return CodeExecutionResponse(**result)

@router.post("/submit", response_model=SubmissionResponse)
async def submit_code(request: CodeExecutionRequest, db: Session = Depends(get_db)):
    """
    Executes code against hidden test cases using Docker, grades it, and saves to database.
    Used for final submission.
    """
    # Grade the submission using the database test cases
    result = await grade_submission_docker(request.code, request.question_id, db)
    
    # Save the submission record to the database
    # 1. Fetch Question to get exam_id to relate this submission properly
    question = db.query(Question).filter(Question.question_id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # 2. Fetch Session to get user_id (if session_id provided)
    user_id = 1 # Fallback dummy user ID (Admin/Student ID 1) for testing if no session
    if request.session_id:
        db_session = db.query(ExamSession).filter(ExamSession.id == request.session_id).first()
        if db_session and db_session.account_id:
            user_id = db_session.account_id

    # 3. Determine status integer for database (1 = Pass, 0 = Fail)
    status_code = 1 if result["status"] == "passed" else 0

    # 4. Create and save the submission
    new_submission = Submission(
        user_id=user_id,
        question_id=request.question_id,
        exam_id=question.exam_id,
        submitted_code=request.code,
        score=result["score"],
        status=status_code
    )
    
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)
    
    # Output result to be piped to the Terminal
    return SubmissionResponse(**result)
