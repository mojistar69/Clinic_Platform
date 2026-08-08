from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Patient
from app.schemas.schemas import (
    PatientCreate,
    PatientResponse
)


router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)



@router.post("/", response_model=PatientResponse)
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db)
):

    new_patient = Patient(
        first_name=patient.first_name,
        last_name=patient.last_name,
        mobile=patient.mobile,
        national_code=patient.national_code,
        birth_date=patient.birth_date
    )


    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return new_patient



@router.get("/", response_model=list[PatientResponse])
def get_patients(
    db: Session = Depends(get_db)
):

    return db.query(Patient).all()