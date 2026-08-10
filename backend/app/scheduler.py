from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

from app.database.database import SessionLocal
from app.services.daily_queue_service import (
    create_tomorrow_queues,
    open_tomorrow_queues
)


scheduler = BackgroundScheduler(
    timezone=ZoneInfo("Asia/Tehran")
)


def prepare_and_open_tomorrow_queues():

    db = SessionLocal()

    try:
        # ایجاد صف‌های فردا
        create_tomorrow_queues(db)

        # باز کردن صف‌های فردا
        open_tomorrow_queues(db)

    finally:
        db.close()


scheduler.add_job(
    prepare_and_open_tomorrow_queues,
    trigger="cron",
    hour=19,
    minute=0,
    id="open_daily_queues",
    replace_existing=True
)


def start_scheduler():
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown()