import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from .database import engine, Base
from .routes import lti, submissions, questions, exams, admin

# Create database tables
Base.metadata.create_all(bind=engine)


def _add_sqlite_column(table_name: str, column_name: str, column_ddl: str) -> None:
    inspector = inspect(engine)
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        return

    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}"))


_add_sqlite_column("exam_sessions", "lti_issuer", "lti_issuer VARCHAR")
_add_sqlite_column("exam_sessions", "lti_user_sub", "lti_user_sub VARCHAR")
_add_sqlite_column("exam_sessions", "lti_client_id", "lti_client_id VARCHAR")
_add_sqlite_column("exam_sessions", "lti_deployment_id", "lti_deployment_id VARCHAR")
_add_sqlite_column("exam_sessions", "ags_token_endpoint", "ags_token_endpoint TEXT")
_add_sqlite_column("exam_sessions", "ags_lineitem_url", "ags_lineitem_url TEXT")
_add_sqlite_column("exam_sessions", "ags_lineitems_url", "ags_lineitems_url TEXT")
_add_sqlite_column("exam_sessions", "ags_scopes_json", "ags_scopes_json TEXT")
_add_sqlite_column("exam_sessions", "ags_grading_user_override", "ags_grading_user_override VARCHAR")
_add_sqlite_column("exam_sessions", "ags_push_status", "ags_push_status VARCHAR DEFAULT 'not_synced'")
_add_sqlite_column("exam_sessions", "ags_last_push_message", "ags_last_push_message TEXT")
_add_sqlite_column("exam_sessions", "ags_last_pushed_at", "ags_last_pushed_at DATETIME")
_add_sqlite_column("submissions", "session_id", "session_id INTEGER")

app = FastAPI(title="Secure Exam IDE API")

# Configure CORS for local development and Tauri frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],  # Added Tauri origin and Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lti.router)
app.include_router(submissions.router)
app.include_router(questions.router)
app.include_router(exams.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"message": "Secure Exam IDE API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
