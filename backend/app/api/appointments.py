from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
def book_appointment(
    request: AppointmentBookRequest,
    db: Session = Depends(get_db)
):

    # 1. بررسی بیمار
    patient = db.query(Patient).filter(
        Patient.id == request.patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # 2. بررسی پزشک
    doctor = db.query(Doctor).filter(
        Doctor.id == request.doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # 3. پیدا کردن صف روزانه
    queue = db.query(DailyDoctorQueue).filter(
        DailyDoctorQueue.doctor_id == request.doctor_id,
        DailyDoctorQueue.queue_date == request.queue_date
    ).first()

    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Daily queue not found"
        )

    # 4. بررسی وضعیت صف
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

    # 5. جلوگیری از نوبت تکراری
    existing = db.query(Appointment).filter(
        Appointment.patient_id == request.patient_id,
        Appointment.doctor_id == request.doctor_id,
        Appointment.appointment_date == request.queue_date
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Patient already has an appointment for this doctor on this date"
        )

    # 6. بررسی ظرفیت
    if queue.current_number >= queue.capacity:
        queue.status = "FULL"
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Appointment capacity is full"
        )

    # 7. شماره بعدی
    next_number = queue.current_number + 1

    #7.5
    # پیدا کردن روز هفته تاریخ نوبت
    appointment_date = jdatetime.datetime.strptime(
    request.queue_date,
    "%Y-%m-%d"
    ).date()

    weekday = appointment_date.weekday()

    # پیدا کردن برنامه پزشک در آن روز
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

    # محاسبه ساعت مراجعه
    appointment_time = calculate_appointment_time(
    schedule.start_time,
    next_number,
    schedule.slot_duration
)

    # 8. افزایش شمارنده
    queue.current_number = next_number

    # 9. اگر آخرین نفر بود، صف را ببند
    if next_number >= queue.capacity:
        queue.status = "FULL"





    # 10. ایجاد نوبت
    appointment = Appointment(
    patient_id=request.patient_id,
    doctor_id=request.doctor_id,
    appointment_date=request.queue_date,
    queue_number=next_number,
    status="WAITING",
    appointment_time=appointment_time
    )

    db.add(appointment)

    # 11. ذخیره
    db.commit()
    db.refresh(appointment)
    return appointment