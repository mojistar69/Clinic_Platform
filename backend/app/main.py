from fastapi import FastAPI
from app.api import patients
from app.api import appointments
from app.database.database import engine
from app.database.database import Base
from app.api import auth
from app.models import models

from app.api import doctors
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

@app.get("/")
def root():
    return {
        "message": "Clinic Platform Running"
    }