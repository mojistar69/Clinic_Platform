from pydantic import BaseModel


class DoctorCreate(BaseModel):

    name: str
    specialty: str
    room_number: str | None = None
    clinic_id: int
    
    
class DoctorResponse(BaseModel):

    id: int
    name: str
    specialty: str
    room_number: str | None
    clinic_id: int

    class Config:
        from_attributes = True