from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Question
from ..schemas import StaticAnalysisTestRequest
from .service import run_static_analysis
from .rule_registry import (
    SUPPORTED_LANGUAGES,
    get_rules_for_language,
)


router = APIRouter(
    prefix="/grading",
    tags=["Grading"],
)


@router.get("/languages")
def get_supported_languages():
    return {
        "languages": [
            {
                "value": "python",
                "label": "Python",
            },
            {
                "value": "javascript",
                "label": "JavaScript",
            },
            {
                "value": "c",
                "label": "C",
            },
            {
                "value": "cpp",
                "label": "C++",
            },
        ]
    }


@router.get("/rules/{language}")
def get_language_rules(language: str):
    normalized_language = language.strip().lower()

    if normalized_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unsupported language: {language}",
        )

    return {
        "language": normalized_language,
        "rules": get_rules_for_language(normalized_language),
    }

@router.post("/analyse")
def analyse_submission_structure(
    request: StaticAnalysisTestRequest,
    db: Session = Depends(get_db),
):
    question = (
        db.query(Question)
        .filter(
            Question.question_id == request.question_id
        )
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    if request.language.strip().lower() != question.language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Submitted language does not match "
                "the question language."
            ),
        )

    return run_static_analysis(
        code=request.code,
        language=question.language,
        rules=question.static_rules,
    )
