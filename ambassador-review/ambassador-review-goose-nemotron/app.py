#!/usr/bin/env /home/linuxbrew/.linuxbrew/bin/python3
"""PyTorch Ambassador Reviewer Scoring Application.

A simple HTML web app that loads locally on Linux for reviewing ambassador
applications and scoring them against the 8-review-question rubric.

Features:
- Load .xlsx reviewer workbook
- Display one applicant at a time
- 8 question scoring (1-5 scale) with radio buttons
- Auto-calculate total score (8-40) and recommendation
- Save scores and notes to JSON between sessions
- Navigate through all assigned applicants via URL parameters
"""

import json
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify, session

# Configuration
XLSX_FILE = "Shared_PyTorch_Ambassador_Reviewer_Workbook_2026.xlsx"
SHEET_NAME = "Reviewer 10"
SCORES_FILE = "scores.json"
NUM_QUESTIONS = 8
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Try to load the workbook - do this at module level since it's read-only
import openpyxl
try:
    wb = openpyxl.load_workbook(os.path.join(APP_DIR, XLSX_FILE))
    if SHEET_NAME not in wb.sheetnames:
        print(f"Error: Sheet '{SHEET_NAME}' not found in {XLSX_FILE}")
        print(f"Available sheets: {wb.sheetnames}")
        sys.exit(1)
    ws = wb[SHEET_NAME]
    print(f"Loaded {SHEET_NAME} sheet with {ws.max_row - 4} applicants")
except ImportError:
    print("Error: openpyxl not installed. Install with: pip3 install --break-system-packages openpyxl")
    sys.exit(1)
except FileNotFoundError:
    print(f"Error: File {XLSX_FILE} not found in {APP_DIR}")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = 'pyTorchAmbassador2026Review!'


def get_row_data(row_num):
    """Get applicant data from row number (1-indexed, row 5 = first applicant)."""
    # Columns A=1, B=2, ... through to column 34
    fields = {
        1: "submission_id",
        2: "issue_url",
        3: "github_username",
        4: "nominee_name",
        5: "current_location",
        6: "years_community",
        7: "github_profile",
        8: "personal_website",
        9: "gitlab_profile",
        10: "linkedin_profile",
        11: "twitter_profile",
        12: "other_specify",
        13: "other_project_name",
        14: "community_contributions",
        15: "pyro_contributions",
        16: "ambition_motivation",
        17: "ambassador_contributions",
        18: "ambassador_focus_areas",
        19: "primary_region",
        20: "primary_country",
        21: "additional_info",
    }

    data = {}
    for col, field in fields.items():
        cell = ws.cell(row=row_num, column=col).value
        if cell is not None:
            data[field] = str(cell).replace('\n', ' ').strip()
        else:
            data[field] = ""

    # Load existing scores for this row
    scores = []
    for q in range(1, NUM_QUESTIONS + 1):
        score_col = 22 + q  # cols 23-30 for questions 1-8
        cell_val = ws.cell(row=row_num, column=score_col).value
        if cell_val is not None and isinstance(cell_val, (int, float)) and 1 <= cell_val <= 5:
            scores.append(int(cell_val))
        else:
            scores.append(1)  # default

    data['scores'] = scores

    # Load existing recommendation
    rec_col = 32
    rec_cell = ws.cell(row=row_num, column=rec_col).value
    data['recommendation'] = str(rec_cell).strip() if rec_cell else ""

    # Load existing comments
    comm_col = 33
    comm_cell = ws.cell(row=row_num, column=comm_col).value
    data['comments'] = str(comm_cell).strip() if comm_cell else ""

    return data


def get_all_applicants():
    """Get all applicant data rows."""
    applicants = []
    # Data starts at row 5 (first applicant), row 4 is header
    for r in range(5, ws.max_row + 1):
        # Check if this row has a submission ID
        sub_id = ws.cell(row=r, column=1).value
        if sub_id is None:
            continue
        applicant = get_row_data(r)
        applicant['row_num'] = r
        applicants.append(applicant)
    return applicants


def save_scores():
    """Save current scores to JSON file."""
    all_data = get_all_applicants()
    save_data = {}
    for applicant in all_data:
        sub_id = applicant['submission_id']
        save_data[sub_id] = {
            'scores': applicant['scores'],
            'comments': applicant.get('new_comments', applicant['comments']),
            'recommendation': applicant.get('new_recommendation', applicant['recommendation']),
        }
    with open(os.path.join(APP_DIR, SCORES_FILE), 'w') as f:
        json.dump(save_data, f, indent=2)


def load_saved_scores():
    """Load previously saved scores from JSON file."""
    if not os.path.exists(os.path.join(APP_DIR, SCORES_FILE)):
        return

    with open(os.path.join(APP_DIR, SCORES_FILE), 'r') as f:
        saved = json.load(f)

    all_data = get_all_applicants()
    for applicant in all_data:
        sub_id = applicant['submission_id']
        if sub_id in saved:
            applicant['scores'] = saved[sub_id].get('scores', [1] * NUM_QUESTIONS)
            applicant['comments'] = saved[sub_id].get('comments', applicant['comments'])
            applicant['recommendation'] = saved[sub_id].get('recommendation', applicant['recommendation'])


def calculate_recommendation(total_score):
    """Determine recommendation based on total score."""
    if total_score >= 32:
        return "Strongly Recommend"
    elif total_score >= 24:
        return "Recommend"
    elif total_score >= 16:
        return "Borderline"
    else:
        return "Do Not Recommend"


@app.route('/', methods=['GET', 'POST'])
def index():
    """Main page - displays applicant and handles scoring."""
    # Get navigation parameter from URL
    nav = request.args.get('nav', type=int)

    # Load applicants on first visit or re-initialize
    if 'applicants' not in session or request.args.get('reset') == 'true':
        all_applicants = get_all_applicants()
        load_saved_scores()
        session['applicants'] = all_applicants
        session['current'] = 0
    else:
        all_applicants = session['applicants']

    # Apply navigation
    if nav is not None:
        current = session['current'] + nav
        if len(all_applicants) > 0:
            current = max(0, min(current, len(all_applicants) - 1))
        session['current'] = current

    current_idx = session['current']
    applicant = all_applicants[current_idx] if all_applicants else {}

    # Handle form submission
    if request.method == 'POST':
        # Save scores for current applicant
        scores = []
        for q in range(1, NUM_QUESTIONS + 1):
            score = request.form.get(f'q{q}')
            if score and score.isdigit():
                s = int(score)
                if 1 <= s <= 5:
                    scores.append(s)
                else:
                    scores.append(applicant['scores'][q - 1] if applicant.get('scores') else 1)
            else:
                scores.append(applicant['scores'][q - 1] if applicant.get('scores') else 1)

        applicant['scores'] = scores
        applicant['new_comments'] = request.form.get('comments', '').strip()
        applicant['new_recommendation'] = request.form.get('recommendation', '').strip()

        # Calculate total and recommendation
        total = sum(scores)
        applicant['total_score'] = total
        applicant['recommendation'] = calculate_recommendation(total)

        # Save to file
        save_scores()

        # Reload applicants with updated data from file
        session['applicants'] = get_all_applicants()

        # Navigate if requested
        redirect_to = request.form.get('redirect_to')
        if redirect_to == 'next':
            session['current'] = min(current_idx + 1, len(session['applicants']) - 1)
        elif redirect_to == 'prev':
            session['current'] = max(current_idx - 1, 0)
        elif redirect_to == 'reset':
            if os.path.exists(os.path.join(APP_DIR, SCORES_FILE)):
                os.remove(os.path.join(APP_DIR, SCORES_FILE))
            session['applicants'] = get_all_applicants()
            session['current'] = 0
            return redirect(url_for('index'))

        # Redirect with navigation preserved via session;
        # also redirect with nav param so URL reflects the new position
        new_nav = 1 if redirect_to == 'next' else (-1 if redirect_to == 'prev' else None)
        return redirect(url_for('index', nav=new_nav))

    # Calculate total and recommendation for display
    total = sum(applicant['scores']) if applicant.get('scores') else 0
    applicant['total_score'] = applicant.get('total_score', total)
    applicant['recommendation'] = applicant.get('recommendation', calculate_recommendation(total))

    total_applicants = len(all_applicants) if all_applicants else 0

    return render_template(
        'index.html',
        applicant=applicant,
        all_applicants=all_applicants,
        current_index=current_idx,
        total_score=applicant.get('total_score', total),
        recommendation=applicant.get('recommendation', ''),
        num_questions=NUM_QUESTIONS,
        total_applicants=total_applicants,
    )


@app.route('/nav/<int:direction>')
def navigate(direction):
    """Navigate applicants via URL parameter - delegates to index with nav param."""
    return redirect(url_for('index', nav=direction))


@app.route('/reset')
def reset_all():
    """Reset all scores and start fresh."""
    if os.path.exists(os.path.join(APP_DIR, SCORES_FILE)):
        os.remove(os.path.join(APP_DIR, SCORES_FILE))
    session.pop('applicants', None)
    session.pop('current', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    # Remove old scores file to start fresh
    if os.path.exists(os.path.join(APP_DIR, SCORES_FILE)):
        os.remove(os.path.join(APP_DIR, SCORES_FILE))

    print(f"\n=== PyTorch Ambassador Reviewer App ===")
    print(f"Loaded applicant data from {SHEET_NAME}")
    print(f"Open your browser to: http://127.0.0.1:5000/")
    print(f"Navigation: Add ?nav=1 (next) or ?nav=-1 (prev) to URL")
    print(f"Press Ctrl+C to stop the server\n")

    app.run(host='0.0.0.0', port=5000, debug=False)