from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import verify_admin_role
from ..models import Question, TestCase, Submission, UserAccount
from ..schemas import QuestionCreate, QuestionResponse, TestCaseCreate, TestCaseResponse

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(verify_admin_role)])

@router.post("/questions", response_model=QuestionResponse)
def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    """Admin endpoint to create a new programming question."""
    new_question = Question(
        exam_id=question.exam_id,
        title=question.title,
        description=question.description,
        diff_level=question.diff_level,
        default_code=question.default_code
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return new_question

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
