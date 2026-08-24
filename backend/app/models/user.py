from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database.database import Base
from app.models.models import Doctor, Patient
from enum import Enum


class UserRole(str, Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    RECEPTIONIST = "RECEPTIONIST"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    mobile = Column(
        String,
        unique=True,
        nullable=False
    )

    password_hash = Column(
        String,
        nullable=False
    )

    full_name = Column(
        String,
        nullable=False
    )

    role = Column(
        String(20),
        nullable=False,
        default=UserRole.PATIENT.value
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    doctor = relationship("Doctor")

    patient = relationship("Patient")