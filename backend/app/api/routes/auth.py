import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token
from app.crud import user as user_crud
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    TokenRead,
    UserCreate,
    UserLogin,
    UserRead,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenRead, status_code=201)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        user = user_crud.create_user(
            db, name=payload.name, email=payload.email, password=payload.password
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token = create_access_token(user.id)
    return TokenRead(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenRead)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = user_crud.authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(user.id)
    return TokenRead(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Always the same response whether or not the email is registered —
    # never lets a caller use this endpoint to discover which emails have
    # accounts. Only the presence/absence of `reset_link` differs, and only
    # in dev mode where it's returned directly instead of emailed.
    response = ForgotPasswordResponse()

    user = user_crud.get_user_by_email(db, payload.email)
    if user is None:
        return response

    plaintext_token = user_crud.create_password_reset_token(db, user)
    reset_link = f"{settings.frontend_base_url}/reset-password?token={plaintext_token}"

    # Stands in for real email delivery until a mailer is wired up (see
    # Settings.password_reset_dev_mode) — this is the only place the link
    # is ever surfaced today.
    logger.info("Password reset requested for user %s: %s", user.id, reset_link)

    if settings.password_reset_dev_mode:
        response.reset_link = reset_link
    return response


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_record = user_crud.get_valid_reset_token(db, payload.token)
    if token_record is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")

    user_crud.reset_password(db, token_record, payload.new_password)
    return {"detail": "Password updated — you can now log in with your new password."}
