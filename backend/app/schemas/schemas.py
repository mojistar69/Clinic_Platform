from pydantic import BaseModel


# Clinic

class ClinicCreate(BaseModel):
    name: str
    address: str | None = None
    phone: str | None = None


class ClinicResponse(BaseModel):
    id: int
    name: str
    address: str | None
    phone: str | None
    is_active: bool

    class Config:
        from_attributes = True



# Doctor

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
        
        
class PatientCreate(BaseModel):

    first_name: str
    last_name: str
    mobile: str
    national_code: str | None = None
    birth_date: str | None = None



class PatientResponse(BaseModel):

    id: int
    first_name: str
    last_name: str
    mobile: str
    national_code: str | None
    birth_date: str | None


    class Config:
        from_attributes = True


class AppointmentCreate(BaseModel):

    patient_id: int
    doctor_id: int



class AppointmentResponse(BaseModel):

    id: int
    patient_id: int
    doctor_id: int
    queue_number: int
    status: str


    class Config:
        from_attributes = True