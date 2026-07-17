"""
NSE Trading Calendar.

Determines valid trading days by:
1. Checking against known NSE holidays (hardcoded from official circulars).
2. Checking against actual bhavcopy file existence (auto-derived from data).
3. Filtering weekends (Saturday/Sunday are never trading days).
"""

from datetime import date, timedelta
from pathlib import Path

# ── Known NSE Holidays ─────────────────────────────────────────────────────────
# We maintain a curated set. These are the CLOSED days (no trading).
# Source: NSE official circulars. We only need rough coverage — the bhavcopy
# downloader will naturally skip dates where no file exists, and the actual
# trading calendar is derived from successfully downloaded files.
#
# Format: set of date objects.

NSE_HOLIDAYS: set[date] = {
    # ── 2024 ──
    date(2024, 1, 26),   # Republic Day
    date(2024, 3, 8),    # Mahashivratri
    date(2024, 3, 25),   # Holi
    date(2024, 3, 29),   # Good Friday
    date(2024, 4, 11),   # Id-Ul-Fitr
    date(2024, 4, 17),   # Shri Ram Navmi
    date(2024, 5, 1),    # Maharashtra Day
    date(2024, 6, 17),   # Bakri Id
    date(2024, 7, 17),   # Moharram
    date(2024, 8, 15),   # Independence Day
    date(2024, 10, 2),   # Mahatma Gandhi Jayanti
    date(2024, 11, 1),   # Diwali Laxmi Pujan
    date(2024, 11, 15),  # Gurunanak Jayanti
    date(2024, 12, 25),  # Christmas

    # ── 2025 ──
    date(2025, 2, 26),   # Mahashivratri
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Id-Ul-Fitr
    date(2025, 4, 10),   # Shri Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Mahatma Gandhi Jayanti / Dussehra
    date(2025, 10, 21),  # Diwali Laxmi Pujan
    date(2025, 10, 22),  # Diwali-Balipratipada
    date(2025, 11, 5),   # Prakash Gurpurb Sri Guru Nanak Dev
    date(2025, 12, 25),  # Christmas

    # ── 2023 ──
    date(2023, 1, 26),   # Republic Day
    date(2023, 3, 7),    # Holi
    date(2023, 3, 30),   # Ram Navami
    date(2023, 4, 4),    # Mahavir Jayanti
    date(2023, 4, 7),    # Good Friday
    date(2023, 4, 14),   # Dr. Ambedkar Jayanti
    date(2023, 4, 22),   # Id-Ul-Fitr
    date(2023, 5, 1),    # Maharashtra Day
    date(2023, 6, 29),   # Bakri Id
    date(2023, 8, 15),   # Independence Day
    date(2023, 9, 19),   # Ganesh Chaturthi
    date(2023, 10, 2),   # Mahatma Gandhi Jayanti
    date(2023, 10, 24),  # Dussehra
    date(2023, 11, 14),  # Diwali-Balipratipada
    date(2023, 11, 27),  # Gurunanak Jayanti
    date(2023, 12, 25),  # Christmas

    # ── 2022 ──
    date(2022, 1, 26),   # Republic Day
    date(2022, 3, 1),    # Mahashivratri
    date(2022, 3, 18),   # Holi
    date(2022, 4, 14),   # Dr. Ambedkar Jayanti / Ram Navami
    date(2022, 4, 15),   # Good Friday
    date(2022, 5, 3),    # Id-Ul-Fitr
    date(2022, 8, 9),    # Moharram
    date(2022, 8, 15),   # Independence Day
    date(2022, 8, 31),   # Ganesh Chaturthi
    date(2022, 10, 5),   # Dussehra
    date(2022, 10, 24),  # Diwali-Laxmi Pujan
    date(2022, 10, 26),  # Diwali-Balipratipada
    date(2022, 11, 8),   # Gurunanak Jayanti

    # ── 2021 ──
    date(2021, 1, 26),   # Republic Day
    date(2021, 3, 11),   # Mahashivratri
    date(2021, 3, 29),   # Holi
    date(2021, 4, 2),    # Good Friday
    date(2021, 4, 14),   # Dr. Ambedkar Jayanti / Ram Navami
    date(2021, 4, 21),   # Ram Navami
    date(2021, 5, 13),   # Id-Ul-Fitr
    date(2021, 7, 21),   # Bakri Id
    date(2021, 8, 19),   # Moharram
    date(2021, 8, 30),   # Ganesh Chaturthi (half day)
    date(2021, 10, 15),  # Dussehra
    date(2021, 11, 4),   # Diwali-Laxmi Pujan
    date(2021, 11, 5),   # Diwali-Balipratipada
    date(2021, 11, 19),  # Gurunanak Jayanti

    # ── 2020 ──
    date(2020, 2, 21),   # Mahashivratri
    date(2020, 3, 10),   # Holi
    date(2020, 4, 2),    # Ram Navami
    date(2020, 4, 6),    # Mahavir Jayanti
    date(2020, 4, 10),   # Good Friday
    date(2020, 4, 14),   # Dr. Ambedkar Jayanti
    date(2020, 5, 1),    # Maharashtra Day
    date(2020, 5, 25),   # Id-Ul-Fitr
    date(2020, 8, 1),    # Bakri Id (Sat — observed on preceding or next day if needed)
    date(2020, 8, 15),   # Independence Day
    date(2020, 10, 2),   # Mahatma Gandhi Jayanti
    date(2020, 11, 16),  # Diwali-Balipratipada
    date(2020, 11, 30),  # Gurunanak Jayanti

    # ── 2019 ──
    date(2019, 1, 26),   # Republic Day (Saturday — may not affect)
    date(2019, 3, 4),    # Mahashivratri
    date(2019, 3, 21),   # Holi
    date(2019, 4, 17),   # Ram Navami
    date(2019, 4, 19),   # Good Friday / Mahavir Jayanti
    date(2019, 4, 29),   # General Elections
    date(2019, 5, 1),    # Maharashtra Day
    date(2019, 6, 5),    # Id-Ul-Fitr
    date(2019, 8, 12),   # Bakri Id
    date(2019, 8, 15),   # Independence Day
    date(2019, 9, 2),    # Ganesh Chaturthi
    date(2019, 9, 10),   # Moharram
    date(2019, 10, 2),   # Mahatma Gandhi Jayanti
    date(2019, 10, 8),   # Dussehra
    date(2019, 10, 21),  # General Election result day
    date(2019, 10, 28),  # Diwali-Laxmi Pujan
    date(2019, 11, 12),  # Gurunanak Jayanti
    date(2019, 12, 25),  # Christmas

    # ── 2018 ──
    date(2018, 1, 26),   # Republic Day
    date(2018, 2, 13),   # Mahashivratri
    date(2018, 3, 2),    # Holi
    date(2018, 3, 29),   # Mahavir Jayanti
    date(2018, 3, 30),   # Good Friday
    date(2018, 5, 1),    # Maharashtra Day
    date(2018, 8, 15),   # Independence Day
    date(2018, 8, 22),   # Bakri Id
    date(2018, 9, 13),   # Ganesh Chaturthi
    date(2018, 9, 20),   # Moharram
    date(2018, 10, 2),   # Mahatma Gandhi Jayanti
    date(2018, 10, 18),  # Dussehra
    date(2018, 11, 7),   # Diwali-Laxmi Pujan
    date(2018, 11, 8),   # Diwali-Balipratipada
    date(2018, 11, 23),  # Gurunanak Jayanti
    date(2018, 12, 25),  # Christmas

    # ── 2017 ──
    date(2017, 1, 26),   # Republic Day
    date(2017, 2, 24),   # Mahashivratri
    date(2017, 3, 13),   # Holi
    date(2017, 4, 4),    # Ram Navami
    date(2017, 4, 14),   # Dr. Ambedkar Jayanti / Good Friday
    date(2017, 5, 1),    # Maharashtra Day
    date(2017, 6, 26),   # Id-Ul-Fitr
    date(2017, 8, 15),   # Independence Day
    date(2017, 8, 25),   # Ganesh Chaturthi
    date(2017, 10, 2),   # Mahatma Gandhi Jayanti
    date(2017, 10, 19),  # Diwali-Laxmi Pujan
    date(2017, 10, 20),  # Diwali-Balipratipada
    date(2017, 12, 25),  # Christmas
}


def is_weekend(d: date) -> bool:
    """Check if a date is Saturday (5) or Sunday (6)."""
    return d.weekday() >= 5


def is_nse_holiday(d: date) -> bool:
    """Check if a date is a known NSE holiday."""
    return d in NSE_HOLIDAYS


def is_trading_day(d: date) -> bool:
    """
    Check if a date is likely a valid NSE trading day.

    A date is a trading day if:
    - It is not a weekend (Saturday/Sunday)
    - It is not a known NSE holiday

    Note: This is approximate for dates not in the holiday set. The actual
    ground truth is derived from bhavcopy file existence after download.
    """
    return not is_weekend(d) and not is_nse_holiday(d)


def trading_days_between(from_date: date, to_date: date) -> list[date]:
    """
    Return a list of estimated trading days in [from_date, to_date] (inclusive).

    Uses the hardcoded holiday calendar + weekend filter. For the most accurate
    results (especially for older years), cross-reference with actual bhavcopy
    files.
    """
    days = []
    current = from_date
    while current <= to_date:
        if is_trading_day(current):
            days.append(current)
        current += timedelta(days=1)
    return days


def derive_trading_days_from_files(data_dir: Path) -> set[date]:
    """
    Derive actual trading days from successfully downloaded bhavcopy files.

    This is the ground truth — if a bhavcopy file exists and was parseable,
    that date was a valid trading day.

    Args:
        data_dir: Directory containing raw bhavcopy files.

    Returns:
        Set of dates for which we have data.
    """
    from datetime import datetime

    trading_dates: set[date] = set()

    if not data_dir.exists():
        return trading_dates

    for filepath in data_dir.iterdir():
        name = filepath.name
        try:
            # Legacy format: fo{dd}{MMM}{yyyy}bhav.csv or .zip
            if name.startswith("fo") and "bhav" in name:
                date_part = name[2:11]  # e.g., "03OCT2023"
                d = datetime.strptime(date_part, "%d%b%Y").date()
                trading_dates.add(d)
            # UDiFF format: BhavCopy_NSE_FO_0_0_0_{YYYYMMDD}_F_0000.csv or .zip
            elif name.startswith("BhavCopy_NSE_FO"):
                parts = name.split("_")
                date_str = parts[6]  # YYYYMMDD
                d = datetime.strptime(date_str, "%Y%m%d").date()
                trading_dates.add(d)
        except (ValueError, IndexError):
            continue

    return trading_dates
