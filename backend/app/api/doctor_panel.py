from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.auth.permissions import require_role

from app.models.models import (
    Appointment,
    Patient,
    Doctor
)

from app.models.user import User


router = APIRouter(
    prefix="/doctor-panel",
    tags=["Doctor Panel"]
)


# =========================================================
# Helpers
# =========================================================

def get_current_doctor(
    current_user: User,
    db: Session
):
    """
    Get the Doctor linked to the authenticated User.
    """

    if not current_user.doctor_id:
        raise HTTPException(
            status_code=400,
            detail="Doctor account is not linked to a doctor"
        )

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id == current_user.doctor_id
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    return doctor


def appointment_to_response(
    appointment: Appointment,
    db: Session
):
    """
    Convert appointment + patient information
    into a clean response.
    """

    patient = (
        db.query(Patient)
        .filter(
            Patient.id == appointment.patient_id
        )
        .first()
    )

    return {
        "appointment_id": appointment.id,
        "queue_number": appointment.queue_number,
        "patient_id": appointment.patient_id,
        "patient_name": (
            f"{patient.first_name} {patient.last_name}"
            if patient
            else None
        ),
        "appointment_time": appointment.appointment_time,
        "status": appointment.status
    }


# =========================================================
# Doctor Dashboard
# =========================================================

@router.get(
    "/dashboard/{queue_date}"
)
def doctor_dashboard(
    queue_date: str,
    current_user: User = Depends(
        require_role("DOCTOR")
    ),
    db: Session = Depends(get_db)
):

    doctor = get_current_doctor(
        current_user,
        db
    )

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == queue_date
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .all()
    )

    current_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == queue_date,
            Appointment.status == "IN_VISIT"
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .first()
    )

    next_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == queue_date,
            Appointment.status == "CALLED"
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .first()
    )

    if not next_appointment:
        next_appointment = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor.id,
                Appointment.appointment_date == queue_date,
                Appointment.status == "WAITING"
            )
            .order_by(
                Appointment.queue_number.asc()
            )
            .first()
        )

    return {
        "doctor": {
            "id": doctor.id,
            "name": doctor.name,
            "specialty": doctor.specialty,
            "room_number": doctor.room_number
        },

        "date": queue_date,

        "total_patients": len(appointments),

        "current_patient": (
            appointment_to_response(
                current_appointment,
                db
            )
            if current_appointment
            else None
        ),

        "next_patient": (
            appointment_to_response(
                next_appointment,
                db
            )
            if next_appointment
            else None
        )
    }


# =========================================================
# Call Next Patient
# =========================================================

@router.post(
    "/call-next/{queue_date}"
)
def call_next_patient(
    queue_date: str,
    current_user: User = Depends(
        require_role("DOCTOR")
    ),
    db: Session = Depends(get_db)
):

    doctor = get_current_doctor(
        current_user,
        db
    )

    # Prevent calling another patient
    # while a visit is already active.
    active_visit = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == queue_date,
            Appointment.status == "IN_VISIT"
        )
        .first()
    )

    if active_visit:
        raise HTTPException(
            status_code=400,
            detail="Doctor already has an active visit"
        )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == queue_date,
            Appointment.status == "WAITING"
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="No waiting patient found"
        )

    appointment.status = "CALLED"

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Patient called successfully",
        **appointment_to_response(
            appointment,
            db
        )
    }


# =========================================================
# Start Visit
# =========================================================

@router.post(
    "/start-visit/{queue_date}"
)
def start_visit(
    queue_date: str,
    current_user: User = Depends(
        require_role("DOCTOR")
    ),
    db: Session = Depends(get_db)
):

    doctor = get_current_doctor(
        current_user,
        db
    )

    active_visit = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == queue_date,
            Appointment.status == "IN_VISIT"
        )
        .first()
    )

    if active_visit:
        raise HTTPException(
            status_code=400,
            detail="Doctor already has an active visit"
        )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == queue_date,
            Appointment.status == "CALLED"
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="No called patient found"
        )

    appointment.status = "IN_VISIT"

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Visit started successfully",
        **appointment_to_response(
            appointment,
            db
        )
    }


# =========================================================
# End Visit
# =========================================================

@router.post(
    "/end-visit/{queue_date}"
)
def end_visit(
    queue_date: str,
    current_user: User = Depends(
        require_role("DOCTOR")
    ),
    db: Session = Depends(get_db)
):

    doctor = get_current_doctor(
        current_user,
        db
    )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == queue_date,
            Appointment.status == "IN_VISIT"
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="No active visit found"
        )

    appointment.status = "DONE"

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Visit completed successfully",
        **appointment_to_response(
            appointment,
            db
        )
    }