import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import models

TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_data():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # User Account
    user = models.UserAccount(
        account_id=1,
        first_name="Test",
        last_name="Student",
        email="student@example.com",
    )
    db.add(user)

    # Exam
    exam = models.Exam(
        exam_id=100,
        title="Multi Question Exam",
        description="Exam with multiple questions",
        language="python",
        duration=60,
        status=1,
    )
    db.add(exam)
    db.flush()

    # Exam Session
    session = models.ExamSession(
        id=55,
        account_id=1,
        exam_id=100,
        status="started",
    )
    db.add(session)

    # Question 1: Factorial
    q1 = models.Question(
        question_id=101,
        exam_id=100,
        title="Factorial",
        description="Compute factorial of n",
        diff_level=1,
        language="python",
        functional_weight=100.0,
        static_weight=0.0,
    )

    # Question 2: Fibonacci
    q2 = models.Question(
        question_id=102,
        exam_id=100,
        title="Fibonacci",
        description="Compute nth fibonacci number",
        diff_level=2,
        language="python",
        functional_weight=100.0,
        static_weight=0.0,
    )

    # Question 3: Prime Checker
    q3 = models.Question(
        question_id=103,
        exam_id=100,
        title="Prime Checker",
        description="Check if number is prime",
        diff_level=2,
        language="python",
        functional_weight=100.0,
        static_weight=0.0,
    )

    db.add_all([q1, q2, q3])
    db.commit()
    db.close()


@patch("app.routes.submissions.push_submission_grade_to_moodle")
@patch("app.routes.submissions.grade_submission_docker", new_callable=AsyncMock)
def test_submit_all_questions_for_session(mock_grade_docker, mock_push_moodle):
    """
    Verify that submitting solutions for Q1, Q2, and Q3 sequentially for the same exam session
    correctly creates and saves 3 separate submission records in the database.
    """
    mock_grade_docker.return_value = {
        "status": "passed",
        "score": 100.0,
        "feedback": "All test cases passed.",
        "test_cases": [],
    }

    session_id = 55

    # Submit Question 1
    resp_q1 = client.post(
        "/submissions/submit",
        json={
            "code": "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)",
            "language": "python",
            "question_id": 101,
            "session_id": session_id,
        },
    )
    assert resp_q1.status_code == 200, resp_q1.text
    data_q1 = resp_q1.json()
    assert data_q1["status"] == "passed"
    assert data_q1["score"] == 100.0

    # Submit Question 2
    resp_q2 = client.post(
        "/submissions/submit",
        json={
            "code": "def fibonacci(n):\n    return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
            "language": "python",
            "question_id": 102,
            "session_id": session_id,
        },
    )
    assert resp_q2.status_code == 200, resp_q2.text
    data_q2 = resp_q2.json()
    assert data_q2["status"] == "passed"

    # Submit Question 3
    resp_q3 = client.post(
        "/submissions/submit",
        json={
            "code": "def is_prime(n):\n    return n > 1 and all(n % i != 0 for i in range(2, int(n**0.5) + 1))",
            "language": "python",
            "question_id": 103,
            "session_id": session_id,
        },
    )
    assert resp_q3.status_code == 200, resp_q3.text
    data_q3 = resp_q3.json()
    assert data_q3["status"] == "passed"

    # Query DB directly to verify 3 submissions exist for session_id 55
    db = TestingSessionLocal()
    submissions = (
        db.query(models.Submission)
        .filter(models.Submission.session_id == session_id)
        .order_by(models.Submission.question_id.asc())
        .all()
    )
    assert len(submissions) == 3

    submitted_question_ids = [s.question_id for s in submissions]
    assert submitted_question_ids == [101, 102, 103]

    assert "factorial" in submissions[0].submitted_code
    assert "fibonacci" in submissions[1].submitted_code
    assert "is_prime" in submissions[2].submitted_code
    db.close()
