import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud import resume as resume_crud
from app.db.database import get_db
from app.models.user import User
from app.schemas.resume import ResumeRead
from app.services.resume_analysis import analyze_resume
from app.services.resume_parsing import (
    PdfExtractionError,
    extract_text_from_pdf,
    parse_sections,
)
from app.services.resume_storage import ResumeUploadError, save_resume_file, validate_and_read

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/", response_model=ResumeRead, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = await validate_and_read(file)
    except ResumeUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        text = extract_text_from_pdf(data)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parsed = parse_sections(text)
    analysis = analyze_resume(parsed, text)

    # Only written to disk once every validation step above has passed.
    stored_filename = save_resume_file(data)

    return resume_crud.create_resume(
        db,
        user_id=current_user.id,
        stored_filename=stored_filename,
        original_filename=file.filename or "resume.pdf",
        content_type=file.content_type or "application/pdf",
        size_bytes=len(data),
        extracted_text=text,
        parsed=parsed,
        analysis=analysis,
    )


@router.get("/", response_model=list[ResumeRead])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All of the current user's previously uploaded resumes, newest first
    — lets the setup page offer "use a previous resume" instead of
    requiring a fresh upload every time (see frontend/src/pages/
    InterviewSetupPage.jsx). A resume can already be attached to any number
    of interviews (Interview.resume_id has no uniqueness constraint); this
    just makes that reuse actually reachable from the UI."""
    return resume_crud.list_resumes(db, current_user.id)


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = resume_crud.get_resume(db, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resume"
        )
    return resume
