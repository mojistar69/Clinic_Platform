from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import jdatetime

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
# Dashboard
# =========================================================

@router.get("/dashboard")
def doctor_dashboard(
    current_user: User = Depends(
        require_role("DOCTOR")
    ),
    db: Session = Depends(get_db)
):

    # 1. پیدا کردن پزشک

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

    # 2. تاریخ امروز شمسی

    today = jdatetime.date.today().strftime(
        "%Y-%m-%d"
    )

    # 3. تمام نوبت‌های امروز

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == today
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .all()
    )

    # 4. بیمار فعلی

    current_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == today,
            Appointment.status == "IN_VISIT"
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .first()
    )

    # 5. بیمار بعدی

    next_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == today,
            Appointment.status == "WAITING"
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .first()
    )

    # 6. ساخت current patient

    current_patient = None

    if current_appointment:

        patient = (
            db.query(Patient)
            .filter(
                Patient.id == current_appointment.patient_id
            )
            .first()
        )

        current_patient = {
            "queue_number": current_appointment.queue_number,
            "patient_id": patient.id if patient else None,
            "patient_name": (
                f"{patient.first_name} {patient.last_name}"
                if patient
                else None
            ),
            "status": current_appointment.status
        }

    # 7. ساخت next patient

    next_patient = None

    if next_appointment:

        patient = (
            db.query(Patient)
            .filter(
                Patient.id == next_appointment.patient_id
            )
            .first()
        )

        next_patient = {
            "queue_number": next_appointment.queue_number,
            "patient_id": patient.id if patient else None,
            "patient_name": (
                f"{patient.first_name} {patient.last_name}"
                if patient
                else None
            ),
            "status": next_appointment.status
        }

    # 8. پاسخ

    return {
        "doctor": {
            "id": doctor.id,
            "name": doctor.name,
            "specialty": doctor.specialty,
            "room_number": doctor.room_number
        },

        "today": {
            "date": today,
            "total_patients": len(appointments)
        },

        "current_patient": current_patient,

        "next_patient": next_patient
    }


# =========================================================
# Call Next Patient
# =========================================================

@router.post("/call-next")
def call_next_patient(
    current_user: User = Depends(
        require_role("DOCTOR")
    ),
    db: Session = Depends(get_db)
):

    if not current_user.doctor_id:
        raise HTTPException(
            status_code=400,
            detail="Doctor account is not linked to a doctor"
        )

    today = jdatetime.date.today().strftime(
        "%Y-%m-%d"
    )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == current_user.doctor_id,
            Appointment.appointment_date == today,
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

    patient = (
        db.query(Patient)
        .filter(
            Patient.id == appointment.patient_id
        )
        .first()
    )

    return {
        "message": "Patient called successfully",
        "queue_number": appointment.queue_number,
        "patient_id": appointment.patient_id,
        "patient_name": (
            f"{patient.first_name} {patient.last_name}"
            if patient
            else None
        ),
        "status": appointment.status
    }


# =========================================================
# Start Visit
# =========================================================

@router.post("/start-visit")
def start_visit(
    current_user: User = Depends(
        require_role("DOCTOR")
    ),
    db: Session = Depends(get_db)
):

    if not current_user.doctor_id:
        raise HTTPException(
            status_code=400,
            detail="Doctor account is not linked to a doctor"
        )

    today = jdatetime.date.today().strftime(
        "%Y-%m-%d"
    )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == current_user.doctor_id,
            Appointment.appointment_date == today,
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

    patient = (
        db.query(Patient)
        .filter(
            Patient.id == appointment.patient_id
        )
        .first()
    )

    return {
        "message": "Visit started successfully",
        "queue_number": appointment.queue_number,
        "patient_id": appointment.patient_id,
        "patient_name": (
            f"{patient.first_name} {patient.last_name}"
            if patient
            else None
        ),
        "status": appointment.status
    }


# =========================================================
# End Visit
# =========================================================

@router.post("/end-visit")
def end_visit(
    current_user: User = Depends(
        require_role("DOCTOR")
    ),
    db: Session = Depends(get_db)
):

    if not current_user.doctor_id:
        raise HTTPException(
            status_code=400,
            detail="Doctor account is not linked to a doctor"
        )

    today = jdatetime.date.today().strftime(
        "%Y-%m-%d"
    )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == current_user.doctor_id,
            Appointment.appointment_date == today,
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

    patient = (
        db.query(Patient)
        .filter(
            Patient.id == appointment.patient_id
        )
        .first()
    )

    return {
        "message": "Visit completed successfully",
        "queue_number": appointment.queue_number,
        "patient_id": appointment.patient_id,
        "patient_name": (
            f"{patient.first_name} {patient.last_name}"
            if patient
            else None
        ),
        "status": appointment.status
    }