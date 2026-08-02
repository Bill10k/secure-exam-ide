from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import verify_admin_role
from ..models import Exam,Question, QuestionStaticRule,TestCase, Submission, UserAccount
from ..schemas import QuestionCreate, QuestionResponse, TestCaseCreate, TestCaseResponse
from ..grading.rule_registry import (
    get_rule_definition,
    is_rule_supported_for_language,
)
router = APIRouter(prefix="/admin", tags=["Admin"], )

@router.post("/questions", response_model=QuestionResponse)
def create_question(
    question: QuestionCreate,
    db: Session = Depends(get_db),
):
    exam = (
        db.query(Exam)
        .filter(Exam.exam_id == question.exam_id)
        .first()
    )

    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found.",
        )

    for rule in question.static_rules:
        definition = get_rule_definition(rule.rule_type)

        if definition is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown static rule: {rule.rule_type}",
            )

        if not is_rule_supported_for_language(
            rule.rule_type,
            question.language,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Rule '{rule.rule_type}' is not supported "
                    f"for language '{question.language}'."
                ),
            )

    new_question = Question(
        exam_id=question.exam_id,
        title=question.title,
        description=question.description,
        diff_level=question.diff_level,
        default_code=question.default_code,
        language=question.language,
        functional_weight=question.functional_weight,
        static_weight=question.static_weight,
    )

    try:
        db.add(new_question)
        db.flush()

        for rule in question.static_rules:
            db.add(
                QuestionStaticRule(
                    question_id=new_question.question_id,
                    rule_type=rule.rule_type,
                    expected_value=rule.expected_value,
                    weight=rule.weight,
                    required=rule.required,
                )
            )

        db.commit()
        db.refresh(new_question)
        return new_question

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create question.",
        ) from exc
@router.post("/testcases", response_model=TestCaseResponse)
def create_testcase(testcase: TestCaseCreate, db: Session = Depends(get_db)):
    """Admin endpoint to add test cases to a question."""
    # Optional: check if question exists
    question = db.query(Question).filter(Question.question_id == testcase.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    new_testcase = TestCase(
        question_id=testcase.question_id,
        input_data=testcase.input_data,
        expected_output=testcase.expected_output,
        is_hidden=testcase.is_hidden,
        weight=testcase.weight if hasattr(TestCase, 'weight') else 1.0 # fallback if DB isn't migrated
    )
    db.add(new_testcase)
    db.commit()
    db.refresh(new_testcase)
    return new_testcase

@router.get("/results/exam/{exam_id}")
def get_exam_results(exam_id: int, db: Session = Depends(get_db)):
    """Admin endpoint to view all student submissions and grades for an exam."""
    # Query all submissions for the exam, joining with the user account
    submissions = db.query(Submission, UserAccount).join(
        UserAccount, Submission.user_id == UserAccount.account_id
    ).filter(Submission.exam_id == exam_id).all()
    
    results = []
    for sub, user in submissions:
        results.append({
            "submission_id": sub.submission_id,
            "user_id": user.account_id,
            "student_name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "question_id": sub.question_id,
            "score": sub.score,
            "status": sub.status,
            "submitted_at": sub.submitted_at
        })
        
    return {"exam_id": exam_id, "results": results}
