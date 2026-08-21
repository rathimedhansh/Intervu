from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.crud import user as user_crud
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import TokenRead, UserCreate, UserLogin, UserRead

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
