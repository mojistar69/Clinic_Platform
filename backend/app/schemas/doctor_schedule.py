from pydantic import BaseModel


class DoctorScheduleCreate(BaseModel):
    doctor_id: int
    weekday: int
    start_time: str
    end_time: str
    slot_duration: int = 15
    capacity: int = 20
    is_active: bool = True


class DoctorScheduleResponse(BaseModel):
    id: int
    doctor_id: int
    weekday: int
    start_time: str
    end_time: str
    slot_duration: int
    capacity: int
    is_active: bool

    class Config:
        from_attributes = True