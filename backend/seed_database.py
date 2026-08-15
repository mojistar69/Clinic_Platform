import json

from app.database.database import SessionLocal
from app.models.models import Doctor, DoctorSchedule


def seed_doctors():

    db = SessionLocal()

    try:

        with open(
            "seed_data/doctors.json",
            "r",
            encoding="utf-8"
        ) as file:

            doctors_data = json.load(file)

        for item in doctors_data:

            doctor = Doctor(
                name=item["name"],
                specialty=item["specialty"],
                room_number=item.get("room_number"),
                clinic_id=item["clinic_id"]
            )

            db.add(doctor)
            db.flush()

            for schedule_data in item.get("schedules", []):

                schedule = DoctorSchedule(
                    doctor_id=doctor.id,
                    weekday=schedule_data["weekday"],
                    start_time=schedule_data["start_time"],
                    end_time=schedule_data["end_time"],
                    slot_duration=schedule_data.get(
                        "slot_duration",
                        15
                    ),
                    capacity=schedule_data.get(
                        "capacity",
                        20
                    ),
                    is_active=True
                )

                db.add(schedule)

        db.commit()

        print("Doctors and schedules inserted successfully.")

    except Exception as e:

        db.rollback()

        print("Error:")
        print(e)

    finally:
        db.close()


if __name__ == "__main__":
    seed_doctors()