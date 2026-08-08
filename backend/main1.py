from app.database.database import SessionLocal
from app.models.user import User


db = SessionLocal()


user = db.query(User).filter(
    User.mobile == "09121234567"
).first()


user.role = "ADMIN"


db.commit()

print("User changed to ADMIN")