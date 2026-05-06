from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ExamAssignment, Exam

router = APIRouter(prefix="/exams", tags=["Exams"])

@router.get("/session/{assignment_id}")
def get_exam_session(assignment_id: int, db: Session = Depends(get_db)):
    """Fetch the exam session and related exam details for a student."""
    assignment = db.query(ExamAssignment).filter(ExamAssignment.assignment_id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    exam = db.query(Exam).filter(Exam.exam_id == assignment.exam_id).first()
    return {
        "assignment": assignment,
        "exam": exam
    }
