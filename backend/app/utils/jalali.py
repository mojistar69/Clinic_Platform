import jdatetime
from datetime import datetime


def today_jalali() -> str:
    """
    تاریخ امروز به فرمت شمسی YYYY-MM-DD
    """
    return jdatetime.date.today().strftime("%Y-%m-%d")


def now_jalali():
    """
    تاریخ و زمان فعلی شمسی
    """
    return jdatetime.datetime.now()


def gregorian_to_jalali(dt: datetime) -> str:
    """
    تبدیل تاریخ میلادی به شمسی
    """
    return jdatetime.datetime.fromgregorian(
        datetime=dt
    ).strftime("%Y-%m-%d")


def jalali_to_gregorian(
    year: int,
    month: int,
    day: int
) -> datetime:
    """
    تبدیل تاریخ شمسی به میلادی
    """

    return jdatetime.datetime(
        year,
        month,
        day
    ).togregorian()