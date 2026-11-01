"""
US equity market calendar helpers: Eastern "today" and NYSE trading days.
"""

from datetime import date, datetime, timedelta

import pytz

EASTERN = pytz.timezone('US/Eastern')


def eastern_today() -> date:
    """Today's date in New York, whatever the machine's timezone (GitHub runners are UTC)."""
    return datetime.now(EASTERN).date()


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The nth given weekday (0=Mon) of a month; n=-1 for the last one."""
    if n > 0:
        first = date(year, month, 1)
        return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    last = (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _easter(year: int) -> date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _observed(d: date) -> date:
    """Saturday holidays are observed the Friday before, Sunday ones the Monday after."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def nyse_holidays(year: int) -> set:
    """Regular NYSE full-day closures for a year (not one-off closures such as days of mourning)."""
    holidays = {
        _nth_weekday(year, 1, 0, 3),   # Martin Luther King Jr. Day
        _nth_weekday(year, 2, 0, 3),   # Washington's Birthday
        _easter(year) - timedelta(days=2),  # Good Friday
        _nth_weekday(year, 5, 0, -1),  # Memorial Day
        _observed(date(year, 7, 4)),   # Independence Day
        _nth_weekday(year, 9, 0, 1),   # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
        _observed(date(year, 12, 25)),  # Christmas
    }
    # New Year's Day on a Saturday is not observed on the Friday before
    new_year = date(year, 1, 1)
    if new_year.weekday() != 5:
        holidays.add(_observed(new_year))
    if year >= 2022:
        holidays.add(_observed(date(year, 6, 19)))  # Juneteenth
    return holidays


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in nyse_holidays(d.year)


def next_trading_day(d: date) -> date:
    """The first trading day after d."""
    d += timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d
