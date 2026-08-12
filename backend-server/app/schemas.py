from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, Field, model_validator
SUPPORTED_LANGUAGES = {
    "python",
    "javascript",
    "c",
    "cpp",
}
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

# Static grading rules
class StaticRuleBase(BaseModel):
    rule_type: str
    expected_value: Optional[str] = None
    weight: float = 1.0
    required: bool = True


class StaticRuleCreate(StaticRuleBase):
    rule_id: Optional[int] = None


class StaticRuleResponse(StaticRuleBase):
    rule_id: int
    question_id: Optional[int] = None

    class Config:
        from_attributes = True


# Question
class QuestionBase(BaseModel):
    title: str
    description: str
    diff_level: Optional[int] = 1
    default_code: Optional[str] = None

    language: str = "python"
    functional_weight: float = 80.0
    static_weight: float = 20.0

    @model_validator(mode="after")
    def validate_question_configuration(self):
        language = self.language.strip().lower()

        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{self.language}'. "
                f"Supported languages are: "
                f"{', '.join(sorted(SUPPORTED_LANGUAGES))}."
            )

        self.language = language

        total = self.functional_weight + self.static_weight

        if abs(total - 100.0) > 0.001:
            raise ValueError(
                "Functional weight and static weight must add up to 100."
            )

        if self.functional_weight < 0 or self.static_weight < 0:
            raise ValueError("Grading weights cannot be negative.")

        return self


class QuestionCreate(QuestionBase):
    exam_id: int
    static_rules: List[StaticRuleCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_static_rules(self):
        if self.static_weight == 0 and self.static_rules:
            raise ValueError(
                "Static rules cannot be provided when static weight is 0."
            )

        total_rule_weight = sum(rule.weight for rule in self.static_rules)

        if any(rule.weight < 0 for rule in self.static_rules):
            raise ValueError("Static-rule weights cannot be negative.")

        if self.static_weight > 0 and self.static_rules and total_rule_weight <= 0:
            raise ValueError(
                "Static rules must have a total weight greater than 0."
            )

        return self


class QuestionUpdate(QuestionBase):
    static_rules: List[StaticRuleCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_static_rules(self):
        if self.static_weight == 0 and self.static_rules:
            raise ValueError(
                "Static rules cannot be provided when static weight is 0."
            )

        total_rule_weight = sum(rule.weight for rule in self.static_rules)

        if any(rule.weight < 0 for rule in self.static_rules):
            raise ValueError("Static-rule weights cannot be negative.")

        if self.static_weight > 0 and self.static_rules and total_rule_weight <= 0:
            raise ValueError(
                "Static rules must have a total weight greater than 0."
            )

        return self


class QuestionResponse(QuestionBase):
    question_id: int
    exam_id: int
    static_rules: List[StaticRuleResponse] = Field(default_factory=list)

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


class TestCaseUpdate(TestCaseBase):
    pass


class TestCaseResponse(TestCaseBase):
    test_case_id: int
    question_id: int

    class Config:
        from_attributes = True


class QuestionDetailResponse(QuestionResponse):
    test_cases: List[TestCaseResponse] = Field(default_factory=list)


class QuestionHydrateResponse(QuestionResponse):
    snapshot: Optional["CodeSnapshotHydrateResponse"] = None
    sample_test_cases: List[TestCaseResponse] = Field(default_factory=list)


# Exam
class ExamBase(BaseModel):
    title: str
    description: str
    language: str = "python"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: int


class ExamSummaryResponse(BaseModel):
    exam_id: int
    title: str
    description: Optional[str] = ""
    duration: int
    language: str = "python"
    question_count: int = 0
    submission_count: int = 0
    published: bool = True

    class Config:
        from_attributes = True


class ExamUpdate(BaseModel):
    title: str
    description: Optional[str] = ""
    duration: int
    published: Optional[bool] = None

    @model_validator(mode="after")
    def validate_exam(self):
        if not self.title or not self.title.strip():
            raise ValueError("Exam title cannot be empty.")
        if self.duration <= 0:
            raise ValueError("Exam duration must be positive.")
        return self


class ExamResponse(ExamBase):
    exam_id: int
    published: bool = True
    questions: List[QuestionResponse] = Field(default_factory=list)

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

    functional_score: float
    static_score: float
    functional_weight: float
    static_weight: float

    static_checks: List[dict[str, Any]] = Field(
        default_factory=list
    )
# Code Snapshot
class CodeSnapshotSaveRequest(BaseModel):
    session_id: int
    question_id: int
    code: str
    version: int


class CodeSnapshotSaveResponse(BaseModel):
    saved: bool
    version: int
    saved_at: datetime


class CodeSnapshotResponse(BaseModel):
    question_id: int
    code: str
    version: int
    saved_at: datetime


class CodeSnapshotHydrateResponse(BaseModel):
    code: str
    version: int
    saved_at: datetime


class ExamHydrateResponse(ExamResponse):
    server_time: datetime
    session_started_at: datetime
    session_duration_seconds: int
    session_ends_at: datetime
    remaining_seconds: int
    questions: List[QuestionHydrateResponse] = Field(default_factory=list)

class StaticAnalysisTestRequest(BaseModel):
    code: str
    language: str = "python"
    question_id: int
