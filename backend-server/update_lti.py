import os
import re

with open('app/routes/lti.py', 'r') as f:
    text = f.read()

new_routes = """
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
        default_code=question_data.get("default_code", "def solution():\\n    pass")
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
"""

if "/api/exam" not in text:
    with open('app/routes/lti.py', 'w') as f:
        f.write(text + "\n" + new_routes)
