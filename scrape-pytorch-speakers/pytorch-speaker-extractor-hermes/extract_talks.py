#!/usr/bin/env python3
"""
Extract talks and speakers from the PyTorch Conference North America schedule.

Uses the Sessionize API (the same backend powering the conference schedule page)
to fetch structured session and speaker data, then writes two CSV files:

    talks.csv       — one row per talk, expanded speaker columns
    company_counts.csv — one row per company, count of speaker_1_company

Service sessions (breaks, registration, keynotes without speakers) are
skipped — only actual conference talks are included.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Sessionize event ID extracted from the page source
SESSIONIZE_EVENT_ID = "0d2wfbyq"

# Sessionize API v2 endpoints
GRID_SMART_URL = (
    f"https://sessionize.com/api/v2/{SESSIONIZE_EVENT_ID}/view/GridSmart"
)
SPEAKERS_URL = (
    f"https://sessionize.com/api/v2/{SESSIONIZE_EVENT_ID}/view/Speakers"
)

OUTPUT_FILE = "talks.csv"
COMPANY_COUNTS_FILE = "company_counts.csv"

# HTTP headers — Sessionize may rate-limit without a user-agent
HEADERS: dict[str, str] = {
    "User-Agent": (
        "PyTorchCon Talk Extractor "
        "(https://github.com/pytorch-speaker-extractor)"
    ),
}

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def fetch_json(url: str) -> Any:
    """Fetch a JSON endpoint and return the parsed data."""
    print(f"  Fetching {url} ...")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_speaker_map(speakers_data: list[dict]) -> dict[str, str]:
    """Build a lookup: speaker full_name -> company.

    The Sessionize Speakers API returns a list of speaker objects. Each
    speaker has a ``questionAnswers`` array; the entry with ``question ==
    "Company"`` contains the affiliation we want.
    """
    name_to_company: dict[str, str] = {}

    for speaker in speakers_data:
        full_name = speaker.get("fullName", "")
        if not full_name:
            continue

        # Look for the Company answer in questionAnswers
        company = ""
        for qa in speaker.get("questionAnswers", []):
            if qa.get("question") == "Company":
                raw = qa.get("answer")
                company = raw.strip() if raw else ""
                break

        name_to_company[full_name] = company

    print(f"  Built speaker map: {len(name_to_company)} speakers")
    return name_to_company


# ---------------------------------------------------------------------------
# Session extraction
# ---------------------------------------------------------------------------
def extract_sessions(grid_data: list[dict]) -> list[dict]:
    """Walk the GridSmart structure and collect talk info.

    The GridSmart API returns a list of day objects, each containing rooms,
    each containing sessions. We walk this tree and skip service sessions
    (breaks, registration, etc.) by checking ``isServiceSession`` and
    whether the session has speakers.

    Returns a list of dicts:
        {
            "title": str,
            "speaker_names": list[str],
        }
    """
    talks: list[dict] = []

    for day in grid_data:
        for room in day.get("rooms", []):
            for session in room.get("sessions", []):
                # Skip service sessions (breaks, registration, meals, etc.)
                if session.get("isServiceSession", False):
                    continue

                # Skip sessions without any speaker info
                speaker_list = session.get("speakers", [])
                if not speaker_list:
                    continue

                title = session.get("title", "").strip()
                if not title:
                    continue

                talks.append({
                    "title": title,
                    "speaker_names": [
                        sp.get("name", "").strip()
                        for sp in speaker_list
                        if sp.get("name")
                    ],
                })

    return talks


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------
def write_talks_csv(talks: list[dict], speakers_map: dict[str, str],
                    output_path: str) -> None:
    """Write talks to CSV with one row per talk and expanded speaker columns.

    Columns:
        talk_title, speaker_1_name, speaker_1_company,
        speaker_2_name, speaker_2_company, ...
    """
    if not talks:
        print("No talks extracted — nothing to write.", file=sys.stderr)
        return

    # Determine the max number of speakers across all talks
    max_speakers = max(len(t["speaker_names"]) for t in talks)
    print(f"Maximum speakers on a single talk: {max_speakers}")

    # Build column headers
    headers = ["talk_title"]
    for i in range(1, max_speakers + 1):
        headers.append(f"speaker_{i}_name")
        headers.append(f"speaker_{i}_company")

    # Write the CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for talk in talks:
            row = [talk["title"]]
            for speaker_name in talk["speaker_names"]:
                company = speakers_map.get(speaker_name, "")
                row.append(speaker_name)
                row.append(company)
            # Pad with empty strings if fewer than max_speakers
            padding = (max_speakers - len(talk["speaker_names"])) * 2
            row.extend([""] * padding)
            writer.writerow(row)

    print(f"Written {len(talks)} talks to {output_path}")


# ---------------------------------------------------------------------------
# Company count aggregation
# ---------------------------------------------------------------------------
def write_company_counts_from_talks(talks: list[dict],
                                    speakers_map: dict[str, str],
                                    output_path: str) -> None:
    """Count speaker_1_company occurrences directly from in-memory data.

    Takes the already-fetched talks list and speaker map — no disk I/O.

    The output has columns:
        company, count

    Sorted by count descending, then alphabetically by company name.
    Empty/blank company values are excluded.
    """
    company_counter: Counter[str] = Counter()

    for talk in talks:
        # Only look at the first speaker (speaker_1)
        if talk["speaker_names"]:
            speaker_name = talk["speaker_names"][0]
            company = speakers_map.get(speaker_name, "").strip()
            if company:
                company_counter[company] += 1

    # Sort by count descending, then alphabetically
    sorted_companies = sorted(
        company_counter.items(), key=lambda x: (-x[1], x[0])
    )

    print(f"Found {len(sorted_companies)} unique companies")

    # Write the counts CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["company", "count"])
        for company, count in sorted_companies:
            writer.writerow([company, count])

    print(f"Written {len(sorted_companies)} company counts to {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    print("=== PyTorch Conference North America — Talk Extractor ===\n")

    # 1. Fetch structured session data from Sessionize
    print("Step 1: Fetching sessions ...")
    grid_data = fetch_json(GRID_SMART_URL)
    talks = extract_sessions(grid_data)
    print(f"  Found {len(talks)} talks with speakers.\n")

    # 2. Fetch speaker data to get company affiliations
    print("Step 2: Fetching speaker info ...")
    speakers_data = fetch_json(SPEAKERS_URL)
    speakers_map = build_speaker_map(speakers_data)

    # 3. Write talks CSV
    print("\nStep 3: Writing talks CSV ...")
    write_talks_csv(talks, speakers_map, OUTPUT_FILE)

    # 4. Write company counts CSV directly from in-memory data
    print("\nStep 4: Writing company counts CSV ...")
    write_company_counts_from_talks(talks, speakers_map, COMPANY_COUNTS_FILE)

    print(f"\nDone. {len(talks)} talks extracted, {COMPANY_COUNTS_FILE} generated.")


if __name__ == "__main__":
    main()
