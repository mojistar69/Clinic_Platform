from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import DailyDoctorQueue, Doctor
from app.schemas.daily_queue import DailyQueueResponse
from app.services.daily_queue_service import (
    create_tomorrow_queues,
    open_tomorrow_queues,
    create_queues_for_date,
    open_queues_for_date
)


router = APIRouter(
    prefix="/daily-queues",
    tags=["Daily Doctor Queue"]
)
@router.post("/test-open-tomorrow")
def test_open_tomorrow(
    db: Session = Depends(get_db)
):

    created = create_tomorrow_queues(db)

    opened = open_tomorrow_queues(db)

    return {
        "message": "Test scheduler executed successfully",
        "created": len(created),
        "opened": len(opened)
    }

@router.post(
    "/{doctor_id}/{queue_date}",
    response_model=DailyQueueResponse
)
def create_daily_queue(
    doctor_id: int,
    queue_date: str,
    db: Session = Depends(get_db)
):

    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    existing = db.query(DailyDoctorQueue).filter(
        DailyDoctorQueue.doctor_id == doctor_id,
        DailyDoctorQueue.queue_date == queue_date
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Queue already exists for this doctor and date"
        )

    queue = DailyDoctorQueue(
        doctor_id=doctor_id,
        queue_date=queue_date,
        capacity=20,
        current_number=0,
        status="CLOSED"
    )

    db.add(queue)
    db.commit()
    db.refresh(queue)

    return queue
    
    
@router.patch(
    "/{doctor_id}/{queue_date}/open",
    response_model=DailyQueueResponse
)
def open_daily_queue(
    doctor_id: int,
    queue_date: str,
    db: Session = Depends(get_db)
):

    queue = db.query(DailyDoctorQueue).filter(
        DailyDoctorQueue.doctor_id == doctor_id,
        DailyDoctorQueue.queue_date == queue_date
    ).first()

    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Daily queue not found"
        )

    if queue.status == "FULL":
        raise HTTPException(
            status_code=400,
            detail="Queue is already full"
        )

    if queue.status == "OPEN":
        raise HTTPException(
            status_code=400,
            detail="Queue is already open"
        )

    queue.status = "OPEN"

    db.commit()
    db.refresh(queue)

    return queue
    
    
@router.post(
    "/prepare-tomorrow"
)
def prepare_tomorrow_queues(
    db: Session = Depends(get_db)
):

    queues = create_tomorrow_queues(db)

    return {
        "message": "Tomorrow queues prepared successfully",
        "count": len(queues)
    }
    
@router.post("/open-tomorrow")
def open_tomorrow(
    db: Session = Depends(get_db)
):

    queues = open_tomorrow_queues(db)

    return {
        "message": "Tomorrow queues opened successfully",
        "count": len(queues)
    }

@router.get("/{doctor_id}/{queue_date}", response_model=DailyQueueResponse)
def get_daily_queue(
    doctor_id: int,
    queue_date: str,
    db: Session = Depends(get_db)
):
    queue = db.query(DailyDoctorQueue).filter(
        DailyDoctorQueue.doctor_id == doctor_id,
        DailyDoctorQueue.queue_date == queue_date
    ).first()

    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Daily queue not found"
        )

    return queue