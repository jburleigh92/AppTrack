from fastapi import FastAPI
from app.api.error_handlers.handlers import (
    http_exception_handler,
    general_exception_handler
)
from fastapi.exceptions import HTTPException


def register_error_handlers(app: FastAPI) -> None:
    """Register global error handlers for the FastAPI application."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
