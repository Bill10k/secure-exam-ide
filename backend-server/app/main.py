from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import lti, submissions, questions, exams, admin

# Create database tables
Base.metadata.create_all(bind=engine)

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
