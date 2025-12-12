from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness_check():
    """Liveness probe - checks if the application process is running."""
    return {"status": "ok"}


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe - checks if the application can serve requests (DB connection)."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "message": "Database unavailable"}
        )
