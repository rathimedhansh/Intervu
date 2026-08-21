from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud import dashboard as dashboard_crud
from app.db.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_model=DashboardRead)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return dashboard_crud.get_dashboard_stats(db, current_user.id)
