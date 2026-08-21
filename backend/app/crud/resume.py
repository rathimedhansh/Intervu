from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.services.resume_analysis import ResumeAnalysis
from app.services.resume_parsing import ParsedResume


def create_resume(
    db: Session,
    *,
    user_id: int,
    stored_filename: str,
    original_filename: str,
    content_type: str,
    size_bytes: int,
    extracted_text: str,
    parsed: ParsedResume,
    analysis: ResumeAnalysis,
) -> Resume:
    resume = Resume(
        user_id=user_id,
        stored_filename=stored_filename,
        original_filename=original_filename[:255],
        content_type=content_type,
        size_bytes=size_bytes,
        extracted_text=extracted_text,
        parsed=parsed.to_dict(),
        analysis=analysis.to_dict(),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def get_resume(db: Session, resume_id: int) -> Resume | None:
    return db.get(Resume, resume_id)


def list_resumes(db: Session, user_id: int) -> list[Resume]:
    return (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .all()
    )
