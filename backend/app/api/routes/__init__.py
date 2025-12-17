from fastapi import APIRouter
from app.api.routes import (
    advisory,
    health,
    capture,
    email_ingest,
    scraper,
    internal,
    analysis,
    timeline,
    exports,
    resume,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(capture.router, prefix="/applications", tags=["capture"])
api_router.include_router(email_ingest.router, prefix="/emails", tags=["email-ingest"])
api_router.include_router(scraper.router, prefix="/scraper", tags=["scraper"])
api_router.include_router(advisory.router, prefix="/advisory", tags=["advisory"])
api_router.include_router(analysis.router, prefix="/applications", tags=["analysis"])
api_router.include_router(timeline.router, prefix="/applications", tags=["timeline"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(resume.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(internal.router)
