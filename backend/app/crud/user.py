from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.strip().lower()).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, name: str, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    if get_user_by_email(db, normalized_email) is not None:
        raise ValueError("Email already registered")

    user = User(
        name=name.strip(),
        email=normalized_email,
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Race with a concurrent signup for the same email; the unique
        # constraint is the source of truth, the check above is just a
        # fast path for the common case.
        db.rollback()
        raise ValueError("Email already registered") from None
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
