from fastapi import FastAPI

from app.database.database import engine, Base

from app.api import auth
from app.api import doctors
from app.api import patients
from app.api import appointments
from app.api import doctor_schedules
from app.models import user



Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Clinic Platform API",
    version="1.0.0"
)


app.include_router(
    doctors.router
)

app.include_router(
    patients.router
)

app.include_router(
    appointments.router
)

app.include_router(
    auth.router
)

app.include_router(
    doctor_schedules.router
)


@app.get("/")
def root():
    return {
        "message": "Clinic Platform Running"
    }