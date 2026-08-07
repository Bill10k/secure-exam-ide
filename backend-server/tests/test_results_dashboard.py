import pytest
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
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Create User Account
    user = models.UserAccount(
        account_id=1,
        first_name="Bill",
        last_name="Gbadago",
        email="bill@example.com",
    )
    db.add(user)

    # Create Exam
    exam = models.Exam(
        exam_id=10,
        title="UnitTest Assessment",
        description="Final assessment",
        language="python",
        duration=60,
        status=1,
    )
    db.add(exam)
    db.flush()

    # Create Question
    question = models.Question(
        question_id=101,
        exam_id=10,
        title="Recursive Factorial",
        description="Write a recursive function named factorial(n).",
        language="python",
        functional_weight=80.0,
        static_weight=20.0,
    )
    db.add(question)
    db.flush()

    # Create Exam Session
    session = models.ExamSession(
        id=50,
        exam_id=10,
        account_id=1,
        user_id="lti_user_1",
        status="started",
    )
    db.add(session)
    db.flush()

    # Create Code Snapshot
    snapshot = models.CodeSnapshot(
        session_id=50,
        question_id=101,
        code="def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)",
        version=1,
    )
    db.add(snapshot)

    # Create Submissions
    sub1 = models.Submission(
        submission_id=1001,
        session_id=50,
        user_id=1,
        question_id=101,
        exam_id=10,
        submitted_code="def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)",
        functional_score=80.0,
        static_score=20.0,
        final_score=100.0,
        score=100.0,
        status=1,
        status_label="Passed",
        functional_results=[
            {"input": "5", "expected": "120", "output": "120", "status": "passed", "weight": 1.0, "passed": True}
        ],
        static_analysis=[
            {"rule_type": "require_recursion", "expected_value": "True", "passed": True, "weight": 1.0, "earned": 1.0}
        ],
        grading_duration_ms=450.0,
        grading_version="v1",
        sync_status="synced",
        sync_message="Score posted successfully",
        submission_hash="hash1001",
    )
    db.add(sub1)

    sub2 = models.Submission(
        submission_id=1002,
        session_id=50,
        user_id=1,
        question_id=101,
        exam_id=10,
        submitted_code="def factorial(n):\n    return 1",
        functional_score=20.0,
        static_score=0.0,
        final_score=16.0,
        score=16.0,
        status=0,
        status_label="Failed",
        functional_results=[
            {"input": "5", "expected": "120", "output": "1", "status": "failed", "weight": 1.0, "passed": False}
        ],
        static_analysis=[
            {"rule_type": "require_recursion", "expected_value": "True", "passed": False, "weight": 1.0, "earned": 0.0}
        ],
        grading_duration_ms=320.0,
        grading_version="v1",
        sync_status="failed",
        sync_message="Token request failed",
        submission_hash="hash1002",
    )
    db.add(sub2)

    db.commit()
    db.close()


def test_get_exam_results_paginated():
    response = client.get("/lti/results/10?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["exam_id"] == 10
    assert data["total_items"] == 2
    assert len(data["submissions"]) == 2


def test_get_exam_results_search_filter():
    response = client.get("/lti/results/10?search=Bill&status_filter=passed")
    assert response.status_code == 200
    data = response.json()
    assert data["total_items"] == 1
    assert data["submissions"][0]["submission_id"] == 1001
    assert data["submissions"][0]["final_score"] == 100.0


def test_get_exam_analytics():
    response = client.get("/lti/results/10/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["exam_id"] == 10
    assert data["total_submissions"] == 2
    assert data["overview"]["highest_score"] == 100.0
    assert data["overview"]["lowest_score"] == 16.0
    assert data["overview"]["pass_rate_pct"] == 50.0
    assert data["histogram"]["score_100"] == 1
    assert len(data["rule_heatmap"]) > 0


def test_get_submission_detail():
    response = client.get("/lti/submissions/1001")
    assert response.status_code == 200
    data = response.json()
    assert data["submission_id"] == 1001
    assert data["student_name"] == "Bill Gbadago"
    assert data["final_score"] == 100.0
    assert data["status_label"] == "Passed"
    assert len(data["functional_results"]) == 1
    assert len(data["static_analysis"]) == 1
    assert len(data["snapshots"]) == 1
    assert len(data["timeline"]) >= 2


def test_retry_moodle_sync():
    response = client.post("/lti/sync/retry/1002")
    assert response.status_code == 200
    data = response.json()
    assert data["submission_id"] == 1002
    assert "sync_status" in data


def test_export_exam_results():
    response = client.get("/lti/results/10/export?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    content = response.text
    assert "Submission ID" in content
    assert "Bill Gbadago" in content
