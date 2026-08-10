from pydantic import BaseModel


class DailyQueueResponse(BaseModel):
    id: int
    doctor_id: int
    queue_date: str
    capacity: int
    current_number: int
    status: str

    class Config:
        from_attributes = True