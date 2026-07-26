# ExamIDE / ProctorIDE

This repository contains a secure programming exam environment with:

- `backend-server/`: FastAPI backend API for exam sessions, LTI integration, submissions, question management, and admin routes.
- `ProctorIDE/`: Tauri + React desktop application frontend powered by Vite and Monaco Editor.
- `sandbox/`: Docker support for running the backend in an isolated container.
- `scripts/`: Utility scripts for development and deployment.

---

## Overview

ExamIDE is intended as a secure exam platform for offline programming assessments. The backend exposes REST endpoints and LTI integration, while the `ProctorIDE` desktop app provides the exam interface and editor experience.

---

## Prerequisites

- Node.js 18+ and npm
- Python 3.13+ (the backend `requirements.txt` is built for modern Python)
- Rust toolchain + Cargo if you want to run the Tauri desktop app
- `pip` for Python dependency installation
- `npm` for frontend dependency installation
- `docker` if you want to run the sandbox container

---

## Backend Setup (`backend-server`)

1. Open a terminal and change into the backend folder:

   ```powershell
   cd backend-server
   ```

2. Create and activate a virtual environment (recommended):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. Install Python dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Start the FastAPI server using Uvicorn:

   ```powershell
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Or, if you want to run it through Python:

   ```powershell
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Verify the backend is running:

   - `http://localhost:8000/`
   - `http://localhost:8000/health`

### Notes

- The backend package is located at `backend-server/app`.
- The FastAPI app instance is defined in `backend-server/app/main.py`.
- `uvicorn app.main:app` uses that module path to start the API server.

---

## Frontend / Desktop App Setup (`ProctorIDE`)

1. Open a terminal and change into the frontend folder:

   ```powershell
   cd ProctorIDE
   ```

2. Install Node dependencies:

   ```powershell
   npm install
   ```

3. Start the frontend in development mode:

   ```powershell
   npm run dev
   ```

4. To run the Tauri desktop app locally:

   ```powershell
   npm run tauri dev
   ```

5. To build the frontend for production:

   ```powershell
   npm run build
   ```

6. To preview a built web app:

   ```powershell
   npm run preview
   ```

### Notes

- The main desktop application is in `ProctorIDE/src`.
- This project uses React + TypeScript + Tailwind CSS with Tauri integration.
- You can run the backend and frontend simultaneously during development.

---

## Optional: Run Backend in Docker (`sandbox`)

The `sandbox/dockerfile` is available for containerizing the backend.

1. Build the Docker image:

   ```powershell
   cd sandbox
   docker build -t examide-backend .
   ```

2. Run the container:

   ```powershell
   docker run --rm -p 8000:8000 examide-backend
   ```

3. The backend will be exposed at:

   - `http://localhost:8000`

---

## Useful Files

- `backend-server/app/main.py` — FastAPI application startup and routing.
- `backend-server/requirements.txt` — backend Python dependencies.
- `ProctorIDE/package.json` — frontend scripts, dependencies, and Tauri configuration.
- `sandbox/dockerfile` — Dockerfile for the backend environment.
- `backend-server/generate_keys.py` and `backend-server/update_lti.py` — utility scripts for LTI and keys.

---

## Running the Full System

1. Start the backend server.
2. Start the desktop frontend or use the Tauri app.
3. Open the app and connect to the backend at `http://localhost:8000`.

If you encounter CORS or connection issues, verify the backend is running and that the frontend is configured to call the correct local API URL.
