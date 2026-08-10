import jdatetime
from sqlalchemy.orm import Session

from app.models.models import DoctorSchedule, DailyDoctorQueue
from app.services.jalali import tomorrow_jalali


def create_tomorrow_queues(db: Session):

    tomorrow = tomorrow_jalali()

    tomorrow_date = jdatetime.datetime.strptime(
        tomorrow,
        "%Y-%m-%d"
    ).date()

    tomorrow_weekday = tomorrow_date.weekday()

    schedules = db.query(DoctorSchedule).filter(
        DoctorSchedule.weekday == tomorrow_weekday,
        DoctorSchedule.is_active == True
    ).all()

    created_queues = []

    for schedule in schedules:

        existing = db.query(DailyDoctorQueue).filter(
            DailyDoctorQueue.doctor_id == schedule.doctor_id,
            DailyDoctorQueue.queue_date == tomorrow
        ).first()

        if existing:
            continue

        queue = DailyDoctorQueue(
            doctor_id=schedule.doctor_id,
            queue_date=tomorrow,
            capacity=schedule.capacity,
            current_number=0,
            status="CLOSED"
        )

        db.add(queue)
        created_queues.append(queue)

    db.commit()

    return created_queues


def open_tomorrow_queues(db: Session):

    tomorrow = tomorrow_jalali()

    queues = db.query(DailyDoctorQueue).filter(
        DailyDoctorQueue.queue_date == tomorrow,
        DailyDoctorQueue.status == "CLOSED"
    ).all()

    opened_queues = []

    for queue in queues:
        queue.status = "OPEN"
        opened_queues.append(queue)

    db.commit()

    return opened_queues