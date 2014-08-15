from datetime import datetime
from application import app

#Change %e to %d if running on Windows
def format_date(value, format=app.config['FP_DATE_FORMAT']):
    return value.strftime(format)

def format_month(value, format='%b'):
    return value.strftime(format)

def format_day(value, format='%e'):
    return value.strftime(format)
    
def time_since(value):
    now = datetime.utcnow()
    diff = now - value
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )
    for period, singular, plural in periods:
        if period:
            return "%d %s" % (period, singular if period == 1 else plural)
    return "a few seconds"

