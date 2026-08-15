from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.database.database import get_db
from app.models.models import (
    Appointment,
    Patient,
    Doctor,
    DailyDoctorQueue
)
from app.schemas.appointment import (
    AppointmentBookRequest,
    AppointmentResponse
)
from app.models.models import (
    Appointment,
    Patient,
    Doctor,
    DoctorSchedule,
    DailyDoctorQueue
)
import jdatetime

from app.services.appointment_service import calculate_appointment_time

router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)
from app.models.models import (
    Appointment,
    Patient,
    Doctor,
    DailyDoctorQueue,
    DoctorSchedule
)

@router.post(
    "/book",
    response_model=AppointmentResponse
)
@router.post(
    "/book",
    response_model=AppointmentResponse
)
def book_appointment(
    request: AppointmentBookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # 1. بررسی اینکه کاربر بیمار باشد
    if current_user.role != "PATIENT":
        raise HTTPException(
            status_code=403,
            detail="Only patients can book appointments"
        )

    # 2. پیدا کردن بیمار از روی کاربر لاگین‌شده
    if not current_user.patient_id:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    patient = db.query(Patient).filter(
        Patient.id == current_user.patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # 3. بررسی پزشک
    doctor = db.query(Doctor).filter(
        Doctor.id == request.doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # 4. پیدا کردن صف روزانه
    queue = db.query(DailyDoctorQueue).filter(
        DailyDoctorQueue.doctor_id == request.doctor_id,
        DailyDoctorQueue.queue_date == request.queue_date
    ).first()

    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Daily queue not found"
        )

    # 5. بررسی وضعیت صف
    if queue.status == "FULL":
        raise HTTPException(
            status_code=400,
            detail="Appointment capacity is full"
        )

    if queue.status != "OPEN":
        raise HTTPException(
            status_code=400,
            detail="Appointment booking is not open"
        )

    # 6. جلوگیری از نوبت تکراری
    existing = db.query(Appointment).filter(
        Appointment.patient_id == patient.id,
        Appointment.doctor_id == request.doctor_id,
        Appointment.appointment_date == request.queue_date
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Patient already has an appointment for this doctor on this date"
        )

    # 7. بررسی ظرفیت
    if queue.current_number >= queue.capacity:
        queue.status = "FULL"
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Appointment capacity is full"
        )

    # 8. شماره بعدی
    next_number = queue.current_number + 1

    # 9. پیدا کردن روز هفته
    appointment_date = jdatetime.datetime.strptime(
        request.queue_date,
        "%Y-%m-%d"
    ).date()

    weekday = appointment_date.weekday()

    # 10. پیدا کردن برنامه پزشک
    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == request.doctor_id,
        DoctorSchedule.weekday == weekday,
        DoctorSchedule.is_active == True
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=400,
            detail="Doctor has no active schedule for this day"
        )

    # 11. محاسبه ساعت مراجعه
    appointment_time = calculate_appointment_time(
        schedule.start_time,
        next_number,
        schedule.slot_duration
    )

    # 12. افزایش شمارنده صف
    queue.current_number = next_number

    # 13. بستن صف در صورت تکمیل ظرفیت
    if next_number >= queue.capacity:
        queue.status = "FULL"

    # 14. ایجاد نوبت
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=request.doctor_id,
        appointment_date=request.queue_date,
        queue_number=next_number,
        status="WAITING",
        appointment_time=appointment_time
    )

    db.add(appointment)

    # 15. ذخیره
    db.commit()
    db.refresh(appointment)

    return appointment
    
@router.get(
    "/patient/{patient_id}/recent",
    response_model=list[AppointmentResponse]
)
def get_recent_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    appointments = (
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

    return appointments
    
    
@router.get(
    "/patient/{patient_id}/upcoming",
    response_model=list[AppointmentResponse]
)
def get_upcoming_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
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
    
@router.get(
    "/patient/{patient_id}/history",
    response_model=list[AppointmentResponse]
)
def get_patient_appointment_history(
    patient_id: int,
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date < today
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.id.desc()
        )
        .all()
    )

    return appointments