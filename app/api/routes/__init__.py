from fastapi import APIRouter
from app.api.routes import health, capture, email_ingest, scraper, internal, analysis, timeline, exports

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(capture.router, prefix="/applications", tags=["capture"])
api_router.include_router(email_ingest.router, prefix="/emails", tags=["email-ingest"])
api_router.include_router(scraper.router, prefix="/scraper", tags=["scraper"])
api_router.include_router(analysis.router, prefix="/applications", tags=["analysis"])
api_router.include_router(timeline.router, prefix="/applications", tags=["timeline"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(internal.router)
