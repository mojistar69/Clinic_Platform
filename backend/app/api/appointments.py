from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import jdatetime

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.models.models import (
    Appointment,
    Patient,
    Doctor,
    DoctorSchedule,
    DailyDoctorQueue
)
from app.schemas.appointment import (
    AppointmentBookRequest,
    AppointmentResponse
)
from app.services.appointment_service import calculate_appointment_time


router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)


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
    current_user: User = Depends(get_current_user)
):

    # 1. فقط بیمار می‌تواند نوبت بگیرد
    if current_user.role != "PATIENT":
        raise HTTPException(
            status_code=403,
            detail="Only patients can book appointments"
        )

    # 2. بررسی اتصال User به Patient
    if not current_user.patient_id:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    # 3. پیدا کردن بیمار از روی JWT
    patient = (
        db.query(Patient)
        .filter(Patient.id == current_user.patient_id)
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # 4. بررسی پزشک
    doctor = (
        db.query(Doctor)
        .filter(Doctor.id == request.doctor_id)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # 5. پیدا کردن صف روزانه
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

    # 6. بررسی وضعیت صف
    if queue.status != "OPEN":
        if queue.status == "FULL":
            raise HTTPException(
                status_code=400,
                detail="Appointment capacity is full"
            )

        raise HTTPException(
            status_code=400,
            detail="Appointment booking is not open"
        )

    # 7. جلوگیری از نوبت تکراری
    existing = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient.id,
            Appointment.doctor_id == request.doctor_id,
            Appointment.appointment_date == request.queue_date,
            Appointment.status != "CANCELLED"
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Patient already has an appointment for this doctor on this date"
        )

    # 8. بررسی ظرفیت
    if queue.current_number >= queue.capacity:
        queue.status = "FULL"
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Appointment capacity is full"
        )

    # 9. شماره بعدی صف
    next_number = queue.current_number + 1

    # 10. تبدیل تاریخ جلالی به تاریخ برای تعیین روز هفته
    try:
        appointment_date = jdatetime.datetime.strptime(
            request.queue_date,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    weekday = appointment_date.weekday()

    # 11. پیدا کردن برنامه پزشک
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

    # 12. محاسبه ساعت مراجعه
    appointment_time = calculate_appointment_time(
        schedule.start_time,
        next_number,
        schedule.slot_duration
    )

    # 13. افزایش شماره فعلی صف
    queue.current_number = next_number

    # 14. اگر ظرفیت پر شد، صف را ببند
    if next_number >= queue.capacity:
        queue.status = "FULL"

    # 15. ایجاد نوبت
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=request.doctor_id,
        appointment_date=request.queue_date,
        queue_number=next_number,
        status="WAITING",
        appointment_time=appointment_time
    )

    db.add(appointment)

    # 16. ذخیره
    db.commit()
    db.refresh(appointment)

    return appointment


# =========================================================
# Cancel Appointment
# =========================================================

@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse
)
def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # بررسی اتصال کاربر به بیمار
    if not current_user.patient_id:
        raise HTTPException(
            status_code=403,
            detail="User is not linked to a patient"
        )

    # فقط نوبت متعلق به همین بیمار پیدا شود
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

    # نوبت قبلاً لغو شده
    if appointment.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Appointment is already cancelled"
        )

    # نوبت تکمیل شده
    if appointment.status == "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Completed appointment cannot be cancelled"
        )

    # لغو نوبت
    appointment.status = "CANCELLED"

    # پیدا کردن صف
    queue = (
        db.query(DailyDoctorQueue)
        .filter(
            DailyDoctorQueue.doctor_id == appointment.doctor_id,
            DailyDoctorQueue.queue_date == appointment.appointment_date
        )
        .first()
    )

    # اگر صف FULL بوده، دوباره OPEN شود
    if queue and queue.status == "FULL":
        queue.status = "OPEN"

    db.commit()
    db.refresh(appointment)

    return appointment


# =========================================================
# My Recent Appointments
# =========================================================

@router.get(
    "/my/recent",
    response_model=list[AppointmentResponse]
)
def get_my_recent_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if not current_user.patient_id:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == current_user.patient_id,
            Appointment.appointment_date <= today
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.id.desc()
        )
        .limit(5)
        .all()
    )

    return appointments


# =========================================================
# My Upcoming Appointments
# =========================================================

@router.get(
    "/my/upcoming",
    response_model=list[AppointmentResponse]
)
def get_my_upcoming_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if not current_user.patient_id:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == current_user.patient_id,
            Appointment.appointment_date >= today,
            Appointment.status.in_([
                "WAITING",
                "CONFIRMED"
            ])
        )
        .order_by(
            Appointment.appointment_date.asc(),
            Appointment.id.asc()
        )
        .all()
    )

    return appointments


# =========================================================
# My Appointment History
# =========================================================

@router.get(
    "/my/history",
    response_model=list[AppointmentResponse]
)
def get_my_appointment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if not current_user.patient_id:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == current_user.patient_id,
            Appointment.appointment_date < today
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.id.desc()
        )
        .all()
    )

    return appointments