from fastapi import FastAPI
from .database import engine, Base
from .routes import lti

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Secure Exam IDE API")

app.include_router(lti.router)

@app.get("/")
def read_root():
    return {"message": "Secure Exam IDE API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
