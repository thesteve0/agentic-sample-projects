#!/usr/bin/env python3
"""
Extract talks and speakers from the PyTorch Conference North America schedule.

This script fetches schedule data from the Sessionize API (which powers the
conference website), extracts talk titles and speaker information, and writes
the results to a CSV file.

API endpoint:
    https://sessionize.com/api/v2/0d2wfbyq/view/All

Output format (CSV):
    - Column 1: Talk Title
    - For each speaker: Speaker N Name, Speaker N Company

Example row:
    Contributing to PyTorch with AI agents,Alex Goldberg,Google,
    How PyTorch Powers Open Foundational Models,Louis Castricone,NVIDIA,Jeff Stancl,NVIDIA

Usage:
    source .venv/bin/activate
    python extract_talks.py
"""

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The Sessionize API endpoint for this conference.
# This is the same API that the conference website uses to load schedule data.
SESSIONIZE_API_URL = (
    "https://sessionize.com/api/v2/0d2wfbyq/view/All"
)

OUTPUT_CSV = Path("talks_and_speakers.csv")

# Output file for company-speaker-count aggregation
COMPANY_COUNT_CSV = Path("speaker_company_counts.csv")

# Red Hat output files
REDHAT_TALKS_CSV = Path("redhat_talks_and_speakers.csv")
REDHAT_SPEAKERS_CSV = Path("redhat_speakers_list.csv")

# Known Red Hat company names (exact match, case-sensitive after lowercasing)
REDHAT_COMPANY_VARIANTS = {"red hat", "red hat llc", "redhat"}

# The question ID used for speaker company information in Sessionize.
# This ID is conference-specific and found in the API's "questions" list.
SPEAKER_COMPANY_QUESTION_ID = 128058

# Request timeout in seconds
REQUEST_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Speaker:
    """Represents a single speaker with name and company affiliation."""

    name: str
    company: str


@dataclass
class Talk:
    """Represents a single talk with its title and list of speakers."""

    title: str
    speakers: List[Speaker] = field(default_factory=list)


# ---------------------------------------------------------------------------
# API data fetching
# ---------------------------------------------------------------------------

def fetch_schedule_data(url: str, timeout: int = REQUEST_TIMEOUT) -> dict:
    """Fetch and parse the schedule data from the Sessionize API.

    Args:
        url: The Sessionize API endpoint URL.
        timeout: Request timeout in seconds.

    Returns:
        A dictionary with keys: 'sessions', 'speakers', 'questions',
        'categories', 'rooms'.

    Raises:
        requests.RequestException: If the API request fails.
    """
    print(f"Fetching schedule from Sessionize API: {url}")
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    print(f"Downloaded {len(response.text):,} bytes of API data")
    return data


# ---------------------------------------------------------------------------
# Speaker lookup
# ---------------------------------------------------------------------------

def build_speaker_lookup(
    speakers_list: list, company_question_id: int = SPEAKER_COMPANY_QUESTION_ID
) -> Dict[str, Speaker]:
    """Build a lookup dictionary mapping speaker UUIDs to Speaker objects.

    The Sessionize API returns speakers as a flat list, each with:
    - firstName, lastName: the speaker's name
    - questionAnswers: a list of {questionId, answerValue} pairs,
      where one entry holds the company affiliation.

    Args:
        speakers_list: The 'speakers' list from the Sessionize API response.
        company_question_id: The question ID corresponding to the company field.

    Returns:
        A dictionary mapping speaker UUID strings to Speaker objects.
    """
    lookup: Dict[str, Speaker] = {}

    for speaker_data in speakers_list:
        speaker_id = speaker_data["id"]
        first_name = speaker_data.get("firstName", "").strip()
        last_name = speaker_data.get("lastName", "").strip()
        name = f"{first_name} {last_name}".strip()

        # Extract company from questionAnswers
        company = ""
        for qa in speaker_data.get("questionAnswers", []):
            if qa.get("questionId") == company_question_id:
                company = qa.get("answerValue", "").strip()
                break

        lookup[speaker_id] = Speaker(name=name, company=company)

    print(f"Built speaker lookup: {len(lookup)} speakers indexed")
    return lookup


# ---------------------------------------------------------------------------
# Talk extraction
# ---------------------------------------------------------------------------

def extract_talks(
    sessions_list: list, speaker_lookup: Dict[str, Speaker]
) -> List[Talk]:
    """Extract all talks from the sessions list, resolving speaker info.

    Each session from the API has:
    - title: the talk title
    - speakers: a list of speaker UUIDs referencing the speakers list

    Args:
        sessions_list: The 'sessions' list from the Sessionize API response.
        speaker_lookup: Dictionary mapping speaker UUIDs to Speaker objects.

    Returns:
        A list of Talk objects.
    """
    talks = []

    for session_data in sessions_list:
        title = session_data.get("title", "").strip()
        if not title:
            continue  # Skip sessions with no title

        # Resolve speaker UUIDs to Speaker objects
        speaker_ids = session_data.get("speakers", [])
        speakers = [
            speaker_lookup[sid]
            for sid in speaker_ids
            if sid in speaker_lookup
        ]

        talks.append(Talk(title=title, speakers=speakers))

    return talks


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def determine_max_speakers(talks: List[Talk]) -> int:
    """Determine the maximum number of speakers across all talks.

    This ensures the CSV has a consistent number of columns for every row.

    Args:
        talks: List of all extracted Talk objects.

    Returns:
        The maximum number of speakers found in any single talk, or 0 if empty.
    """
    if not talks:
        return 0
    return max(len(t.speakers) for t in talks)


def write_talks_to_csv(talks: List[Talk], output_path: Path) -> None:
    """Write all talks and speakers to a CSV file.

    The CSV layout is:
        Talk Title, Speaker 1 Name, Speaker 1 Company,
        Speaker 2 Name, Speaker 2 Company, ...

    Each talk gets exactly one row. Columns for speakers beyond what a talk
    has are padded with empty strings so every row has the same width.

    Args:
        talks: List of Talk objects to write.
        output_path: Path to the output CSV file.
    """
    max_speakers = determine_max_speakers(talks)

    # Build header: Talk Title + (Speaker N Name, Speaker N Company) pairs
    header = ["Talk Title"]
    for i in range(1, max_speakers + 1):
        header.extend([f"Speaker {i} Name", f"Speaker {i} Company"])

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)

        for talk in talks:
            row = [talk.title]
            for speaker in talk.speakers:
                row.append(speaker.name)
                row.append(speaker.company)
            # Pad remaining speaker columns with empty strings
            remaining = max_speakers - len(talk.speakers)
            for _ in range(remaining * 2):
                row.append("")
            writer.writerow(row)

    print(f"Wrote {len(talks)} talks to '{output_path}'")


# ---------------------------------------------------------------------------
# Statistics and reporting
# ---------------------------------------------------------------------------

def compute_company_counts(talks: List[Talk]) -> Dict[str, int]:
    """Count how many talks have each company as the first speaker's affiliation.

    For every talk, we look at Speaker 1's company and increment a counter
    for that company. Talks with no speakers (or no first speaker) are
    skipped.

    Args:
        talks: List of all extracted Talk objects.

    Returns:
        A dictionary mapping company names to their count of talks where
        they appear as the first speaker's company.
    """
    counts: Dict[str, int] = {}

    for talk in talks:
        if talk.speakers:
            company = talk.speakers[0].company
            if company:
                counts[company] = counts.get(company, 0) + 1

    return counts


def write_company_counts_to_csv(
    company_counts: Dict[str, int], output_path: Path
) -> None:
    """Write company speaker counts to a two-column CSV.

    The CSV has:
        - Column 1: Company Name
        - Column 2: Count of talks where this company is the first speaker

    Rows are sorted by count in descending order, then alphabetically by
    company name for ties.

    Args:
        company_counts: Dictionary mapping company names to counts.
        output_path: Path to the output CSV file.
    """
    # Sort: descending by count, then ascending by company name for ties
    sorted_entries = sorted(
        company_counts.items(), key=lambda x: (-x[1], x[0])
    )

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Company", "Count"])

        for company, count in sorted_entries:
            writer.writerow([company, count])

    print(f"Wrote {len(sorted_entries)} company counts to '{output_path}'")


def print_statistics(talks: List[Talk]) -> None:
    """Print summary statistics about the extracted talks.

    Args:
        talks: List of all extracted Talk objects.
    """
    total = len(talks)
    with_speakers = sum(1 for t in talks if t.speakers)
    without_speakers = total - with_speakers
    total_speakers = sum(len(t.speakers) for t in talks)

    # Speaker count distribution
    speaker_counts: Dict[int, int] = {}
    for t in talks:
        count = len(t.speakers)
        speaker_counts[count] = speaker_counts.get(count, 0) + 1

    print("\n--- Statistics ---")
    print(f"Total talks:                {total}")
    print(f"Talks with speakers:        {with_speakers}")
    print(f"Talks without speakers:     {without_speakers}")
    print(f"Total speaker assignments:  {total_speakers}")
    print(f"\nSpeakers per talk breakdown:")
    for count in sorted(speaker_counts.keys()):
        n = speaker_counts[count]
        label = "talk" if count == 1 else "talks"
        print(f"  {count} speaker{'' if count == 1 else 's'}:  {n} {label}")


# ---------------------------------------------------------------------------
# Red Hat filtering
# ---------------------------------------------------------------------------

def is_red_hat_company(company: str) -> bool:
    """Check if a company name is a known Red Hat variant.

    Matches case-insensitively against known variants:
      - "Red Hat"
      - "RedHat"
      - "Red Hat LLC"

    Args:
        company: The company name string from the speaker data.

    Returns:
        True if the company matches a Red Hat variant.
    """
    return company.lower() in REDHAT_COMPANY_VARIANTS


def filter_redhat_talks(talks: List[Talk]) -> List[Talk]:
    """Filter talks to only those with at least one Red Hat speaker.

    Checks all speakers up to the maximum of 3 per talk.

    Args:
        talks: List of all Talk objects.

    Returns:
        A list of Talk objects where at least one speaker's company
        matches a Red Hat variant.
    """
    redhat_talks = []
    for talk in talks:
        for speaker in talk.speakers[:3]:  # max 3 speakers per talk
            if is_red_hat_company(speaker.company):
                redhat_talks.append(talk)
                break
    return redhat_talks


def write_redhat_talks_to_csv(
    redhat_talks: List[Talk], output_path: Path
) -> None:
    """Write Red Hat talks and speakers to a CSV file.

    The CSV has:
        - Column 1: Talk Title
        - Column 2: Speaker 1 Name
        - Column 3: Speaker 1 Company
        - Column 4: Speaker 2 Name
        - Column 5: Speaker 2 Company
        - Column 6: Speaker 3 Name
        - Column 7: Speaker 3 Company

    Only talks with at least one Red Hat speaker are included.

    Args:
        redhat_talks: List of Talk objects filtered to Red Hat speakers.
        output_path: Path to the output CSV file.
    """
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Talk Title",
            "Speaker 1 Name", "Speaker 1 Company",
            "Speaker 2 Name", "Speaker 2 Company",
            "Speaker 3 Name", "Speaker 3 Company",
        ])

        for talk in redhat_talks:
            row = [talk.title]
            for speaker in talk.speakers[:3]:  # max 3
                row.append(speaker.name)
                row.append(speaker.company)
            # Pad if fewer than 3 speakers
            for _ in range((3 - len(talk.speakers)) * 2):
                row.append("")
            writer.writerow(row)

    print(f"Wrote {len(redhat_talks)} Red Hat talks to '{output_path}'")


def write_redhat_speakers_to_csv(
    redhat_talks: List[Talk], output_path: Path
) -> None:
    """Write a deduplicated list of Red Hat speakers to a CSV file.

    The CSV has:
        - Column 1: Speaker Name
        - Column 2: Company
        - Column 3: Talk Titles (semicolon-separated)

    Args:
        redhat_talks: List of Talk objects with Red Hat speakers.
        output_path: Path to the output CSV file.
    """
    # Build a mapping: speaker_name -> {company, talk_titles}
    speaker_map: Dict[str, Dict] = {}
    for talk in redhat_talks:
        for speaker in talk.speakers[:3]:
            if is_red_hat_company(speaker.company):
                name = speaker.name
                if name not in speaker_map:
                    speaker_map[name] = {
                        "company": speaker.company,
                        "talks": [],
                    }
                speaker_map[name]["talks"].append(talk.title)

    # Sort by speaker name
    sorted_speakers = sorted(speaker_map.items(), key=lambda x: x[0])

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Speaker Name", "Company", "Talk Titles"])

        for name, info in sorted_speakers:
            talks_str = "; ".join(info["talks"])
            writer.writerow([name, info["company"], talks_str])

    print(f"Wrote {len(sorted_speakers)} Red Hat speakers to '{output_path}'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Fetch schedule data, extract talks, and write CSV output."""
    # Step 1: Fetch raw data from the Sessionize API
    try:
        api_data = fetch_schedule_data(SESSIONIZE_API_URL)
    except requests.RequestException as exc:
        print(f"Error fetching schedule data: {exc}", file=sys.stderr)
        sys.exit(1)

    sessions_list = api_data.get("sessions", [])
    speakers_list = api_data.get("speakers", [])

    print(f"API returned {len(sessions_list)} session(s) and {len(speakers_list)} speaker(s)")

    # Step 2: Build a lookup table for speakers (UUID -> Speaker object)
    speaker_lookup = build_speaker_lookup(speakers_list)

    # Step 3: Extract talks, resolving speaker references
    talks = extract_talks(sessions_list, speaker_lookup)

    if not talks:
        print("No talks found. Check the API data.", file=sys.stderr)
        sys.exit(1)

    # Step 4: Write output CSV
    write_talks_to_csv(talks, OUTPUT_CSV)

    # Step 5: Compute and write company speaker counts
    company_counts = compute_company_counts(talks)
    write_company_counts_to_csv(company_counts, COMPANY_COUNT_CSV)

    # Step 5b: Filter and write Red Hat talks/speakers
    redhat_talks = filter_redhat_talks(talks)
    write_redhat_talks_to_csv(redhat_talks, REDHAT_TALKS_CSV)
    write_redhat_speakers_to_csv(redhat_talks, REDHAT_SPEAKERS_CSV)
    print(f"Found {len(redhat_talks)} talks with Red Hat speakers ({len(redhat_talks) / len(talks) * 100:.1f}% of total)")

    # Step 6: Print summary statistics
    print_statistics(talks)

    print("\nDone!")


if __name__ == "__main__":
    main()
