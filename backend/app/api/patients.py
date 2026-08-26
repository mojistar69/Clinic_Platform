from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_role
from app.database.database import get_db
from app.models.models import Patient
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.schemas.schemas import (
    PatientCreate,
    PatientResponse
)


router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


@router.post(
    "/",
    response_model=PatientResponse
)
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "RECEPTIONIST")
    )
):
    existing_mobile = (
        db.query(Patient)
        .filter(Patient.mobile == patient.mobile)
        .first()
    )

    if existing_mobile:
        raise HTTPException(
            status_code=409,
            detail="A patient with this mobile already exists"
        )

    if patient.national_code:
        existing_national_code = (
            db.query(Patient)
            .filter(
                Patient.national_code == patient.national_code
            )
            .first()
        )

        if existing_national_code:
            raise HTTPException(
                status_code=409,
                detail="A patient with this national code already exists"
            )

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


@router.get(
    "/",
    response_model=list[PatientResponse]
)
def get_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "RECEPTIONIST")
    )
):
    return (
        db.query(Patient)
        .order_by(Patient.id.asc())
        .all()
    )


@router.get(
    "/me",
    response_model=PatientResponse
)
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(
        "PATIENT_ME DEBUG:",
        current_user.id,
        current_user.role,
        current_user.patient_id
    )

    if current_user.role != "PATIENT":
        raise HTTPException(
            status_code=403,
            detail="Only patients can access their own profile"
        )

    if current_user.patient_id is None:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    patient = (
        db.query(Patient)
        .filter(
            Patient.id == current_user.patient_id
        )
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient


@router.get(
    "/by-id/{patient_id}",
    response_model=PatientResponse
)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "PATIENT":
        if current_user.patient_id != patient_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

    elif current_user.role not in (
        "ADMIN",
        "RECEPTIONIST"
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    patient = (
        db.query(Patient)
        .filter(Patient.id == patient_id)
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient
    
    
@router.get(
    "/profile",
    response_model=PatientResponse
)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.patient_id is None:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    patient = (
        db.query(Patient)
        .filter(
            Patient.id == current_user.patient_id
        )
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient