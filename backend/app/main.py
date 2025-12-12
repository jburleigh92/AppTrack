from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.routes import api_router
from app.api.error_handlers import register_error_handlers
from app.db.session import init_db


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    # Configure logging
    configure_logging(settings)
    
    # Initialize database
    init_db(settings.DATABASE_URL)
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        debug=settings.DEBUG
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Register error handlers
    register_error_handlers(app)
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    return app


app = create_app()
