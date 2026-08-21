from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud import answer as answer_crud
from app.crud import interview as interview_crud
from app.crud import interview_flow as interview_flow_crud
from app.crud import question as question_crud
from app.db.database import get_db
from app.models.interview import Interview
from app.models.user import User
from app.schemas.answer import AnswerCreate, AnswerRead
from app.schemas.interview import (
    InterviewComplete,
    InterviewCreate,
    InterviewRead,
    InterviewSummary,
    InterviewTurnRead,
)

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _get_owned_interview(db: Session, interview_id: int, user: User) -> Interview:
    interview = interview_crud.get_interview(db, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    if interview.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this interview"
        )
    return interview


@router.post("/", response_model=InterviewRead, status_code=201)
def create_interview(
    payload: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return interview_crud.create_interview(
            db,
            role=payload.role,
            difficulty=payload.difficulty,
            question_count=payload.question_count,
            user_id=current_user.id,
            resume_id=payload.resume_id,
            focus_categories=payload.focus_categories,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/", response_model=list[InterviewSummary])
def list_interviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return interview_crud.list_interviews(db, current_user.id)


@router.get("/{interview_id}", response_model=InterviewRead)
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_interview(db, interview_id, current_user)


@router.delete("/{interview_id}")
def delete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes an interview (pending or completed) and everything under it
    — see app.crud.interview.delete_interview for the cascade behavior.
    Lets the History page (frontend/src/pages/HistoryPage.jsx) offer
    cleanup for test runs and abandoned in-progress interviews, which
    otherwise live forever and skew the dashboard's aggregate scores."""
    interview = _get_owned_interview(db, interview_id, current_user)
    interview_crud.delete_interview(db, interview)
    return {"deleted": True}


@router.post("/{interview_id}/complete", response_model=InterviewRead)
def complete_interview(
    interview_id: int,
    payload: InterviewComplete = InterviewComplete(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_owned_interview(db, interview_id, current_user)
    camera_metrics = (
        payload.camera_metrics.model_dump() if payload.camera_metrics else None
    )
    return interview_crud.complete_interview(db, interview, camera_metrics)


@router.post(
    "/{interview_id}/questions/{question_id}/answer", response_model=AnswerRead
)
def answer_question(
    interview_id: int,
    question_id: int,
    payload: AnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_interview(db, interview_id, current_user)
    question = question_crud.get_question(db, question_id)
    if question is None or question.interview_id != interview_id:
        raise HTTPException(status_code=404, detail="Question not found")
    speech_metrics = (
        payload.speech_metrics.model_dump() if payload.speech_metrics else None
    )
    return answer_crud.submit_answer(db, question, payload.text, speech_metrics)


@router.post(
    "/{interview_id}/questions/{question_id}/respond", response_model=InterviewTurnRead
)
def respond_to_question(
    interview_id: int,
    question_id: int,
    payload: AnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """One turn of the conversational interview flow: save + evaluate the
    answer, then decide and persist the next question (or signal
    completion). See app.crud.interview_flow.advance_conversation."""
    interview = _get_owned_interview(db, interview_id, current_user)

    if interview.status == "completed":
        raise HTTPException(status_code=409, detail="Interview is already completed")
    if interview.question_count is None:
        raise HTTPException(
            status_code=400,
            detail="This interview does not support the conversational flow",
        )

    question = question_crud.get_question(db, question_id)
    if question is None or question.interview_id != interview_id:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.answer is not None:
        raise HTTPException(
            status_code=409, detail="This question has already been answered"
        )

    speech_metrics = (
        payload.speech_metrics.model_dump() if payload.speech_metrics else None
    )
    return interview_flow_crud.advance_conversation(
        db, interview, question, payload.text, speech_metrics
    )
