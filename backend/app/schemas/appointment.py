from pydantic import BaseModel


class AppointmentBookRequest(BaseModel):

    doctor_id: int
    queue_date: str


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: str
    queue_number: int
    status: str
    appointment_time: str | None

    class Config:
        from_attributes = True