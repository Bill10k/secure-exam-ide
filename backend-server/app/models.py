from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base

class UserAccount(Base):
    __tablename__ = "user_accounts"

    account_id = Column(Integer, primary_key=True, index=True)
    role_type = Column(Integer, default=1) # 1: Student, 2: Admin/Instructor
    status = Column(Integer, default=1) # 1: Active
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    date_created = Column(DateTime(timezone=True), server_default=func.now())
    date_updated = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sessions = relationship("ExamSession", back_populates="user_account")
    activity_logs = relationship("ActivityLog", back_populates="user_account")
    submissions = relationship("Submission", back_populates="user_account")
    assignments = relationship("ExamAssignment", back_populates="user_account")

class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, index=True)
    # LTI Context
    context_id = Column(String, index=True)
    resource_link_id = Column(String, index=True)
    user_id = Column(String, index=True) # LTI user ID
    exam_id = Column(Integer, ForeignKey('exams.exam_id'), nullable=True) # Selected through deep linking
    
    # Internal User Link
    account_id = Column(Integer, ForeignKey('user_accounts.account_id'), nullable=True)
    user_account = relationship("UserAccount", back_populates="sessions")
    
    raw_jwt = Column(Text, nullable=True)
    lti_user_sub = Column(String, nullable=True)
    lti_issuer = Column(String, nullable=True)
    lti_client_id = Column(String, nullable=True)
    lti_deployment_id = Column(String, nullable=True)
    ags_token_endpoint = Column(Text, nullable=True)
    ags_lineitem_url = Column(Text, nullable=True)
    ags_lineitems_url = Column(Text, nullable=True)
    ags_scopes_json = Column(Text, nullable=True)
    ags_grading_user_override = Column(String, nullable=True) # Optional override: which Moodle user ID to grade
    ags_push_status = Column(String, default="not_synced")
    ags_last_push_message = Column(Text, nullable=True)
    ags_last_pushed_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True) # in seconds
    status = Column(String, default="initialized") # initialized, started, submitted
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    submissions = relationship("Submission", back_populates="session")
    code_snapshots = relationship("CodeSnapshot", back_populates="session")

class Exam(Base):
    __tablename__ = "exams"
    
    exam_id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    language = Column(String, default="python")
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    duration = Column(Integer) # in minutes
    status = Column(Integer, default=1) # 1: Active, 0: Inactive
    date_created = Column(DateTime(timezone=True), server_default=func.now())
    
    
    questions = relationship("Question", back_populates="exam")
    assignments = relationship("ExamAssignment", back_populates="exam")
    submissions = relationship("Submission", back_populates="exam")

class ExamAssignment(Base):
    __tablename__ = "exam_assignments"
    
    assignment_id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey('exams.exam_id'))
    account_id = Column(Integer, ForeignKey('user_accounts.account_id'))
    date_assigned = Column(DateTime(timezone=True), server_default=func.now())
    date_completed = Column(DateTime(timezone=True), nullable=True)
    score = Column(Float, nullable=True)
    status = Column(Integer, default=0) # 0: assigned, 1: completed
    
    exam = relationship("Exam", back_populates="assignments")
    user_account = relationship("UserAccount", back_populates="assignments")

class Question(Base):
    __tablename__ = "questions"

    question_id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(
        Integer,
        ForeignKey("exams.exam_id"),
        nullable=False,
    )

    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    diff_level = Column(Integer)

    language = Column(
        String,
        default="python",
        nullable=False,
    )

    default_code = Column(Text, nullable=True)

    functional_weight = Column(
        Float,
        default=80.0,
        nullable=False,
    )

    static_weight = Column(
        Float,
        default=20.0,
        nullable=False,
    )

    date_created = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    status = Column(Integer, default=1)

    exam = relationship(
        "Exam",
        back_populates="questions",
    )

    test_cases = relationship(
        "TestCase",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    submissions = relationship(
        "Submission",
        back_populates="question",
    )

    code_snapshots = relationship(
        "CodeSnapshot",
        back_populates="question",
    )

    static_rules = relationship(
        "QuestionStaticRule",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class QuestionStaticRule(Base):
    __tablename__ = "question_static_rules"

    rule_id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    question_id = Column(
        Integer,
        ForeignKey(
            "questions.question_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    rule_type = Column(
        String,
        nullable=False,
    )

    expected_value = Column(
        Text,
        nullable=True,
    )

    weight = Column(
        Float,
        default=1.0,
        nullable=False,
    )

    required = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    question = relationship(
        "Question",
        back_populates="static_rules",
    )
class CodeSnapshot(Base):
    __tablename__ = "code_snapshots"

    snapshot_id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('exam_sessions.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.question_id'), nullable=False)
    code = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    saved_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("session_id", "question_id", "version", name="uq_code_snapshots_session_question_version"),
        Index("idx_code_snapshots_session_id", "session_id"),
    )

    session = relationship("ExamSession", back_populates="code_snapshots")
    question = relationship("Question", back_populates="code_snapshots")

class TestCase(Base):
    __tablename__ = "test_cases"
    
    test_case_id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey('questions.question_id'))
    input_data = Column(Text)
    expected_output = Column(Text)
    is_hidden = Column(Boolean, default=True)
    weight = Column(Float, default=1.0)
    
    question = relationship("Question", back_populates="test_cases")

class Submission(Base):
    __tablename__ = "submissions"
    
    submission_id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('exam_sessions.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('user_accounts.account_id'))
    question_id = Column(Integer, ForeignKey('questions.question_id'))
    exam_id = Column(Integer, ForeignKey('exams.exam_id'))
    submitted_code = Column(Text)
    score = Column(Float)
    status = Column(Integer) # e.g., 0: pending, 1: graded
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("ExamSession", back_populates="submissions")
    user_account = relationship("UserAccount", back_populates="submissions")
    question = relationship("Question", back_populates="submissions")
    exam = relationship("Exam", back_populates="submissions")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    log_id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('user_accounts.account_id'))
    event_type = Column(Integer) # e.g., 1: login, 2: tab switch, 3: submit
    ip_address = Column(String)
    datetime_stamp = Column(DateTime(timezone=True), server_default=func.now())
    
    user_account = relationship("UserAccount", back_populates="activity_logs")
