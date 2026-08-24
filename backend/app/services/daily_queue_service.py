import jdatetime
from sqlalchemy.orm import Session

from app.models.models import DoctorSchedule, DailyDoctorQueue
from app.services.jalali import tomorrow_jalali


def create_queues_for_date(
    db: Session,
    queue_date: str
):
    """
    Create daily queues for all active doctor schedules
    matching the weekday of the given Jalali date.
    """

    try:
        target_date = jdatetime.datetime.strptime(
            queue_date,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        raise ValueError(
            "Invalid Jalali date format. Expected YYYY-MM-DD."
        )

    target_weekday = target_date.weekday()

    schedules = (
        db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.weekday == target_weekday,
            DoctorSchedule.is_active == True
        )
        .all()
    )

    created_queues = []

    for schedule in schedules:

        existing = (
            db.query(DailyDoctorQueue)
            .filter(
                DailyDoctorQueue.doctor_id == schedule.doctor_id,
                DailyDoctorQueue.queue_date == queue_date
            )
            .first()
        )

        if existing:
            continue

        queue = DailyDoctorQueue(
            doctor_id=schedule.doctor_id,
            queue_date=queue_date,
            capacity=schedule.capacity,
            current_number=0,
            status="CLOSED"
        )

        db.add(queue)
        created_queues.append(queue)

    db.commit()

    for queue in created_queues:
        db.refresh(queue)

    return created_queues


def create_tomorrow_queues(db: Session):
    """
    Backward-compatible wrapper for the scheduler.
    """
    tomorrow = tomorrow_jalali()
    return create_queues_for_date(db, tomorrow)


def open_queues_for_date(
    db: Session,
    queue_date: str
):
    """
    Open all CLOSED queues for a specific date.
    """

    queues = (
        db.query(DailyDoctorQueue)
        .filter(
            DailyDoctorQueue.queue_date == queue_date,
            DailyDoctorQueue.status == "CLOSED"
        )
        .all()
    )

    opened_queues = []

    for queue in queues:
        queue.status = "OPEN"
        opened_queues.append(queue)

    db.commit()

    for queue in opened_queues:
        db.refresh(queue)

    return opened_queues


def open_tomorrow_queues(db: Session):
    """
    Backward-compatible wrapper for the scheduler.
    """
    tomorrow = tomorrow_jalali()
    return open_queues_for_date(db, tomorrow)