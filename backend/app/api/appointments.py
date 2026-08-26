from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import jdatetime

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_role
from app.database.database import get_db
from app.models.models import (
    Appointment,
    Patient,
    Doctor,
    DoctorSchedule,
    DailyDoctorQueue
)
from app.models.user import User
from app.schemas.appointment import (
    AppointmentBookRequest,
    AppointmentResponse
)
from app.services.appointment_service import (
    calculate_appointment_time
)


router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)

# =========================================================
# My Recent Appointments
# =========================================================

@router.get(
    "/my/recent",
    response_model=list[AppointmentResponse]
)
def get_my_recent_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PATIENT"))
):
    if current_user.patient_id is None:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    return (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == current_user.patient_id,
            Appointment.appointment_date <= today
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.id.desc()
        )
        .limit(10)
        .all()
    )


# =========================================================
# My Upcoming Appointments
# =========================================================

@router.get(
    "/my/upcoming",
    response_model=list[AppointmentResponse]
)
def get_my_upcoming_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PATIENT"))
):
    if current_user.patient_id is None:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    return (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == current_user.patient_id,
            Appointment.appointment_date >= today,
            Appointment.status.in_([
                "WAITING",
                "CONFIRMED",
                "CALLED",
                "IN_VISIT"
            ])
        )
        .order_by(
            Appointment.appointment_date.asc(),
            Appointment.queue_number.asc()
        )
        .all()
    )


# =========================================================
# My Appointment History
# =========================================================

@router.get(
    "/my/history",
    response_model=list[AppointmentResponse]
)
def get_my_appointment_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("PATIENT"))
):
    if current_user.patient_id is None:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    return (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == current_user.patient_id
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.queue_number.desc()
        )
        .all()
    )


# =========================================================
# Cancel My Appointment
# =========================================================
@router.patch(
    "/my/{appointment_id}/cancel",
    response_model=AppointmentResponse
)
def cancel_my_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("PATIENT")
    )
):
    if current_user.patient_id is None:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    # Find appointment belonging to current patient
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == current_user.patient_id
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # Only active appointments can be cancelled
    if appointment.status not in (
        "WAITING",
        "CONFIRMED"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only WAITING or CONFIRMED appointments "
                "can be cancelled"
            )
        )

    today = jdatetime.date.today().strftime(
        "%Y-%m-%d"
    )

    if appointment.appointment_date < today:
        raise HTTPException(
            status_code=400,
            detail="Past appointments cannot be cancelled"
        )

    # Cancel appointment
    appointment.status = "CANCELLED"

    # Find daily queue
    queue = (
        db.query(DailyDoctorQueue)
        .filter(
            DailyDoctorQueue.doctor_id == appointment.doctor_id,
            DailyDoctorQueue.queue_date == appointment.appointment_date
        )
        .first()
    )

    # Recalculate active appointments
    active_appointments_count = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.appointment_date == appointment.appointment_date,
            Appointment.status.notin_([
                "CANCELLED",
                "NO_SHOW"
            ])
        )
        .count()
    )

    # If there is available capacity, reopen the queue
    if queue:
        if active_appointments_count < queue.capacity:
            queue.status = "OPEN"
        else:
            queue.status = "FULL"

    db.commit()
    db.refresh(appointment)

    return appointment
# =========================================================
# Book Appointment
# =========================================================

@router.post(
    "/book",
    response_model=AppointmentResponse
)
def book_appointment(
    request: AppointmentBookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("PATIENT")
    )
):
    # -----------------------------------------------------
    # 1. Current patient
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 2. Doctor
    # -----------------------------------------------------

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id == request.doctor_id
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # -----------------------------------------------------
    # 3. Daily queue
    # -----------------------------------------------------

    queue = (
        db.query(DailyDoctorQueue)
        .filter(
            DailyDoctorQueue.doctor_id == request.doctor_id,
            DailyDoctorQueue.queue_date == request.queue_date
        )
        .first()
    )

    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Daily queue not found"
        )

    # -----------------------------------------------------
    # 4. Queue must be open
    # -----------------------------------------------------

    if queue.status not in ("OPEN",):
        raise HTTPException(
            status_code=400,
            detail="Appointment booking is not open"
        )

    # -----------------------------------------------------
    # 5. Prevent duplicate appointment
    # -----------------------------------------------------

    existing = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient.id,
            Appointment.doctor_id == request.doctor_id,
            Appointment.appointment_date == request.queue_date,
            Appointment.status.notin_([
                "CANCELLED",
                "NO_SHOW"
            ])
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                "Patient already has an appointment "
                "for this doctor on this date"
            )
        )

    # -----------------------------------------------------
    # 6. Count ACTIVE appointments
    # -----------------------------------------------------

    active_appointments_count = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == request.doctor_id,
            Appointment.appointment_date == request.queue_date,
            Appointment.status.notin_([
                "CANCELLED",
                "NO_SHOW"
            ])
        )
        .count()
    )

    # -----------------------------------------------------
    # 7. Check capacity
    # -----------------------------------------------------

    if active_appointments_count >= queue.capacity:
        queue.status = "FULL"
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Appointment capacity is full"
        )

    # -----------------------------------------------------
    # 8. Validate Jalali date
    # -----------------------------------------------------

    try:
        appointment_date = jdatetime.datetime.strptime(
            request.queue_date,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid Jalali date format. "
                "Expected YYYY-MM-DD"
            )
        )

    # -----------------------------------------------------
    # 9. Check doctor's schedule
    # -----------------------------------------------------

    weekday = appointment_date.weekday()

    schedule = (
        db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.doctor_id == request.doctor_id,
            DoctorSchedule.weekday == weekday,
            DoctorSchedule.is_active == True
        )
        .first()
    )

    if not schedule:
        raise HTTPException(
            status_code=400,
            detail="Doctor has no active schedule for this day"
        )

    # -----------------------------------------------------
    # 10. Generate next queue number
    # -----------------------------------------------------

    next_number = queue.current_number + 1

    # -----------------------------------------------------
    # 11. Calculate appointment time
    # -----------------------------------------------------

    appointment_time = calculate_appointment_time(
        schedule.start_time,
        next_number,
        schedule.slot_duration
    )

    # -----------------------------------------------------
    # 12. Create appointment
    # -----------------------------------------------------

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=request.doctor_id,
        appointment_date=request.queue_date,
        queue_number=next_number,
        status="WAITING",
        appointment_time=appointment_time
    )

    db.add(appointment)

    # -----------------------------------------------------
    # 13. Update queue
    # -----------------------------------------------------

    queue.current_number = next_number

    new_active_count = active_appointments_count + 1

    if new_active_count >= queue.capacity:
        queue.status = "FULL"
    else:
        queue.status = "OPEN"

    # -----------------------------------------------------
    # 14. Commit
    # -----------------------------------------------------

    db.commit()
    db.refresh(appointment)

    return appointment

# =========================================================
# Helper: validate patient access
# =========================================================

def validate_patient_access(
    patient_id: int,
    current_user: User
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


# =========================================================
# Recent Appointments
# =========================================================

@router.get(
    "/patient/{patient_id}/recent",
    response_model=list[AppointmentResponse]
)
def get_recent_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    validate_patient_access(
        patient_id,
        current_user
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

    today = jdatetime.date.today().strftime(
        "%Y-%m-%d"
    )

    return (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date <= today
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.id.desc()
        )
        .limit(5)
        .all()
    )


# =========================================================
# Upcoming Appointments
# =========================================================

@router.get(
    "/patient/{patient_id}/upcoming",
    response_model=list[AppointmentResponse]
)
def get_upcoming_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    validate_patient_access(
        patient_id,
        current_user
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

    today = jdatetime.date.today().strftime(
        "%Y-%m-%d"
    )

    return (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date >= today,
            Appointment.status.in_([
                "WAITING",
                "CONFIRMED",
                "CALLED",
                "IN_VISIT"
            ])
        )
        .order_by(
            Appointment.appointment_date.asc(),
            Appointment.queue_number.asc()
        )
        .all()
    )


# =========================================================
# Appointment History
# =========================================================

@router.get(
    "/patient/{patient_id}/history",
    response_model=list[AppointmentResponse]
)
def get_patient_appointment_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    validate_patient_access(
        patient_id,
        current_user
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

    today = jdatetime.date.today().strftime(
        "%Y-%m-%d"
    )

    return (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date < today
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.queue_number.desc()
        )
        .all()
    )


# =========================================================
# Get Single Appointment
# =========================================================

@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse
)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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

    if current_user.role == "PATIENT":
        if current_user.patient_id != appointment.patient_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

    elif current_user.role not in (
        "ADMIN",
        "RECEPTIONIST",
        "DOCTOR"
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    if (
        current_user.role == "DOCTOR"
        and current_user.doctor_id != appointment.doctor_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return appointment