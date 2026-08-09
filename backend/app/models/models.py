from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
    
from sqlalchemy import DateTime
from datetime import datetime

from app.database.database import Base


class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    doctors = relationship(
        "Doctor",
        back_populates="clinic"
    )


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    room_number = Column(String, nullable=True)

    clinic_id = Column(
        Integer,
        ForeignKey("clinics.id")
    )

    clinic = relationship(
        "Clinic",
        back_populates="doctors"
    )
    
class Patient(Base):
    __tablename__ = "patients"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    first_name = Column(
        String,
        nullable=False
    )

    last_name = Column(
        String,
        nullable=False
    )

    mobile = Column(
        String,
        nullable=False
    )

    national_code = Column(
        String,
        nullable=True
    )

    birth_date = Column(
        String,
        nullable=True
    )
    


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id")
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id")
    )

    queue_number = Column(
        Integer,
        nullable=False
    )

    status = Column(
        String,
        default="WAITING"
    )

    appointment_time = Column(
        DateTime,
        default=datetime.utcnow
    )


    patient = relationship(
        "Patient"
    )


    doctor = relationship(
        "Doctor"
    )
    
class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True
    )

    weekday = Column(
        Integer,
        nullable=False
    )

    start_time = Column(
        String,
        nullable=False
    )

    end_time = Column(
        String,
        nullable=False
    )

    slot_duration = Column(
        Integer,
        nullable=False,
        default=15
    )

    capacity = Column(
        Integer,
        nullable=False,
        default=20
    )

    is_active = Column(
        Boolean,
        default=True
    )

    doctor = relationship(
        "Doctor"
    )
    
    
    
    
    
    
class DailyDoctorQueue(Base):
    __tablename__ = "daily_doctor_queues"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True
    )

    queue_date = Column(
        String,
        nullable=False,
        index=True
    )

    capacity = Column(
        Integer,
        nullable=False,
        default=20
    )

    current_number = Column(
        Integer,
        nullable=False,
        default=0
    )

    status = Column(
        String,
        nullable=False,
        default="CLOSED"
    )

    doctor = relationship(
        "Doctor"
    )