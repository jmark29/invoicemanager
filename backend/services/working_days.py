"""Working days calculation for Hessen, Germany.

Implements Easter calculation (Anonymous Gregorian algorithm), Hessen public
holidays, working day counts, and proportional cost distribution across months.

Reference: docs/reference-docs/invoice_data/generate_invoice.py:469-550
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal


def easter_date(year: int) -> date:
    """Calculate Easter Sunday for a given year using the Anonymous Gregorian algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def hessen_holidays(year: int) -> set[date]:
    """Return the set of public holidays for Hessen, Germany in the given year.

    Includes 10 holidays: 6 fixed-date + 4 Easter-dependent (including Fronleichnam).
    """
    easter = easter_date(year)
    return {
        date(year, 1, 1),                    # Neujahr
        easter - timedelta(days=2),           # Karfreitag
        easter + timedelta(days=1),           # Ostermontag
        date(year, 5, 1),                     # Tag der Arbeit
        easter + timedelta(days=39),          # Christi Himmelfahrt
        easter + timedelta(days=50),          # Pfingstmontag
        easter + timedelta(days=60),          # Fronleichnam (Hessen-specific)
        date(year, 10, 3),                    # Tag der Deutschen Einheit
        date(year, 12, 25),                   # 1. Weihnachtstag
        date(year, 12, 26),                   # 2. Weihnachtstag
    }


def working_days_in_month(year: int, month: int) -> int:
    """Count working days (Mon-Fri, excluding Hessen holidays) in the given month."""
    holidays = hessen_holidays(year)
    last_day = monthrange(year, month)[1]
    count = 0
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        if d.weekday() < 5 and d not in holidays:
            count += 1
    return count


def distribute_cost_by_working_days(
    total_amount: float, months: list[tuple[int, int]]
) -> dict[tuple[int, int], float]:
    """Distribute a total amount across months proportional to working days.

    Uses Decimal arithmetic with ROUND_HALF_UP. The last month receives the
    remainder to ensure the distribution sums exactly to total_amount.

    Args:
        total_amount: The total EUR amount to distribute.
        months: List of (year, month) tuples defining the distribution period.

    Returns:
        Dict mapping each (year, month) to its allocated amount.

    Raises:
        ValueError: If there are no working days in the given months.
    """
    if not months:
        raise ValueError("No months provided for distribution")

    wd = {ym: working_days_in_month(ym[0], ym[1]) for ym in months}
    total_days = sum(wd.values())

    if total_days == 0:
        raise ValueError("No working days in the given months")

    total_dec = Decimal(str(total_amount))
    distribution: dict[tuple[int, int], float] = {}
    remaining = total_dec

    for i, ym in enumerate(months):
        if i == len(months) - 1:
            # Last month gets the remainder to avoid rounding drift
            distribution[ym] = float(remaining)
        else:
            share = (total_dec * Decimal(str(wd[ym])) / Decimal(str(total_days))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            distribution[ym] = float(share)
            remaining -= share

    return distribution
