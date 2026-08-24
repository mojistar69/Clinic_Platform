from fastapi import FastAPI

from app.database.database import engine, Base

from app.api import auth
from app.api import doctors
from app.api import patients
from app.api import appointments
from app.api import doctor_schedules
from app.models import user
from app.api import daily_queue
from app.scheduler import start_scheduler, stop_scheduler
from app.api import doctor_panel
from app.api import doctor_calendar
from app.api import clinics
from app.api import reception
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Clinic Platform API",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    stop_scheduler()
    

app.include_router(
    doctors.router
)
app.include_router(
    clinics.router
)

app.include_router(
    patients.router
)

app.include_router(
    reception.router
)

app.include_router(
    appointments.router
)

app.include_router(
doctor_panel.router
)

app.include_router(
    auth.router
)

app.include_router(
    doctor_schedules.router
)

app.include_router(
    daily_queue.router
)

app.include_router(
    doctor_calendar.router
)

@app.get("/")
def root():
    return {
        "message": "Clinic Platform Running"
    }