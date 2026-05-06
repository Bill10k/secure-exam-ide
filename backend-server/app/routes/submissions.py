from fastapi import APIRouter
from ..schemas import CodeExecutionRequest, CodeExecutionResponse, SubmissionResponse
from ..services.sandbox import execute_code_mock, grade_submission_mock

router = APIRouter(prefix="/submissions", tags=["Submissions"])

@router.post("/run", response_model=CodeExecutionResponse)
async def run_code(request: CodeExecutionRequest):
    """
    Executes code interactively and returns the raw stdout/stderr output.
    Used for the terminal.
    """
    result = await execute_code_mock(request.code, request.language)
    return CodeExecutionResponse(**result)

@router.post("/submit", response_model=SubmissionResponse)
async def submit_code(request: CodeExecutionRequest):
    """
    Executes code against hidden test cases, grades it, and saves to database.
    Used for final submission.
    """
    # TODO: Addipa to add database logic to save the submission using request.session_id
    
    result = await grade_submission_mock(request.code, request.question_id)
    return SubmissionResponse(**result)
