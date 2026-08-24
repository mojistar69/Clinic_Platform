from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.permissions import require_role
from app.database.database import get_db
from app.models.models import Appointment, Doctor, DailyDoctorQueue
from app.models.user import User


router = APIRouter(
    prefix="/reception",
    tags=["Reception"]
)


def get_appointment(
    appointment_id: int,
    db: Session
):
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    return appointment


@router.get(
    "/queue/{doctor_id}/{queue_date}"
)
def get_reception_queue(
    doctor_id: int,
    queue_date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("RECEPTIONIST", "ADMIN")
    )
):
    doctor = (
        db.query(Doctor)
        .filter(Doctor.id == doctor_id)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    queue = (
        db.query(DailyDoctorQueue)
        .filter(
            DailyDoctorQueue.doctor_id == doctor_id,
            DailyDoctorQueue.queue_date == queue_date
        )
        .first()
    )

    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Daily queue not found"
        )

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == queue_date
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .all()
    )

    return {
        "doctor_id": doctor_id,
        "queue_date": queue_date,
        "queue_status": queue.status,
        "capacity": queue.capacity,
        "current_number": queue.current_number,
        "appointments": [
            {
                "id": appointment.id,
                "patient_id": appointment.patient_id,
                "queue_number": appointment.queue_number,
                "status": appointment.status,
                "appointment_time": appointment.appointment_time
            }
            for appointment in appointments
        ]
    }


@router.patch(
    "/appointments/{appointment_id}/confirm"
)
def confirm_patient(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("RECEPTIONIST", "ADMIN")
    )
):
    appointment = get_appointment(
        appointment_id,
        db
    )

    if appointment.status != "WAITING":
        raise HTTPException(
            status_code=400,
            detail="Only WAITING appointments can be confirmed"
        )

    appointment.status = "CONFIRMED"

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Patient attendance confirmed",
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "doctor_id": appointment.doctor_id,
        "queue_number": appointment.queue_number,
        "status": appointment.status,
        "appointment_time": appointment.appointment_time
    }


@router.patch(
    "/appointments/{appointment_id}/call"
)
def call_patient(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("RECEPTIONIST", "ADMIN")
    )
):
    appointment = get_appointment(
        appointment_id,
        db
    )

    if appointment.status not in (
        "WAITING",
        "CONFIRMED"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only WAITING or CONFIRMED appointments "
                "can be called"
            )
        )

    appointment.status = "CALLED"

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Patient called successfully",
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "doctor_id": appointment.doctor_id,
        "queue_number": appointment.queue_number,
        "status": appointment.status,
        "appointment_time": appointment.appointment_time
    }


@router.patch(
    "/appointments/{appointment_id}/no-show"
)
def mark_no_show(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("RECEPTIONIST", "ADMIN")
    )
):
    appointment = get_appointment(
        appointment_id,
        db
    )

    if appointment.status not in (
        "WAITING",
        "CONFIRMED",
        "CALLED"
    ):
        raise HTTPException(
            status_code=400,
            detail="This appointment cannot be marked as NO_SHOW"
        )

    appointment.status = "NO_SHOW"

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Appointment marked as NO_SHOW",
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "doctor_id": appointment.doctor_id,
        "queue_number": appointment.queue_number,
        "status": appointment.status,
        "appointment_time": appointment.appointment_time
    }