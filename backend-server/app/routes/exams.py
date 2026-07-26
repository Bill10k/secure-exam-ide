from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..database import get_db
from ..models import ExamAssignment, Exam, ExamSession, CodeSnapshot
from .. import schemas

router = APIRouter(prefix="/exams", tags=["Exams"])

@router.get("/session/{session_id}/hydrate", response_model=schemas.ExamHydrateResponse)
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

    now = datetime.now(timezone.utc)

    def _ensure_aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    started_at = _ensure_aware(session.started_at) or _ensure_aware(session.created_at) or now
    duration_seconds = session.duration if session.duration and session.duration > 0 else (exam.duration or 0) * 60
    elapsed_seconds = max(int((now - started_at).total_seconds()), 0)
    remaining_seconds = max(int(duration_seconds) - elapsed_seconds, 0)

    snapshots = (
        db.query(CodeSnapshot)
        .filter(CodeSnapshot.session_id == session_id)
        .order_by(CodeSnapshot.question_id.asc(), CodeSnapshot.version.desc(), CodeSnapshot.snapshot_id.desc())
        .all()
    )

    latest_snapshots = {}
    for snapshot in snapshots:
        if snapshot.question_id not in latest_snapshots:
            latest_snapshots[snapshot.question_id] = snapshot

    hydrated_questions = []
    for question in exam.questions:
        latest_snapshot = latest_snapshots.get(question.question_id)
        hydrated_questions.append(
            {
                "question_id": question.question_id,
                "exam_id": question.exam_id,
                "title": question.title,
                "description": question.description,
                "diff_level": question.diff_level,
                "default_code": question.default_code,
                "snapshot": (
                    {
                        "code": latest_snapshot.code,
                        "version": latest_snapshot.version,
                        "saved_at": latest_snapshot.saved_at,
                    }
                    if latest_snapshot
                    else None
                ),
            }
        )
    
    print(f"Hydrated exam session {session_id} with {len(hydrated_questions)} questions and {len(latest_snapshots)} snapshots.")

    return {
        "exam_id": exam.exam_id,
        "title": exam.title,
        "description": exam.description,
        "start_time": exam.start_time,
        "end_time": exam.end_time,
        "duration": exam.duration,
        "remaining_seconds": remaining_seconds,
        "questions": hydrated_questions,
    }

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
