from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Clinic
from app.schemas.schemas import ClinicCreate, ClinicResponse


router = APIRouter(
    prefix="/clinics",
    tags=["Clinics"]
)


@router.post("/", response_model=ClinicResponse)
def create_clinic(
    clinic: ClinicCreate,
    db: Session = Depends(get_db)
):

    new_clinic = Clinic(
        name=clinic.name,
        address=clinic.address,
        phone=clinic.phone
    )

    db.add(new_clinic)
    db.commit()
    db.refresh(new_clinic)

    return new_clinic


@router.get("/", response_model=list[ClinicResponse])
def get_clinics(
    db: Session = Depends(get_db)
):

    return db.query(Clinic).all()