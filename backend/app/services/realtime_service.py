from sqlalchemy.orm import Session

from app.models.models import (
    Appointment,
    DailyDoctorQueue
)

from app.api.websocket import manager


def get_queue_snapshot(
    db: Session,
    doctor_id: int,
    queue_date: str
):
    queue = (
        db.query(DailyDoctorQueue)
        .filter(
            DailyDoctorQueue.doctor_id == doctor_id,
            DailyDoctorQueue.queue_date == queue_date
        )
        .first()
    )

    if not queue:
        return None

    # بیمار در حال ویزیت
    current_visit = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == queue_date,
            Appointment.status == "IN_VISIT"
        )
        .order_by(
            Appointment.queue_number.asc()
        )
        .first()
    )

    current_serving_number = (
        current_visit.queue_number
        if current_visit
        else None
    )

    # آخرین بیمار ویزیت‌شده
    last_done = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == queue_date,
            Appointment.status == "DONE"
        )
        .order_by(
            Appointment.queue_number.desc()
        )
        .first()
    )

    last_served_number = (
        last_done.queue_number
        if last_done
        else 0
    )

    # بیماران منتظر
    waiting_appointments = (
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
        .all()
    )

    waiting_count = len(
        waiting_appointments
    )

    next_queue_number = (
        waiting_appointments[0].queue_number
        if waiting_appointments
        else None
    )

    # تعداد کل نوبت‌های فعال
    active_count = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == queue_date,
            Appointment.status.in_([
                "WAITING",
                "CONFIRMED",
                "CALLED",
                "IN_VISIT"
            ])
        )
        .count()
    )

    return {
        "type": "QUEUE_UPDATED",
        "doctor_id": doctor_id,
        "queue_date": queue_date,
        "queue_status": queue.status,
        "capacity": queue.capacity,
        "current_number": queue.current_number,
        "current_serving_number": current_serving_number,
        "last_served_number": last_served_number,
        "waiting_count": waiting_count,
        "active_count": active_count,
        "next_queue_number": next_queue_number
    }


async def broadcast_queue_update(
    db: Session,
    doctor_id: int,
    queue_date: str
):
    snapshot = get_queue_snapshot(
        db,
        doctor_id,
        queue_date
    )

    if snapshot is None:
        return

    await manager.broadcast_queue(
        doctor_id,
        queue_date,
        snapshot
    )