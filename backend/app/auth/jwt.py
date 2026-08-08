from datetime import datetime, timedelta, timezone

from jose import jwt


SECRET_KEY = "CHANGE_THIS_SECRET_KEY"
ALGORITHM = "HS256"


def create_access_token(
    data: dict,
    minutes: int = 60
):
    payload = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=minutes
    )

    payload["exp"] = expire

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )