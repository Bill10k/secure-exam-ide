from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import CodeExecutionRequest, CodeExecutionResponse, SubmissionResponse
from ..services.sandbox import execute_code_docker, grade_submission_docker
from ..models import Submission, ExamSession, Question
from ..services.gradebook import refresh_exam_gradebook
from ..grading.service import run_static_analysis

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
async def submit_code(
    request: CodeExecutionRequest,
    db: Session = Depends(get_db),
):
    """
    Grade submitted code using hidden test cases and static analysis,
    combine both scores, and save the final result.
    """

    question = (
        db.query(Question)
        .filter(Question.question_id == request.question_id)
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

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

    static_result = run_static_analysis(
        code=request.code,
        language=required_language,
        rules=question.static_rules,
    )

    functional_result = await grade_submission_docker(
        request.code,
        request.question_id,
        db,
    )

    functional_score = float(
        functional_result.get("score", 0.0)
    )

    has_static_rules = bool(question.static_rules)

    if has_static_rules:
        static_score = float(
            static_result.get("score", 0.0)
        )
        effective_functional_weight = float(
            question.functional_weight
        )
        effective_static_weight = float(
            question.static_weight
        )
    else:
        static_score = 0.0
        effective_functional_weight = 100.0
        effective_static_weight = 0.0

    final_score = (
        functional_score
        * effective_functional_weight
        / 100.0
    ) + (
        static_score
        * effective_static_weight
        / 100.0
    )

    final_score = round(final_score, 2)

    user_id = 1

    if request.session_id:
        exam_session = (
            db.query(ExamSession)
            .filter(ExamSession.id == request.session_id)
            .first()
        )

        if exam_session and exam_session.account_id:
            user_id = exam_session.account_id

    functional_passed = (
        functional_result.get("status") == "passed"
    )

    # For now, functional correctness determines pass/fail.
    # Static rules affect the score and feedback.
    overall_passed = functional_passed

    status_code = 1 if overall_passed else 0
    status_text = "passed" if overall_passed else "failed"

    feedback_parts = [
        functional_result.get(
            "feedback",
            "Functional grading completed.",
        )
    ]

    if not has_static_rules:
        feedback_parts.append(
            "No static-analysis rules were configured."
        )
    elif not static_result.get("syntax_valid", True):
        feedback_parts.append(
            static_result.get(
                "error",
                "Static analysis failed.",
            )
        )
    else:
        feedback_parts.append(
            (
                "Static analysis: "
                f"{static_result['earned']}/"
                f"{static_result['maximum']} rule points."
            )
        )

    combined_feedback = "\n".join(feedback_parts)

    new_submission = Submission(
        session_id=request.session_id,
        user_id=user_id,
        question_id=request.question_id,
        exam_id=question.exam_id,
        submitted_code=request.code,
        score=final_score,
        status=status_code,
    )

    try:
        db.add(new_submission)
        db.commit()
        db.refresh(new_submission)

        refresh_exam_gradebook(
            db,
            question.exam_id,
            user_id=user_id,
        )

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to save submission result.",
        ) from exc

    return SubmissionResponse(
        status=status_text,
        score=final_score,
        feedback=combined_feedback,
        functional_score=round(functional_score, 2),
        static_score=round(static_score, 2),
        functional_weight=effective_functional_weight,
        static_weight=effective_static_weight,
        static_checks=static_result.get("results", []),
    )