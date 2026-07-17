"""
Tests for the data layer modules.

Tests lot sizes, trading calendar, ATM strike resolution, and (when data
is available) option price queries and expiry resolution.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Lot Size Tests ─────────────────────────────────────────────────────────────

class TestLotSizes:
    """Test the historical lot size lookup."""

    def test_banknifty_lot_size_2022(self):
        """BANKNIFTY should be 25 in 2022 (after Oct 2020 change)."""
        from data.lot_sizes import get_lot_size
        assert get_lot_size("BANKNIFTY", date(2022, 6, 15)) == 25

    def test_banknifty_lot_size_pre_jul_2023(self):
        """BANKNIFTY should be 25 just before the Jul 2023 change."""
        from data.lot_sizes import get_lot_size
        assert get_lot_size("BANKNIFTY", date(2023, 7, 20)) == 25

    def test_banknifty_lot_size_post_jul_2023(self):
        """BANKNIFTY should be 15 on/after Jul 21, 2023."""
        from data.lot_sizes import get_lot_size
        assert get_lot_size("BANKNIFTY", date(2023, 7, 21)) == 15
        assert get_lot_size("BANKNIFTY", date(2024, 3, 15)) == 15

    def test_banknifty_lot_size_post_nov_2024(self):
        """BANKNIFTY should be 30 after Nov 20, 2024."""
        from data.lot_sizes import get_lot_size
        assert get_lot_size("BANKNIFTY", date(2024, 11, 20)) == 30
        assert get_lot_size("BANKNIFTY", date(2025, 1, 10)) == 30

    def test_nifty_lot_size_2022(self):
        """NIFTY should be 50 in 2022."""
        from data.lot_sizes import get_lot_size
        assert get_lot_size("NIFTY", date(2022, 6, 15)) == 50

    def test_nifty_lot_size_post_nov_2024(self):
        """NIFTY should be 75 after Nov 20, 2024."""
        from data.lot_sizes import get_lot_size
        assert get_lot_size("NIFTY", date(2024, 11, 20)) == 75

    def test_finnifty_lot_size_launch(self):
        """FINNIFTY should be 40 at launch in 2021."""
        from data.lot_sizes import get_lot_size
        assert get_lot_size("FINNIFTY", date(2021, 6, 15)) == 40

    def test_finnifty_lot_size_post_apr_2024(self):
        """FINNIFTY should be 25 after Apr 26, 2024."""
        from data.lot_sizes import get_lot_size
        assert get_lot_size("FINNIFTY", date(2024, 5, 1)) == 25

    def test_unknown_symbol_raises(self):
        """Unknown symbol should raise ValueError."""
        from data.lot_sizes import get_lot_size
        with pytest.raises(ValueError, match="Unknown symbol"):
            get_lot_size("INVALID", date(2024, 1, 1))

    def test_date_before_history_raises(self):
        """Date before earliest entry should raise ValueError."""
        from data.lot_sizes import get_lot_size
        with pytest.raises(ValueError, match="No lot size data"):
            get_lot_size("BANKNIFTY", date(2010, 1, 1))

    def test_lot_size_history(self):
        """get_lot_size_history should return a non-empty list."""
        from data.lot_sizes import get_lot_size_history
        history = get_lot_size_history("BANKNIFTY")
        assert len(history) > 0
        assert all(isinstance(d, date) and isinstance(s, int)
                    for d, s in history)


# ── Trading Calendar Tests ─────────────────────────────────────────────────────

class TestTradingCalendar:
    """Test the NSE trading calendar."""

    def test_weekend_not_trading_day(self):
        """Saturdays and Sundays should not be trading days."""
        from data.trading_calendar import is_trading_day
        # Saturday 2024-01-06
        assert not is_trading_day(date(2024, 1, 6))
        # Sunday 2024-01-07
        assert not is_trading_day(date(2024, 1, 7))

    def test_weekday_is_trading_day(self):
        """A normal weekday (not a holiday) should be a trading day."""
        from data.trading_calendar import is_trading_day
        # Monday 2024-01-08 — not a known holiday
        assert is_trading_day(date(2024, 1, 8))

    def test_republic_day_not_trading(self):
        """Republic Day (Jan 26) should not be a trading day."""
        from data.trading_calendar import is_trading_day
        assert not is_trading_day(date(2024, 1, 26))
        assert not is_trading_day(date(2023, 1, 26))

    def test_christmas_not_trading(self):
        """Christmas should not be a trading day."""
        from data.trading_calendar import is_trading_day
        assert not is_trading_day(date(2024, 12, 25))

    def test_trading_days_between(self):
        """Should return only valid trading days in a range."""
        from data.trading_calendar import trading_days_between
        # Jan 1-7, 2024: Mon(1=holiday?), Tue(2), Wed(3), Thu(4), Fri(5), Sat(6), Sun(7)
        # Jan 1 is not in our holiday list, so it's a trading day
        days = trading_days_between(date(2024, 1, 1), date(2024, 1, 7))
        # Should include Mon-Fri (5 days), exclude Sat+Sun
        assert len(days) == 5
        assert date(2024, 1, 6) not in days  # Saturday
        assert date(2024, 1, 7) not in days  # Sunday

    def test_holiday_week(self):
        """A week containing a holiday should have fewer trading days."""
        from data.trading_calendar import trading_days_between
        # Jan 22-26, 2024: Mon(22), Tue(23), Wed(24), Thu(25), Fri(26=Republic Day)
        days = trading_days_between(date(2024, 1, 22), date(2024, 1, 26))
        assert date(2024, 1, 26) not in days
        assert len(days) == 4  # Mon-Thu


# ── ATM Strike Resolution Tests ───────────────────────────────────────────────

class TestStrikeResolution:
    """Test ATM strike resolution logic."""

    def test_banknifty_exact(self):
        """Exact multiple of 100 should return itself."""
        from data.queries import resolve_atm_strike
        assert resolve_atm_strike("BANKNIFTY", 48000.0) == 48000

    def test_banknifty_round_up(self):
        """Price above midpoint should round up."""
        from data.queries import resolve_atm_strike
        assert resolve_atm_strike("BANKNIFTY", 48060.0) == 48100

    def test_banknifty_round_down(self):
        """Price below midpoint should round down."""
        from data.queries import resolve_atm_strike
        assert resolve_atm_strike("BANKNIFTY", 48030.0) == 48000

    def test_banknifty_midpoint(self):
        """Midpoint should round to nearest even (Python rounding)."""
        from data.queries import resolve_atm_strike
        # 48050 → round(48050/100) = round(480.5) = 480 (banker's rounding)
        result = resolve_atm_strike("BANKNIFTY", 48050.0)
        assert result in (48000, 48100)  # Either is acceptable

    def test_nifty_exact(self):
        """Exact multiple of 50 for NIFTY should return itself."""
        from data.queries import resolve_atm_strike
        assert resolve_atm_strike("NIFTY", 24000.0) == 24000

    def test_nifty_round_up(self):
        """NIFTY price above midpoint rounds up."""
        from data.queries import resolve_atm_strike
        assert resolve_atm_strike("NIFTY", 24030.0) == 24050

    def test_nifty_round_down(self):
        """NIFTY price below midpoint rounds down."""
        from data.queries import resolve_atm_strike
        assert resolve_atm_strike("NIFTY", 24010.0) == 24000

    def test_finnifty(self):
        """FINNIFTY uses 50-point intervals like NIFTY."""
        from data.queries import resolve_atm_strike
        assert resolve_atm_strike("FINNIFTY", 21530.0) == 21550

    def test_unknown_symbol(self):
        """Unknown symbol should raise ValueError."""
        from data.queries import resolve_atm_strike
        with pytest.raises(ValueError, match="Unknown symbol"):
            resolve_atm_strike("INVALID", 48000.0)


# ── Parser Tests ───────────────────────────────────────────────────────────────

class TestParser:
    """Test bhavcopy filename detection and date extraction."""

    def test_detect_legacy_format(self):
        """Should detect legacy format from filename."""
        from data.parser import _detect_format_from_filename
        path = Path("fo03OCT2023bhav.csv")
        assert _detect_format_from_filename(path) == "legacy"

    def test_detect_udiff_format(self):
        """Should detect UDiFF format from filename."""
        from data.parser import _detect_format_from_filename
        path = Path("BhavCopy_NSE_FO_0_0_0_20240708_F_0000.csv")
        assert _detect_format_from_filename(path) == "udiff"

    def test_extract_date_legacy(self):
        """Should extract date from legacy filename."""
        from data.parser import _extract_date_from_filename
        path = Path("fo03OCT2023bhav.csv")
        assert _extract_date_from_filename(path) == date(2023, 10, 3)

    def test_extract_date_udiff(self):
        """Should extract date from UDiFF filename."""
        from data.parser import _extract_date_from_filename
        path = Path("BhavCopy_NSE_FO_0_0_0_20240708_F_0000.csv")
        assert _extract_date_from_filename(path) == date(2024, 7, 8)

    def test_unknown_format_raises(self):
        """Unknown filename format should raise ValueError."""
        from data.parser import _detect_format_from_filename
        with pytest.raises(ValueError, match="Unrecognized"):
            _detect_format_from_filename(Path("random_file.csv"))


# ── Downloader URL Tests ──────────────────────────────────────────────────────

class TestDownloaderUrls:
    """Test URL construction for both format eras."""

    def test_legacy_url(self):
        """Legacy URL should follow the old NSE format."""
        from data.downloader import _get_bhavcopy_url
        url = _get_bhavcopy_url(date(2023, 10, 3))
        assert "historical/DERIVATIVES/2023/OCT" in url
        assert "fo03OCT2023bhav.csv.zip" in url

    def test_udiff_url(self):
        """UDiFF URL should follow the new NSE format."""
        from data.downloader import _get_bhavcopy_url
        url = _get_bhavcopy_url(date(2024, 7, 15))
        assert "BhavCopy_NSE_FO_0_0_0_20240715_F_0000.csv.zip" in url

    def test_cutover_date_uses_udiff(self):
        """The cutover date itself should use UDiFF format."""
        from data.downloader import _get_bhavcopy_url
        url = _get_bhavcopy_url(date(2024, 7, 8))
        assert "BhavCopy_NSE_FO" in url

    def test_day_before_cutover_uses_legacy(self):
        """Day before cutover should use legacy format."""
        from data.downloader import _get_bhavcopy_url
        url = _get_bhavcopy_url(date(2024, 7, 5))
        assert "historical/DERIVATIVES" in url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
