import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.database import init_db
from backend.routers import session, report

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database tables on startup
    init_db()
    yield

app = FastAPI(title="InterviewSense Backend", lifespan=lifespan)

# Configure CORS
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(session.router)
app.include_router(report.router)

@app.get("/health")
def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}
