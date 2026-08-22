from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import jdatetime

from app.database.database import get_db
from app.models.models import (
    Doctor,
    DoctorSchedule,
    DailyDoctorQueue
)

router = APIRouter(
    prefix="/doctors",
    tags=["Doctor Calendar"]
)


@router.get("/{doctor_id}/calendar")
def get_doctor_calendar(
    doctor_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------
    # 1. بررسی پزشک
    # --------------------------------------------------

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

    # --------------------------------------------------
    # 2. بررسی ماه
    # --------------------------------------------------

    if month < 1 or month > 12:
        raise HTTPException(
            status_code=400,
            detail="Invalid month"
        )

    if year < 1300 or year > 1500:
        raise HTTPException(
            status_code=400,
            detail="Invalid year"
        )

    # --------------------------------------------------
    # 3. تعداد روزهای ماه شمسی
    # --------------------------------------------------

    if month <= 6:
        days_in_month = 31

    elif month <= 11:
        days_in_month = 30

    else:
        days_in_month = (
            30
            if jdatetime.j_isleap(year)
            else 29
        )

    days = []

    # --------------------------------------------------
    # 4. ایجاد تقویم
    # --------------------------------------------------

    for day in range(1, days_in_month + 1):

        date_str = (
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

        current_date = jdatetime.date(
            year,
            month,
            day
        )

        weekday = current_date.weekday()

        # --------------------------------------------------
        # 5. پیدا کردن برنامه پزشک در این روز
        # --------------------------------------------------

        schedule = (
            db.query(DoctorSchedule)
            .filter(
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.weekday == weekday,
                DoctorSchedule.is_active == True
            )
            .first()
        )

        # --------------------------------------------------
        # 6. روز تعطیل / بدون برنامه
        # --------------------------------------------------

        if not schedule:

            days.append({
                "date": date_str,
                "weekday": weekday,
                "is_working_day": False,
                "status": "CLOSED",
                "capacity": 0,
                "booked": 0,
                "remaining": 0
            })

            continue

        # --------------------------------------------------
        # 7. پیدا کردن صف روزانه
        # --------------------------------------------------

        queue = (
            db.query(DailyDoctorQueue)
            .filter(
                DailyDoctorQueue.doctor_id == doctor_id,
                DailyDoctorQueue.queue_date == date_str
            )
            .first()
        )

        # --------------------------------------------------
        # 8. اگر صف وجود ندارد، ایجاد شود
        # --------------------------------------------------

        if not queue:

            queue = DailyDoctorQueue(
                doctor_id=doctor_id,
                queue_date=date_str,
                capacity=schedule.capacity,
                current_number=0,
                status="OPEN"
            )

            db.add(queue)

            try:
                db.commit()
                db.refresh(queue)

            except IntegrityError:

                # اگر همزمان درخواست دیگری صف را ساخته باشد
                db.rollback()

                queue = (
                    db.query(DailyDoctorQueue)
                    .filter(
                        DailyDoctorQueue.doctor_id == doctor_id,
                        DailyDoctorQueue.queue_date == date_str
                    )
                    .first()
                )

                if not queue:
                    raise HTTPException(
                        status_code=500,
                        detail="Unable to create daily queue"
                    )

        # --------------------------------------------------
        # 9. محاسبه ظرفیت
        # --------------------------------------------------

        booked = queue.current_number

        remaining = max(
            queue.capacity - booked,
            0
        )

        # --------------------------------------------------
        # 10. بررسی وضعیت واقعی صف
        # --------------------------------------------------

        if booked >= queue.capacity:

            if queue.status != "FULL":
                queue.status = "FULL"

                db.commit()

            status = "FULL"

            remaining = 0

        else:

            # اگر صف ظرفیت دارد ولی به هر دلیل CLOSED بوده
            # آن را OPEN می‌کنیم.
            if queue.status == "CLOSED":

                queue.status = "OPEN"

                db.commit()

            status = queue.status

        # --------------------------------------------------
        # 11. اضافه کردن روز به خروجی
        # --------------------------------------------------

        days.append({
            "date": date_str,
            "weekday": weekday,
            "is_working_day": True,
            "status": status,
            "capacity": queue.capacity,
            "booked": booked,
            "remaining": remaining,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "slot_duration": schedule.slot_duration
        })

    # --------------------------------------------------
    # 12. پاسخ نهایی
    # --------------------------------------------------

    return {
        "doctor_id": doctor.id,
        "doctor_name": doctor.name,
        "specialty": doctor.specialty,
        "year": year,
        "month": month,
        "days": days
    }