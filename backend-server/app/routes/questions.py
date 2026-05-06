from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Question
from ..schemas import QuestionResponse

router = APIRouter(prefix="/questions", tags=["Questions"])

@router.get("/exam/{exam_id}", response_model=List[QuestionResponse])
def get_exam_questions(exam_id: int, db: Session = Depends(get_db)):
    """Fetch all questions assigned to a specific exam."""
    questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    return questions

@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(question_id: int, db: Session = Depends(get_db)):
    """Fetch details of a single question."""
    question = db.query(Question).filter(Question.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question
