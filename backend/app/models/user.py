from sqlalchemy import Column, Integer, String, Boolean

from app.database.database import Base


class User(Base):

    __tablename__ = "users"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


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
        String,
        default="PATIENT"
    )


    is_active = Column(
        Boolean,
        default=True
    )