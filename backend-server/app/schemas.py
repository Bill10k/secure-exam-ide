from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# LTI
class LaunchRequest(BaseModel):
    jwt: str

class ExamSessionResponse(BaseModel):
    id: int
    context_id: str
    resource_link_id: str
    user_id: str
    exam_id: Optional[int]
    account_id: Optional[int]
    status: str

    class Config:
        from_attributes = True

class LaunchResponse(BaseModel):
    message: str
    session: ExamSessionResponse

# User
class UserAccountBase(BaseModel):
    role_type: int
    first_name: str
    last_name: str
    email: str

class UserAccountResponse(UserAccountBase):
    account_id: int
    status: int
    
    class Config:
        from_attributes = True

# Question
class QuestionBase(BaseModel):
    title: str
    description: str
    diff_level: int
    default_code: Optional[str] = None

class QuestionCreate(QuestionBase):
    exam_id: int

class QuestionResponse(QuestionBase):
    question_id: int
    exam_id: int
    
    class Config:
        from_attributes = True

# TestCase
class TestCaseBase(BaseModel):
    input_data: str
    expected_output: str
    is_hidden: bool = True
    weight: Optional[float] = 1.0

class TestCaseCreate(TestCaseBase):
    question_id: int

class TestCaseResponse(TestCaseBase):
    test_case_id: int
    question_id: int
    
    class Config:
        from_attributes = True

# Exam
class ExamBase(BaseModel):
    title: str
    description: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: int

class ExamResponse(ExamBase):
    exam_id: int
    questions: List[QuestionResponse] = []
    
    class Config:
        from_attributes = True

# Submission
class CodeExecutionRequest(BaseModel):
    code: str
    language: str
    question_id: int
    session_id: Optional[int] = None
    custom_input: Optional[str] = ""

class CodeExecutionResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float

class SubmissionResponse(BaseModel):
    status: str
    score: float
    feedback: str
