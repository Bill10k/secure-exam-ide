from fastapi import FastAPI

app = FastAPI(title="Secure Exam IDE API")


@app.get("/")
def read_root():
    return {"message": "Secure Exam IDE API"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
