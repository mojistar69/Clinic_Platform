from getpass import getpass

from app.database.database import SessionLocal
from app.models.user import User
from app.models.models import Doctor
from app.auth.security import hash_password


def main():
    db = SessionLocal()

    try:
        doctor_id = int(input("Doctor ID: ").strip())
        mobile = input("Mobile: ").strip()
        full_name = input("Full name: ").strip()

        password = getpass("Password: ")
        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            print("Error: Passwords do not match.")
            return

        doctor = (
            db.query(Doctor)
            .filter(Doctor.id == doctor_id)
            .first()
        )

        if not doctor:
            print("Error: Doctor not found.")
            return

        existing_user = (
            db.query(User)
            .filter(User.mobile == mobile)
            .first()
        )

        if existing_user:
            print("Error: This mobile is already registered.")
            return

        user = User(
            mobile=mobile,
            full_name=full_name,
            password_hash=hash_password(password),
            role="DOCTOR",
            doctor_id=doctor.id,
            patient_id=None,
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print("Doctor account created successfully.")
        print(f"User ID: {user.id}")
        print(f"Doctor ID: {user.doctor_id}")
        print(f"Role: {user.role}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    main()