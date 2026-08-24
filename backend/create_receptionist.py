from getpass import getpass

from app.database.database import SessionLocal
from app.models.user import User
from app.auth.security import hash_password


def main():
    db = SessionLocal()

    try:
        print("=== Create Receptionist ===")

        mobile = input("Mobile: ").strip()
        full_name = input("Full name: ").strip()

        password = getpass("Password: ")
        confirm_password = getpass("Confirm password: ")

        if not mobile:
            print("Error: Mobile is required.")
            return

        if not full_name:
            print("Error: Full name is required.")
            return

        if not password:
            print("Error: Password is required.")
            return

        if password != confirm_password:
            print("Error: Passwords do not match.")
            return

        existing_user = (
            db.query(User)
            .filter(User.mobile == mobile)
            .first()
        )

        if existing_user:
            print("Error: This mobile is already registered.")
            return

        receptionist = User(
            mobile=mobile,
            full_name=full_name,
            password_hash=hash_password(password),
            role="RECEPTIONIST",
            doctor_id=None,
            patient_id=None,
            is_active=True
        )

        db.add(receptionist)
        db.commit()
        db.refresh(receptionist)

        print()
        print("Receptionist created successfully.")
        print(f"User ID: {receptionist.id}")
        print(f"Mobile: {receptionist.mobile}")
        print(f"Name: {receptionist.full_name}")
        print(f"Role: {receptionist.role}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    main()