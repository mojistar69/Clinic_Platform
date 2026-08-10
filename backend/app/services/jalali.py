import jdatetime


def today_jalali() -> str:
    today = jdatetime.date.today()

    return today.strftime("%Y-%m-%d")


def tomorrow_jalali() -> str:
    tomorrow = jdatetime.date.today() + jdatetime.timedelta(days=1)

    return tomorrow.strftime("%Y-%m-%d")


def weekday_jalali() -> int:
    today = jdatetime.date.today()

    return today.weekday()