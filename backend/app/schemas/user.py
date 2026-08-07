from pydantic import BaseModel


class UserCreate(BaseModel):

    mobile: str
    password: str
    full_name: str



class UserLogin(BaseModel):

    mobile: str
    password: str



class UserResponse(BaseModel):

    id: int
    mobile: str
    full_name: str
    role: str

    class Config:
        from_attributes = True