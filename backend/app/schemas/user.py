from pydantic import BaseModel



class UserCreate(BaseModel):
    mobile: str
    full_name: str
    password: str

    # اطلاعات پرونده بیمار
    first_name: str
    last_name: str
    national_code: str | None = None
    birth_date: str | None = None



class UserLogin(BaseModel):
    mobile: str
    password: str


class UserResponse(BaseModel):
    id: int
    mobile: str
    full_name: str
    role: str
    doctor_id: int | None = None
    patient_id: int | None = None
    is_active: bool


    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    
