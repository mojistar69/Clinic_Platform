from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_role
from app.database.database import get_db
from app.models.models import Clinic
from app.models.user import User
from app.schemas.schemas import ClinicCreate, ClinicResponse


router = APIRouter(
    prefix="/clinics",
    tags=["Clinics"]
)


@router.post(
    "",
    response_model=ClinicResponse
)
def create_clinic(
    clinic: ClinicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    new_clinic = Clinic(
        name=clinic.name,
        address=clinic.address,
        phone=clinic.phone,
        is_active=True
    )

    db.add(new_clinic)
    db.commit()
    db.refresh(new_clinic)

    return new_clinic


@router.get(
    "",
    response_model=list[ClinicResponse]
)
def get_clinics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    return (
        db.query(Clinic)
        .filter(Clinic.is_active == True)
        .order_by(Clinic.id.asc())
        .all()
    )