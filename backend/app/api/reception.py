from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.permissions import require_role
from app.database.database import get_db
from app.models.models import (
    Appointment,
    Patient,
    Doctor,
    DailyDoctorQueue
)
from app.models.user import User
from app.api.websocket import manager

from app.services.realtime_service import (
    broadcast_queue_update,
    broadcast_patient_queue_updates
)
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


# =========================================================
# Call Next Patient
# =========================================================

@router.post(
    "/queue/{doctor_id}/{queue_date}/call-next"
)
async def call_next_patient(
    doctor_id: int,
    queue_date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("RECEPTIONIST", "ADMIN")
    )
):
    # -----------------------------------------------------
    # 1. Check doctor
    # -----------------------------------------------------

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id == doctor_id
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # -----------------------------------------------------
    # 2. Check queue
    # -----------------------------------------------------

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

    if queue.status != "OPEN":
        raise HTTPException(
            status_code=400,
            detail="Queue is not open"
        )

    # -----------------------------------------------------
    # 3. Prevent calling another patient
    #    while one patient is already in visit
    # -----------------------------------------------------

    active_visit = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
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

    # -----------------------------------------------------
    # 4. Find next patient
    # -----------------------------------------------------

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == queue_date,
            Appointment.status.in_([
                "WAITING",
                "CONFIRMED"
            ])
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

    # -----------------------------------------------------
    # 5. Call patient
    # -----------------------------------------------------

    appointment.status = "CALLED"

    db.commit()
    db.refresh(appointment)
    await manager.broadcast_queue(
    doctor_id=appointment.doctor_id,
    queue_date=appointment.appointment_date,
    message={
        "type": "PATIENT_CALLED",
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "queue_number": appointment.queue_number,
        "appointment_time": appointment.appointment_time,
        "status": appointment.status
    }
)

    await manager.broadcast_patient(
    appointment_id=appointment.id,
    message={
        "type": "APPOINTMENT_STATUS_CHANGED",
        "appointment_id": appointment.id,
        "queue_number": appointment.queue_number,
        "status": appointment.status,
        "message": "نوبت شما فراخوانده شد"
    }
)           
    print(
    "WS QUEUE UPDATE:",
    appointment.doctor_id,
    appointment.appointment_date
)
    await broadcast_queue_update(
    db,
    appointment.doctor_id,
    appointment.appointment_date
)
    await broadcast_patient_queue_updates(
    db,
    appointment.doctor_id,
    appointment.appointment_date
)
    # -----------------------------------------------------
    # 6. Patient information
    # -----------------------------------------------------

    patient = (
        db.query(Patient)
        .filter(
            Patient.id == appointment.patient_id
        )
        .first()
    )

    return {
        "message": "Next patient called successfully",
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "patient_name": (
            f"{patient.first_name} {patient.last_name}"
            if patient
            else None
        ),
        "doctor_id": appointment.doctor_id,
        "queue_date": appointment.appointment_date,
        "queue_number": appointment.queue_number,
        "appointment_time": appointment.appointment_time,
        "status": appointment.status
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