#!/usr/bin/env python3
"""
extract_talks.py

Extracts all talk sessions and speaker information from the PyTorch Conference
North America 2026 schedule via the Sessionize API embedded in the event page.

The schedule page at:
  https://events.linuxfoundation.org/pytorch-conference-north-america/program/schedule/
uses Sessionize (https://sessionize.com) to serve session data. Rather than
attempting to scrape the JavaScript-rendered HTML, we call the Sessionize API
directly using the event ID found in the page source.

The Sessionize speaker records include a `questionAnswers` array with structured
fields submitted during the CFP process. Question ID 128058 holds the clean
company/organization name entered by the speaker themselves.

Outputs:
  pytorch_talks.csv
    - One row per session (talk, workshop, keynote, etc.)
    - Columns: title, speaker1_name, speaker1_company, speaker2_name, speaker2_company, ...
    - The number of speaker column pairs expands to fit the most-speaker session.
    - Sessions without speakers (Registration, Breaks, etc.) still get a row
      with empty speaker columns.

  company_counts.csv
    - One row per unique company drawn from speaker1_company.
    - Columns: company, count
    - Sorted by count descending, then company name ascending.
"""

import csv
import sys
from collections import Counter

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The Sessionize API event ID, discovered in the event page source:
#   sessionizeAllDataUrl = "https://sessionize.com/api/v2/0d2wfbyq/view/All"
SESSIONIZE_EVENT_ID = "0d2wfbyq"
API_URL = f"https://sessionize.com/api/v2/{SESSIONIZE_EVENT_ID}/view/All"

TALKS_OUTPUT_FILE = "pytorch_talks.csv"
COMPANIES_OUTPUT_FILE = "company_counts.csv"

# Sessionize CFP question IDs for this event.
QUESTION_COMPANY = 128058   # "What is your company/organization?"
QUESTION_JOB_TITLE = 128059 # "What is your job title?"

# Minimum expected session count — used as a sanity check after fetching.
MIN_EXPECTED_SESSIONS = 139


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_schedule_data(url: str) -> dict:
    """
    Fetch the full schedule JSON from the Sessionize API.

    Returns a dict with keys: sessions, speakers, questions, categories, rooms.
    Raises requests.HTTPError if the request fails.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    print(f"Fetching schedule data from: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Data processing — sessions
# ---------------------------------------------------------------------------

def build_speaker_lookup(speakers: list[dict]) -> dict[str, dict]:
    """
    Build a dict mapping speaker ID -> speaker record for O(1) lookup.

    Also pre-processes each record to extract the structured company name
    from the questionAnswers array so downstream code doesn't have to.
    """
    lookup = {}
    for sp in speakers:
        # Index the CFP question answers by question ID for easy access.
        qa = {q["questionId"]: q["answerValue"] for q in sp.get("questionAnswers", [])}
        sp["_company"] = (qa.get(QUESTION_COMPANY) or "").strip()
        lookup[sp["id"]] = sp
    return lookup


def get_speaker_columns(session: dict, speaker_lookup: dict[str, dict]) -> list[tuple[str, str]]:
    """
    Return a list of (name, company) tuples for all speakers in a session.

    Company is drawn from the speaker's structured CFP answer (question ID
    128058), not the free-form tagLine.
    """
    result = []
    for speaker_id in session.get("speakers", []):
        sp = speaker_lookup.get(speaker_id)
        if sp is None:
            result.append((f"[unknown speaker {speaker_id}]", ""))
            continue
        name = (sp.get("fullName") or "").strip()
        company = sp["_company"]
        result.append((name, company))
    return result


def process_sessions(data: dict) -> tuple[list[dict], int]:
    """
    Process raw API data into a flat list of session dicts ready for CSV output.

    Each output dict has:
      - title    : str
      - speakers : list of (name, company) tuples

    Also returns the maximum number of speakers found in any single session,
    which determines how many speaker column pairs the CSV will have.
    """
    speaker_lookup = build_speaker_lookup(data["speakers"])
    sessions = data["sessions"]

    processed = []
    max_speakers = 0

    for session in sessions:
        title = session.get("title", "").strip()
        speakers = get_speaker_columns(session, speaker_lookup)
        max_speakers = max(max_speakers, len(speakers))
        processed.append({"title": title, "speakers": speakers})

    return processed, max_speakers


# ---------------------------------------------------------------------------
# Data processing — company counts
# ---------------------------------------------------------------------------

def count_companies(sessions: list[dict]) -> Counter:
    """
    Count how many primary speakers (speaker1) come from each company.

    Only the first speaker's company is counted, matching the user's request
    for a breakdown by speaker1_company. Sessions without speakers are skipped.
    """
    company_counts: Counter = Counter()
    for session in sessions:
        if not session["speakers"]:
            continue
        _name, company = session["speakers"][0]
        if company:
            company_counts[company] += 1
    return company_counts


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def build_header(max_speakers: int) -> list[str]:
    """
    Build the CSV header row for the talks file.

    Layout: title, speaker1_name, speaker1_company, speaker2_name, speaker2_company, ...
    """
    header = ["title"]
    for i in range(1, max_speakers + 1):
        header.append(f"speaker{i}_name")
        header.append(f"speaker{i}_company")
    return header


def write_talks_csv(sessions: list[dict], max_speakers: int, output_file: str) -> None:
    """
    Write all sessions to a CSV file.

    Rows with fewer speakers than the maximum are padded with empty strings
    so every row has the same number of columns.
    """
    header = build_header(max_speakers)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for session in sessions:
            row = [session["title"]]
            for name, company in session["speakers"]:
                row.append(name)
                row.append(company)
            # Pad with empty strings so every row has the same column count.
            empty_pairs_needed = max_speakers - len(session["speakers"])
            row.extend(["", ""] * empty_pairs_needed)
            writer.writerow(row)

    print(f"Wrote {len(sessions)} sessions to '{output_file}'")


def write_company_counts_csv(company_counts: Counter, output_file: str) -> None:
    """
    Write company speaker counts to a two-column CSV file.

    Columns: company, count
    Sorted by count descending, then company name ascending for stable ordering
    when two companies have the same count.
    """
    sorted_rows = sorted(company_counts.items(), key=lambda x: (-x[1], x[0].lower()))

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["company", "count"])
        for company, count in sorted_rows:
            writer.writerow([company, count])

    print(f"Wrote {len(sorted_rows)} companies to '{output_file}'")


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def print_summary(sessions: list[dict]) -> None:
    """Print a brief summary of the extracted data."""
    total = len(sessions)
    with_speakers = sum(1 for s in sessions if s["speakers"])
    max_sp = max((len(s["speakers"]) for s in sessions), default=0)

    print(f"\n--- Session Summary ---")
    print(f"  Total sessions              : {total}")
    print(f"  Sessions with speakers      : {with_speakers}")
    print(f"  Sessions without speakers   : {total - with_speakers}")
    print(f"  Max speakers in one session : {max_sp}")


def print_company_sample(company_counts: Counter, top_n: int = 10) -> None:
    """Print the top N companies by speaker count."""
    print(f"\n--- Top {top_n} Companies by Speaker1 Count ---")
    for company, count in company_counts.most_common(top_n):
        print(f"  {count:3d}  {company}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        data = fetch_schedule_data(API_URL)
    except requests.RequestException as exc:
        print(f"Error fetching schedule data: {exc}", file=sys.stderr)
        sys.exit(1)

    raw_sessions = data.get("sessions", [])
    raw_speakers = data.get("speakers", [])
    print(f"API returned {len(raw_sessions)} sessions and {len(raw_speakers)} speakers.")

    if len(raw_sessions) < MIN_EXPECTED_SESSIONS:
        print(
            f"Warning: expected at least {MIN_EXPECTED_SESSIONS} sessions "
            f"but only got {len(raw_sessions)}.",
            file=sys.stderr,
        )

    sessions, max_speakers = process_sessions(data)

    write_talks_csv(sessions, max_speakers, TALKS_OUTPUT_FILE)

    company_counts = count_companies(sessions)
    write_company_counts_csv(company_counts, COMPANIES_OUTPUT_FILE)

    print_summary(sessions)
    print_company_sample(company_counts)


if __name__ == "__main__":
    main()
