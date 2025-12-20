"""UI routes for serving HTML templates"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def resume_upload_page(request: Request):
    """Serve resume upload page"""
    return templates.TemplateResponse("resume_upload.html", {"request": request})


@router.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    """Serve job search page (universal, no resume required)"""
    return templates.TemplateResponse("jobs.html", {"request": request})


@router.get("/jobs/recommended", response_class=HTMLResponse)
async def recommended_jobs_page(request: Request):
    """Serve AI-powered job recommendations page (requires resume)"""
    return templates.TemplateResponse("recommended.html", {"request": request})


@router.get("/applications", response_class=HTMLResponse)
async def applications_page(request: Request):
    """Serve applications dashboard page"""
    return templates.TemplateResponse("applications.html", {"request": request})
