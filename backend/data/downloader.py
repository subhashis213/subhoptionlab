"""
NSE F&O Bhavcopy Downloader.

Downloads daily bhavcopy files from NSE archives. Handles both:
- Legacy format (before July 8, 2024):
  https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{YYYY}/{MMM}/fo{dd}{MMM}{YYYY}bhav.csv.zip
- UDiFF format (July 8, 2024 onwards):
  https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{YYYYMMDD}_F_0000.csv.zip

NSE aggressively blocks automated requests, so we:
1. First establish a browser-like session (get cookies from nseindia.com)
2. Use realistic headers (User-Agent, Referer, Accept, etc.)
3. Rate-limit requests (configurable delay between downloads)
4. Retry on transient failures with exponential backoff
"""

import io
import logging
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from config import (
    LEGACY_BHAVCOPY_URL,
    NSE_BASE_URL,
    RAW_DIR,
    UDIFF_BHAVCOPY_URL,
    UDIFF_CUTOVER_DATE,
)
from data.trading_calendar import is_trading_day

logger = logging.getLogger(__name__)

# ── NSE Session Management ────────────────────────────────────────────────────

# Headers that mimic a real browser
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _create_nse_session() -> requests.Session:
    """
    Create a requests session with NSE cookies.

    NSE requires a valid session cookie to serve archive files. We get this
    by first visiting the main page, which sets the necessary cookies.
    """
    session = requests.Session()
    session.headers.update(_BROWSER_HEADERS)

    try:
        # Visit the main NSE page to get cookies
        resp = session.get(NSE_BASE_URL, timeout=15)
        resp.raise_for_status()
        logger.info("NSE session established (cookies: %s)", list(session.cookies.keys()))
    except requests.RequestException as e:
        logger.warning(
            "Failed to establish NSE session (cookies may be missing): %s", e
        )

    return session


# ── URL Construction ───────────────────────────────────────────────────────────

_UDIFF_CUTOVER = datetime.strptime(UDIFF_CUTOVER_DATE, "%Y-%m-%d").date()


def _get_bhavcopy_url(d: date) -> str:
    """Build the download URL for a given date based on the format era."""
    if d >= _UDIFF_CUTOVER:
        # UDiFF format: BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip
        return UDIFF_BHAVCOPY_URL.format(date_compact=d.strftime("%Y%m%d"))
    else:
        # Legacy format: fo{dd}{MMM}{YYYY}bhav.csv.zip
        return LEGACY_BHAVCOPY_URL.format(
            year=d.strftime("%Y"),
            month_upper=d.strftime("%b").upper(),
            dd=d.strftime("%d"),
        )


def _get_expected_filename(d: date) -> str:
    """Return the expected CSV filename inside the ZIP for a given date."""
    if d >= _UDIFF_CUTOVER:
        return f"BhavCopy_NSE_FO_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv"
    else:
        return f"fo{d.strftime('%d%b%Y').upper()}bhav.csv"


def _get_output_csv_path(d: date, output_dir: Path) -> Path:
    """Return the path where we save the extracted CSV."""
    if d >= _UDIFF_CUTOVER:
        return output_dir / f"BhavCopy_NSE_FO_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv"
    else:
        return output_dir / f"fo{d.strftime('%d%b%Y').upper()}bhav.csv"


# ── Download Logic ─────────────────────────────────────────────────────────────


def download_bhavcopy(
    d: date,
    session: requests.Session,
    output_dir: Path | None = None,
    max_retries: int = 3,
) -> Path | None:
    """
    Download and extract a single day's F&O bhavcopy.

    Args:
        d: The trading date to download.
        session: An authenticated NSE requests session.
        output_dir: Directory to save the CSV. Defaults to RAW_DIR.
        max_retries: Number of retries on transient failures.

    Returns:
        Path to the extracted CSV file, or None if download failed.
    """
    if output_dir is None:
        output_dir = RAW_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    csv_path = _get_output_csv_path(d, output_dir)
    if csv_path.exists() and csv_path.stat().st_size > 100:
        logger.debug("Already downloaded: %s", csv_path.name)
        return csv_path

    url = _get_bhavcopy_url(d)
    logger.info("Downloading bhavcopy for %s: %s", d, url)

    for attempt in range(1, max_retries + 1):
        try:
            # Set Referer to look more legitimate
            headers = {"Referer": f"{NSE_BASE_URL}/all-reports"}
            resp = session.get(url, headers=headers, timeout=30)

            if resp.status_code == 404:
                logger.info(
                    "No bhavcopy for %s (404 — likely a holiday or weekend)", d
                )
                return None

            resp.raise_for_status()

            # Extract the CSV from the ZIP
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                # Find the CSV file inside the ZIP
                csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
                if not csv_names:
                    logger.error("No CSV found in ZIP for %s", d)
                    return None

                # Use the first CSV file found
                csv_name = csv_names[0]
                csv_content = zf.read(csv_name)

                # Save with our standard name
                csv_path.write_bytes(csv_content)
                logger.info(
                    "Saved: %s (%d bytes)", csv_path.name, len(csv_content)
                )
                return csv_path

        except zipfile.BadZipFile:
            logger.error("Corrupted ZIP for %s (attempt %d/%d)", d, attempt, max_retries)
        except requests.RequestException as e:
            logger.warning(
                "Download failed for %s (attempt %d/%d): %s",
                d, attempt, max_retries, e,
            )

        if attempt < max_retries:
            backoff = 2 ** attempt
            logger.info("Retrying in %ds...", backoff)
            time.sleep(backoff)

    logger.error("Failed to download bhavcopy for %s after %d attempts", d, max_retries)
    return None


def download_date_range(
    from_date: date,
    to_date: date,
    output_dir: Path | None = None,
    delay_seconds: float = 1.5,
) -> dict[date, Path | None]:
    """
    Download bhavcopies for all trading days in a date range.

    Args:
        from_date: Start date (inclusive).
        to_date: End date (inclusive).
        output_dir: Directory to save CSVs. Defaults to RAW_DIR.
        delay_seconds: Delay between downloads to avoid NSE rate-limiting.

    Returns:
        Dictionary mapping each attempted date to its CSV path (or None if
        the download failed / date was a holiday).
    """
    if output_dir is None:
        output_dir = RAW_DIR

    session = _create_nse_session()
    results: dict[date, Path | None] = {}

    current = from_date
    total_days = (to_date - from_date).days + 1
    downloaded = 0
    skipped = 0

    logger.info(
        "Starting download: %s to %s (%d calendar days)",
        from_date, to_date, total_days,
    )

    while current <= to_date:
        if not is_trading_day(current):
            current += timedelta(days=1)
            skipped += 1
            continue

        result = download_bhavcopy(current, session, output_dir)
        results[current] = result

        if result is not None:
            downloaded += 1

        # Rate limiting
        time.sleep(delay_seconds)
        current += timedelta(days=1)

        # Progress logging every 20 downloads
        if downloaded > 0 and downloaded % 20 == 0:
            logger.info(
                "Progress: %d downloaded, %d skipped, currently at %s",
                downloaded, skipped, current,
            )

            # Re-establish session periodically (NSE sessions expire)
            if downloaded % 100 == 0:
                logger.info("Re-establishing NSE session...")
                session = _create_nse_session()
                time.sleep(2)

    logger.info(
        "Download complete: %d successful, %d total trading days attempted",
        downloaded,
        len(results),
    )
    return results


# ── CLI Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Download NSE F&O bhavcopy files for a date range."
    )
    parser.add_argument(
        "--from-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: raw_bhavcopies/)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between downloads in seconds (default: 1.5)",
    )

    args = parser.parse_args()

    results = download_date_range(
        from_date=args.from_date,
        to_date=args.to_date,
        output_dir=args.output_dir,
        delay_seconds=args.delay,
    )

    # Summary
    success = sum(1 for v in results.values() if v is not None)
    failed = sum(1 for v in results.values() if v is None)
    print(f"\n{'='*60}")
    print(f"Download Summary")
    print(f"{'='*60}")
    print(f"  Date range: {args.from_date} to {args.to_date}")
    print(f"  Successfully downloaded: {success}")
    print(f"  Failed/Holiday: {failed}")
    print(f"  Files saved to: {args.output_dir or RAW_DIR}")
