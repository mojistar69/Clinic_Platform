from sqlalchemy.orm import Session

from app.models.models import (
    Appointment,
    DailyDoctorQueue,
    DoctorSchedule
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

    waiting_count = len(waiting_appointments)

    next_queue_number = (
        waiting_appointments[0].queue_number
        if waiting_appointments
        else None
    )

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


def get_patient_queue_snapshot(
    db: Session,
    appointment: Appointment
):
    """
    اطلاعات اختصاصی یک بیمار را از وضعیت فعلی صف می‌سازد.
    """

    queue = (
        db.query(DailyDoctorQueue)
        .filter(
            DailyDoctorQueue.doctor_id == appointment.doctor_id,
            DailyDoctorQueue.queue_date == appointment.appointment_date
        )
        .first()
    )

    if not queue:
        return None

    current_visit = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.appointment_date == appointment.appointment_date,
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

    last_done = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.appointment_date == appointment.appointment_date,
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

    people_ahead = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.appointment_date == appointment.appointment_date,
            Appointment.queue_number < appointment.queue_number,
            Appointment.status.in_([
                "WAITING",
                "CONFIRMED",
                "CALLED",
                "IN_VISIT"
            ])
        )
        .count()
    )

    schedule = None

    try:
        import jdatetime

        appointment_date = jdatetime.datetime.strptime(
            appointment.appointment_date,
            "%Y-%m-%d"
        ).date()

        schedule = (
            db.query(DoctorSchedule)
            .filter(
                DoctorSchedule.doctor_id == appointment.doctor_id,
                DoctorSchedule.weekday == appointment_date.weekday(),
                DoctorSchedule.is_active == True
            )
            .first()
        )

    except (ValueError, TypeError):
        schedule = None

    slot_duration = (
        schedule.slot_duration
        if schedule and schedule.slot_duration
        else 15
    )

    estimated_wait_minutes = (
        people_ahead * slot_duration
    )

    if appointment.status == "IN_VISIT":
        patient_queue_status = "IN_VISIT"

    elif appointment.status == "CALLED":
        patient_queue_status = "CALLED"

    elif appointment.status == "DONE":
        patient_queue_status = "DONE"

    elif appointment.status in (
        "CANCELLED",
        "NO_SHOW"
    ):
        patient_queue_status = appointment.status

    elif people_ahead == 0:
        patient_queue_status = "READY"

    elif people_ahead <= 2:
        patient_queue_status = "NEAR"

    else:
        patient_queue_status = "WAITING"

    return {
        "type": "MY_QUEUE_UPDATED",
        "appointment_id": appointment.id,
        "doctor_id": appointment.doctor_id,
        "queue_date": appointment.appointment_date,
        "queue_number": appointment.queue_number,
        "appointment_time": appointment.appointment_time,
        "status": appointment.status,
        "patient_queue_status": patient_queue_status,
        "queue_status": queue.status,
        "capacity": queue.capacity,
        "current_serving_number": current_serving_number,
        "last_served_number": last_served_number,
        "people_ahead": people_ahead,
        "estimated_wait_minutes": estimated_wait_minutes
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

    print(
        "BROADCAST SNAPSHOT:",
        doctor_id,
        queue_date
    )

    await manager.broadcast_queue(
        doctor_id,
        queue_date,
        snapshot
    )


async def broadcast_patient_queue_updates(
    db: Session,
    doctor_id: int,
    queue_date: str
):
    """
    برای تمام Appointmentهای فعال این صف،
    وضعیت اختصاصی بیمار را ارسال می‌کند.
    """

    appointments = (
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
        .order_by(
            Appointment.queue_number.asc()
        )
        .all()
    )

    print(
        "PATIENT QUEUE BROADCAST:",
        doctor_id,
        queue_date,
        "patients=",
        len(appointments)
    )

    for appointment in appointments:

        snapshot = get_patient_queue_snapshot(
            db,
            appointment
        )

        if snapshot is None:
            continue

        await manager.broadcast_patient(
            appointment_id=appointment.id,
            message=snapshot
        )