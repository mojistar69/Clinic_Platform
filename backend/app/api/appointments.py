from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Appointment
from app.schemas.schemas import (
    AppointmentCreate,
    AppointmentResponse
)


router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)



@router.post("/", response_model=AppointmentResponse)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db)
):

    last_number = (
        db.query(Appointment)
        .count()
    )


    new_appointment = Appointment(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        queue_number=last_number + 1
    )


    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    return new_appointment



@router.get("/queue")
def get_queue(
    db: Session = Depends(get_db)
):

    return (
        db.query(Appointment)
        .filter(
            Appointment.status == "WAITING"
        )
        .all()
    )