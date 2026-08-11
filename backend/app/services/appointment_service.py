from datetime import datetime, timedelta


def calculate_appointment_time(
    start_time: str,
    queue_number: int,
    slot_duration: int
) -> str:

    start = datetime.strptime(
        start_time,
        "%H:%M"
    )

    appointment_time = start + timedelta(
        minutes=(queue_number - 1) * slot_duration
    )

    return appointment_time.strftime("%H:%M")