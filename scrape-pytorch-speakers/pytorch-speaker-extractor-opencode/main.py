"""
PyTorch Conference North America — Talk Extractor

Fetches the conference schedule from the Sessionize API, extracts all talks
with their speakers and company affiliations, and writes the results to a CSV file.

Usage:
    uv run python main.py
"""

import csv
import logging
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCHEDULE_URL = (
    "https://events.linuxfoundation.org/pytorch-conference-north-america/"
    "program/schedule/"
)
OUTPUT_CSV = Path("talks.csv")

# Sessionize API code extracted from the schedule page
SESSIONIZE_API_CODE = "0d2wfbyq"
SESSIONIZE_API_URL = (
    f"https://sessionize.com/api/v2/{SESSIONIZE_API_CODE}/view/All"
)

# Question IDs from the Sessionize API used to identify speaker fields
COMPANY_QUESTION_ID = 128058
TITLE_QUESTION_ID = 128059

# Maximum number of speakers we expect per talk (used for CSV column width)
MAX_SPEAKERS = 10

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API Helpers
# ---------------------------------------------------------------------------


def fetch_sessionize_data() -> dict:
    """Download the full schedule data from the Sessionize API.

    Returns
    -------
    dict
        The JSON response containing ``sessions``, ``speakers``,
        ``questions``, ``categories``, and ``rooms``.

    Raises
    ------
    requests.HTTPError
        If the HTTP request did not return a successful status code.
    """
    log.info("Fetching schedule data from Sessionize API")
    resp = requests.get(SESSIONIZE_API_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_speaker_lookup(data: dict) -> dict[str, dict]:
    """Build a mapping of speaker UUID -> speaker dict for fast lookups.

    Parameters
    ----------
    data : dict
        The full Sessionize API response.

    Returns
    -------
    dict
        Mapping from speaker ``id`` (UUID string) to the speaker dict.
    """
    return {sp["id"]: sp for sp in data["speakers"]}


def get_speaker_company(speaker: dict) -> str:
    """Extract the company / affiliation from a speaker's question answers.

    Parameters
    ----------
    speaker : dict
        A speaker dict from the Sessionize API.

    Returns
    -------
    str
        The company name, or an empty string if not found.
    """
    for qa in speaker.get("questionAnswers", []):
        if qa.get("questionId") == COMPANY_QUESTION_ID:
            return qa.get("answerValue", "")
    return ""


def get_speaker_title(speaker: dict) -> str:
    """Extract the professional title from a speaker's question answers.

    Parameters
    ----------
    speaker : dict
        A speaker dict from the Sessionize API.

    Returns
    -------
    str
        The title, or an empty string if not found.
    """
    for qa in speaker.get("questionAnswers", []):
        if qa.get("questionId") == TITLE_QUESTION_ID:
            return qa.get("answerValue", "")
    return ""


# ---------------------------------------------------------------------------
# Scraping Helpers (for fallback / HTML extraction)
# ---------------------------------------------------------------------------


def fetch_page(url: str) -> str:
    """Download the schedule page and return its HTML text.

    Parameters
    ----------
    url : str
        The full URL of the conference schedule page.

    Returns
    -------
    str
        The raw HTML content.

    Raises
    ------
    requests.HTTPError
        If the HTTP request did not return a successful status code.
    """
    log.info("Fetching %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def extract_api_code_from_html(html: str) -> str:
    """Extract the Sessionize API code embedded in the schedule page.

    The page includes a data attribute containing JSON with
    ``sessionizeApiCode``. This function parses that JSON and returns
    the code.

    Parameters
    ----------
    html : str
        The raw HTML of the schedule page.

    Returns
    -------
    str
        The Sessionize API code (e.g. ``"0d2wfbyq"``).

    Raises
    ------
    ValueError
        If the API code cannot be found in the HTML.
    """
    import re

    # The data attribute contains JSON with the API code
    pattern = r'"sessionizeApiCode"\s*:\s*"([^"]+)"'
    match = re.search(pattern, html)
    if not match:
        raise ValueError(
            "Could not find sessionizeApiCode in the schedule page HTML. "
            "The page structure may have changed."
        )
    return match.group(1)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_talks_from_api(data: dict) -> list[dict]:
    """Extract all talks from the Sessionize API response.

    Parameters
    ----------
    data : dict
        The full Sessionize API response containing ``sessions`` and
        ``speakers``.

    Returns
    -------
    list[dict]
        Each dict has the keys:
            - ``talk_title`` (str)
            - ``speakers``   (list of (name, company) tuples)
    """
    sessions = data["sessions"]
    speaker_lookup = build_speaker_lookup(data)

    talks: list[dict] = []
    for session in sessions:
        # Skip service sessions (registration, breaks, meals, etc.)
        if session.get("isServiceSession", False):
            continue

        talk_title = session.get("title", "Untitled")
        speaker_ids = session.get("speakers", [])

        speakers: list[tuple[str, str]] = []
        for sid in speaker_ids:
            speaker = speaker_lookup.get(sid)
            if speaker:
                name = speaker.get("fullName", "")
                company = get_speaker_company(speaker)
                speakers.append((name, company))

        talks.append({
            "talk_title": talk_title,
            "speakers": speakers,
        })

    return talks


def extract_talks_from_html(html: str) -> list[dict]:
    """Parse the HTML and extract all talks with their speakers.

    This is a fallback method used when the Sessionize API is unavailable.
    It uses CSS selectors matching the page structure described by the user.

    Parameters
    ----------
    html : str
        The full HTML of the schedule page.

    Returns
    -------
    list[dict]
        Each dict has the keys:
            - ``talk_title`` (str)
            - ``speakers``   (list of (name, company) tuples)
    """
    # First, extract the API code from the HTML
    api_code = extract_api_code_from_html(html)
    log.info("Found Sessionize API code: %s (using API directly instead)", api_code)

    # Fall back to API call
    resp = requests.get(
        f"https://sessionize.com/api/v2/{api_code}/view/All", timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    return extract_talks_from_api(data)


def extract_talks(html: str | None = None) -> list[dict]:
    """Extract all talks, trying the API first and falling back to HTML.

    Parameters
    ----------
    html : str, optional
        Pre-fetched HTML. If provided and the API fails, this HTML will
        be used as a fallback.

    Returns
    -------
    list[dict]
        List of talk dicts with ``talk_title`` and ``speakers`` keys.
    """
    try:
        data = fetch_sessionize_data()
        talks = extract_talks_from_api(data)
        log.info("Extracted %d talks via Sessionize API", len(talks))
        return talks
    except requests.RequestException as exc:
        log.warning("Sessionize API failed (%s), falling back to HTML", exc)

    if html is None:
        html = fetch_page(SCHEDULE_URL)

    return extract_talks_from_html(html)


# ---------------------------------------------------------------------------
# CSV Output
# ---------------------------------------------------------------------------


def write_csv(talks: list[dict], output_path: Path) -> None:
    """Write the extracted talks to a CSV file.

    The CSV has the following columns::

        Talk Title, Speaker 1 Name, Speaker 1 Affiliation,
        Speaker 2 Name, Speaker 2 Affiliation, ...

    The number of speaker column pairs is determined by the maximum
    number of speakers found on any single talk.

    Parameters
    ----------
    talks : list[dict]
        The list of talk dicts returned by :func:`extract_talks`.
    output_path : Path
        Where to write the CSV file.
    """
    # Determine the maximum number of speakers across all talks
    max_speakers = min(
        MAX_SPEAKERS,
        max((len(t["speakers"]) for t in talks), default=0),
    )
    if max_speakers == 0:
        max_speakers = 1  # at least one speaker column pair

    # Build header
    header = ["Talk Title"]
    for i in range(1, max_speakers + 1):
        header.append(f"Speaker {i} Name")
        header.append(f"Speaker {i} Affiliation")

    # Build rows
    rows: list[list[str]] = []
    for talk in talks:
        row = [talk["talk_title"]]
        for i in range(max_speakers):
            if i < len(talk["speakers"]):
                name, company = talk["speakers"][i]
                row.extend([name, company])
            else:
                row.extend(["", ""])
        rows.append(row)

    # Write to CSV
    log.info(
        "Writing %d talks (%d speaker columns) to %s",
        len(rows),
        max_speakers,
        output_path,
    )
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    log.info("Done — wrote %d rows to %s", len(rows), output_path)


def write_company_counts_csv(talks: list[dict], output_path: Path) -> None:
    """Write a two-column CSV with company name and Speaker 1 company count.

    For each talk, the company of the first speaker (Speaker 1) is counted.
    Talks with no speakers or no Speaker 1 company are excluded.

    The output CSV has the columns::

        Company, Count

    Sorted by count descending, then company name alphabetically.

    Parameters
    ----------
    talks : list[dict]
        The list of talk dicts returned by :func:`extract_talks`.
    output_path : Path
        Where to write the company counts CSV file.
    """
    from collections import Counter

    # Count non-empty Speaker 1 companies
    company_counts: Counter = Counter()
    for talk in talks:
        if talk["speakers"]:
            _, company = talk["speakers"][0]
            if company.strip():
                company_counts[company.strip()] += 1

    # Sort by count descending, then company name ascending
    sorted_companies = sorted(
        company_counts.items(), key=lambda x: (-x[1], x[0])
    )

    # Write to CSV
    log.info("Writing %d company counts to %s", len(sorted_companies), output_path)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Company", "Count"])
        for company, count in sorted_companies:
            writer.writerow([company, count])

    log.info("Done — wrote %d company counts to %s", len(sorted_companies), output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    talks = extract_talks()
    write_csv(talks, OUTPUT_CSV)
    write_company_counts_csv(talks, Path("company_counts.csv"))
    log.info("Extracted %d talks successfully", len(talks))


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as exc:
        log.error("HTTP error: %s", exc)
        sys.exit(1)
    except requests.RequestException as exc:
        log.error("Request failed: %s", exc)
        sys.exit(1)
