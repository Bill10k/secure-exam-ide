from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import CodeSnapshot
from ..schemas import CodeSnapshotSaveRequest, CodeSnapshotSaveResponse, CodeSnapshotResponse

router = APIRouter(prefix="/snapshots", tags=["Snapshots"])


@router.put("/save", response_model=CodeSnapshotSaveResponse)
def save_snapshot(request: CodeSnapshotSaveRequest, db: Session = Depends(get_db)):
    """Persist the latest code snapshot for a session/question pair."""
    statement = (
        select(CodeSnapshot)
        .where(
            CodeSnapshot.session_id == request.session_id,
            CodeSnapshot.question_id == request.question_id,
        )
        .order_by(CodeSnapshot.version.desc(), CodeSnapshot.snapshot_id.desc())
    )
    snapshot = db.execute(statement).scalars().first()

    if snapshot is None:
        snapshot = CodeSnapshot(
            session_id=request.session_id,
            question_id=request.question_id,
            code=request.code,
            version=request.version,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return CodeSnapshotSaveResponse(saved=True, version=snapshot.version, saved_at=snapshot.saved_at)

    if request.version < snapshot.version:
        return CodeSnapshotSaveResponse(saved=True, version=snapshot.version, saved_at=snapshot.saved_at)

    snapshot.code = request.code
    snapshot.version = snapshot.version + 1 if request.version == snapshot.version else request.version
    db.commit()
    db.refresh(snapshot)

    return CodeSnapshotSaveResponse(saved=True, version=snapshot.version, saved_at=snapshot.saved_at)


@router.get("/{session_id}", response_model=List[CodeSnapshotResponse])
def get_session_snapshots(session_id: int, db: Session = Depends(get_db)):
    """Return all snapshots stored for a given exam session."""
    statement = (
        select(CodeSnapshot)
        .where(CodeSnapshot.session_id == session_id)
        .order_by(CodeSnapshot.question_id.asc(), CodeSnapshot.version.asc(), CodeSnapshot.snapshot_id.asc())
    )
    snapshots = db.execute(statement).scalars().all()

    return [
        CodeSnapshotResponse(
            question_id=snapshot.question_id,
            code=snapshot.code,
            version=snapshot.version,
            saved_at=snapshot.saved_at,
        )
        for snapshot in snapshots
    ]