"""
Helper functions
"""

from datetime import datetime, timedelta


def format_currency(amount):
    """Format so tien thanh chuoi VND"""
    if amount is None:
        return "0"
    return "{:,.0f}".format(amount)


def format_hours(hours):
    """Format so gio lam viec"""
    if hours is None:
        return "0h"
    return f"{hours:.1f}h"


def get_week_dates(date=None):
    """Lay ngay dau va cuoi tuan"""
    if date is None:
        date = datetime.now().date()

    week_start = date - timedelta(days=date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def get_next_week_dates():
    """Lay ngay dau va cuoi tuan sau"""
    today = datetime.now().date()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    next_sunday = next_monday + timedelta(days=6)
    return next_monday, next_sunday


def get_month_dates(month=None, year=None):
    """Lay ngay dau va cuoi thang"""
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year

    from datetime import date
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    return month_start, month_end


def get_day_name(date):
    """Lay ten thu trong tuan"""
    day_names = ['Thu 2', 'Thu 3', 'Thu 4', 'Thu 5', 'Thu 6', 'Thu 7', 'Chu Nhat']
    return day_names[date.weekday()]


def get_shift_name(shift_type):
    """Lay ten ca lam viec"""
    shift_names = {
        'morning': 'Ca Sang (7h-12h)',
        'afternoon': 'Ca Chieu (12h-18h)',
        'evening': 'Ca Toi (18h-22h)'
    }
    return shift_names.get(shift_type, shift_type)
