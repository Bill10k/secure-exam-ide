from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ExamAssignment, Exam, ExamSession
from .. import schemas

router = APIRouter(prefix="/exams", tags=["Exams"])

@router.get("/session/{session_id}/hydrate", response_model=schemas.ExamResponse)
def hydrate_exam_session(session_id: int, db: Session = Depends(get_db)):
    """Fetch the exam session and related exam details for the Tauri app."""
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.exam_id:
        raise HTTPException(status_code=404, detail="No exam linked to this session")
        
    exam = db.query(Exam).filter(Exam.exam_id == session.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    return exam

@router.get("/assignment/{assignment_id}")
def get_exam_assignment(assignment_id: int, db: Session = Depends(get_db)):
    """Fetch the exam assignment and related exam details for a student."""
    assignment = db.query(ExamAssignment).filter(ExamAssignment.assignment_id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    exam = db.query(Exam).filter(Exam.exam_id == assignment.exam_id).first()
    return {
        "assignment": assignment,
        "exam": exam
    }
