import hashlib
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..grading.service import run_static_analysis
from ..models import Exam, ExamSession, Question, Submission
from ..schemas import CodeExecutionRequest, CodeExecutionResponse, SubmissionResponse
from ..services.exam_timing import get_session_timing
from ..services.gradebook import refresh_exam_gradebook
from ..services.moodle_ags import push_submission_grade_to_moodle
from ..services.sandbox import execute_code_docker, grade_submission_docker

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.post("/run", response_model=CodeExecutionResponse)
async def run_code(request: CodeExecutionRequest):
    """
    Executes code interactively using Docker and returns the raw stdout/stderr output.
    Used for the terminal.
    """
    result = await execute_code_docker(
        request.code,
        request.language,
        getattr(request, "custom_input", ""),
    )
    return CodeExecutionResponse(**result)


@router.post("/submit", response_model=SubmissionResponse)
async def submit_code(
    request: CodeExecutionRequest,
    db: Session = Depends(get_db),
):
    """
    Grade submitted code using hidden test cases and static analysis,
    combine both scores, enforce session timing, save the result,
    and automatically push the grade to Moodle via LTI AGS.
    """
    start_time = time.perf_counter()

    question = (
        db.query(Question)
        .filter(Question.question_id == request.question_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    submitted_language = request.language.strip().lower()
    required_language = question.language.strip().lower()
    if submitted_language != required_language:
        raise HTTPException(
            status_code=400,
            detail=(
                f"This question requires '{required_language}', "
                f"not '{submitted_language}'."
            ),
        )

    user_id = 1
    if request.session_id:
        exam_session = (
            db.query(ExamSession)
            .filter(ExamSession.id == request.session_id)
            .first()
        )
        if not exam_session:
            raise HTTPException(status_code=404, detail="Exam session not found")

        if exam_session.exam_id != question.exam_id:
            raise HTTPException(
                status_code=403,
                detail="Question does not belong to this exam session",
            )

        exam = db.query(Exam).filter(Exam.exam_id == exam_session.exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        timing = get_session_timing(exam_session, exam)
        if timing["is_expired"]:
            exam_session.status = "expired"
            db.add(exam_session)
            db.commit()
            raise HTTPException(
                status_code=403,
                detail="Exam time limit has expired. Late submissions are not accepted.",
            )

        if exam_session.account_id:
            user_id = exam_session.account_id

    static_result = run_static_analysis(
        code=request.code,
        language=required_language,
        rules=question.static_rules,
    )

    functional_result = await grade_submission_docker(
        request.code,
        request.question_id,
        db,
        language=required_language,
    )

    functional_score = float(functional_result.get("score", 0.0))
    has_static_rules = bool(question.static_rules)

    if has_static_rules:
        static_score = float(static_result.get("score", 0.0))
        effective_functional_weight = float(question.functional_weight)
        effective_static_weight = float(question.static_weight)
    else:
        static_score = 0.0
        effective_functional_weight = 100.0
        effective_static_weight = 0.0

    final_score = round(
        (
            functional_score
            * effective_functional_weight
            / 100.0
        )
        + (
            static_score
            * effective_static_weight
            / 100.0
        ),
        2,
    )

    functional_status = functional_result.get("status")
    functional_passed = functional_status == "passed"
    status_code = 1 if functional_passed else 0

    if functional_passed:
        status_label = "Passed"
    elif "syntax" in str(functional_result.get("feedback", "")).lower() or "compile" in str(functional_result.get("feedback", "")).lower():
        status_label = "Compile Error"
    elif "timeout" in str(functional_result.get("feedback", "")).lower() or "error" in str(functional_result.get("feedback", "")).lower():
        status_label = "Runtime Error"
    else:
        status_label = "Failed"

    feedback_parts = [
        functional_result.get("feedback", "Functional grading completed.")
    ]
    if not has_static_rules:
        feedback_parts.append("No static-analysis rules were configured.")
    elif not static_result.get("syntax_valid", True):
        feedback_parts.append(static_result.get("error", "Static analysis failed."))
    else:
        feedback_parts.append(
            (
                "Static analysis: "
                f"{static_result['earned']}/"
                f"{static_result['maximum']} rule points."
            )
        )

    submission_hash = hashlib.sha256(request.code.encode("utf-8")).hexdigest()
    grading_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    new_submission = Submission(
        session_id=request.session_id,
        user_id=user_id,
        question_id=request.question_id,
        exam_id=question.exam_id,
        submitted_code=request.code,
        functional_score=round(functional_score, 2),
        static_score=round(static_score, 2),
        final_score=final_score,
        score=final_score,
        status=status_code,
        status_label=status_label,
        functional_results=functional_result.get("test_cases", []),
        static_analysis=static_result.get("results", []),
        grading_duration_ms=grading_duration_ms,
        grading_version="v1",
        submission_hash=submission_hash,
    )

    try:
        db.add(new_submission)
        db.commit()
        db.refresh(new_submission)
        refresh_exam_gradebook(db, question.exam_id, user_id=user_id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to save submission result.",
        ) from exc

    # Resilient decoupled Moodle AGS grade push
    try:
        push_submission_grade_to_moodle(db, new_submission.submission_id)
    except Exception as exc:
        new_submission.sync_status = "failed"
        new_submission.sync_message = f"AGS push error: {str(exc)}"
        db.commit()

    return SubmissionResponse(
        status=status_label.lower(),
        score=final_score,
        feedback="\n".join(feedback_parts),
        functional_score=round(functional_score, 2),
        static_score=round(static_score, 2),
        functional_weight=effective_functional_weight,
        static_weight=effective_static_weight,
        static_checks=static_result.get("results", []),
    )

