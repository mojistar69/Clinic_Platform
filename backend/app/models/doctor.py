from sqlalchemy import Column, Integer, String

from app.database.database import Base


class Doctor(Base):

    __tablename__ = "doctors"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    specialty = Column(
        String,
        nullable=False
    )

    room_number = Column(
        String,
        nullable=True
    )

    clinic_id = Column(
        Integer,
        nullable=False
    )