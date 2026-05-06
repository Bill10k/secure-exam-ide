from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import CodeExecutionRequest, CodeExecutionResponse, SubmissionResponse
from ..services.sandbox import execute_code_docker, grade_submission_docker

router = APIRouter(prefix="/submissions", tags=["Submissions"])

@router.post("/run", response_model=CodeExecutionResponse)
async def run_code(request: CodeExecutionRequest):
    """
    Executes code interactively using Docker and returns the raw stdout/stderr output.
    Used for the terminal.
    """
    result = await execute_code_docker(request.code, request.language)
    return CodeExecutionResponse(**result)

@router.post("/submit", response_model=SubmissionResponse)
async def submit_code(request: CodeExecutionRequest, db: Session = Depends(get_db)):
    """
    Executes code against hidden test cases using Docker, grades it, and saves to database.
    Used for final submission.
    """
    # Grade the submission using the database test cases
    result = await grade_submission_docker(request.code, request.question_id, db)
    
    # TODO: Addipa to add database logic to save the submission record here using request.session_id and result
    
    return SubmissionResponse(**result)
