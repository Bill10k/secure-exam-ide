from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import Exam, ExamAssignment, Submission


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def refresh_exam_gradebook(db: Session, exam_id: int, user_id: int | None = None) -> list[ExamAssignment]:
    """
    Recalculate exam-level grades from the latest submission per question for each student.
    Returns the assignments that were updated.
    """
    exam = db.query(Exam).filter(Exam.exam_id == exam_id).first()
    if not exam:
        return []

    query = db.query(Submission).filter(Submission.exam_id == exam_id)
    if user_id is not None:
        query = query.filter(Submission.user_id == user_id)

    submissions = query.order_by(Submission.submitted_at.asc(), Submission.submission_id.asc()).all()
    if not submissions:
        return []

    latest_scores_by_user: dict[int, dict[int, float]] = defaultdict(dict)
    latest_completed_by_user: dict[int, datetime] = {}

    for submission in submissions:
        user_scores = latest_scores_by_user[submission.user_id]
        user_scores[submission.question_id] = submission.score or 0.0
        if submission.submitted_at:
            latest_completed_by_user[submission.user_id] = submission.submitted_at

    question_count = len(exam.questions)
    updated_assignments: list[ExamAssignment] = []

    for student_id, scores_by_question in latest_scores_by_user.items():
        exam_score = _average(list(scores_by_question.values()))
        completed = len(scores_by_question) >= question_count if question_count else False
        status = 1 if completed else 0

        assignment = db.query(ExamAssignment).filter(
            ExamAssignment.exam_id == exam_id,
            ExamAssignment.account_id == student_id,
        ).first()

        if assignment:
            assignment.score = exam_score
            assignment.status = status
            assignment.date_completed = latest_completed_by_user.get(student_id, datetime.now(timezone.utc))
        else:
            assignment = ExamAssignment(
                exam_id=exam_id,
                account_id=student_id,
                score=exam_score,
                status=status,
                date_completed=latest_completed_by_user.get(student_id, datetime.now(timezone.utc)),
            )
            db.add(assignment)

        updated_assignments.append(assignment)

    db.commit()
    for assignment in updated_assignments:
        db.refresh(assignment)
    return updated_assignments
