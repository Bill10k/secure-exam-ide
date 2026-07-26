from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import CodeExecutionRequest, CodeExecutionResponse, SubmissionResponse
from ..services.sandbox import execute_code_docker, grade_submission_docker
from ..models import Exam, Submission, ExamSession, Question
from ..services.gradebook import refresh_exam_gradebook
from ..services.exam_timing import get_session_timing

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
    question = db.query(Question).filter(Question.question_id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    user_id = 1 # Fallback dummy user ID (Admin/Student ID 1) for testing if no session
    db_session = None
    if request.session_id:
        db_session = db.query(ExamSession).filter(ExamSession.id == request.session_id).first()
        if not db_session:
            raise HTTPException(status_code=404, detail="Exam session not found")

        if db_session.exam_id != question.exam_id:
            raise HTTPException(status_code=403, detail="Question does not belong to this exam session")

        exam = db.query(Exam).filter(Exam.exam_id == db_session.exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        timing = get_session_timing(db_session, exam)
        if timing["is_expired"]:
            db_session.status = "expired"
            db.add(db_session)
            db.commit()
            raise HTTPException(
                status_code=403,
                detail="Exam time limit has expired. Late submissions are not accepted.",
            )

        if db_session.account_id:
            user_id = db_session.account_id

    # Grade the submission using the database test cases only after deadline checks pass.
    result = await grade_submission_docker(request.code, request.question_id, db)

    # 3. Determine status integer for database (1 = Pass, 0 = Fail)
    status_code = 1 if result["status"] == "passed" else 0

    # 4. Create and save the submission
    new_submission = Submission(
        session_id=request.session_id,
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

    # Keep the exam-level gradebook in sync from the latest submission per question.
    refresh_exam_gradebook(db, question.exam_id, user_id=user_id)
    
    # Output result to be piped to the Terminal
    return SubmissionResponse(**result)
