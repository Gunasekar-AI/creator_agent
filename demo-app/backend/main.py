
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

from models import LoginRequest, LoginResponse
from auth_service import authenticate_user

app = FastAPI(title="QA Reusability Demo Application")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/login", response_model=LoginResponse)
def login(request: LoginRequest):
    if authenticate_user(request.username, request.password):
        return LoginResponse(
            success=True,
            message="Login successful",
            username=request.username
        )

    return LoginResponse(
        success=False,
        message="Invalid username or password"
    )


@app.get("/api/dashboard")
def dashboard():
    return {
        "title": "Dashboard",
        "message": "Welcome to the QA Demo Application"
    }
