# PyTorch Ambassador Program Reviewer Scoring Application

## Overview
A lightweight HTML web application for reviewing PyTorch Foundation Ambassador Program applicants and scoring them against the official 8-review-question rubric. Runs locally on your Linux machine.

## Files Created
- `app.py` - Flask application with all scoring logic
- `templates/index.html` - HTML interface with radio button scoring
- `scores.json` - Persistent storage (created at runtime)
- `instructions.md` - This file (you are here)

## Quick Start

### 1. Start the Application
Open a terminal and run:

```bash
cd /var/home/stpousty/git/agentic-sample-projects/ambassador-review
/home/linuxbrew/.linuxbrew/bin/python3 app.py
```

### 2. Open Your Browser
Navigate to: 
- `http://127.0.0.1:5000/` for localhost-only access
- Or use the machine's local IP address (e.g., `http://192.168.x.x:5000`) to access from other devices on the same network

**Note:** The app now binds to `0.0.0.0` to accept connections from outside localhost. To restrict back to localhost only, change `host='0.0.0.0'` back to `host='127.0.0.1'` in `app.py`.

### 3. Access from Other Machines
On the same network, other devices can access the app at `http://<this-machine's-IP>:5000/`

The server will display "Applicant 1 of 25" and show the first applicant's information.

## Application Workflow

### Reviewing Applicants

1. **Read applicant information** displayed at the top of the page:
   - Submission ID and nominee name
   - Current location, years of community involvement
   - Primary region and country
   - GitHub profile link
   - PyTorch projects they're familiar with
   - Community contributions summary
   - Ambassador focus areas
   - Additional information

2. **Score each of the 8 review questions** (1-5 scale):
   - Question 1: Meaningful engagement with PyTorch Foundation projects or communities
   - Question 2: Measurable impact through technical contributions, community engagement, documentation, education, mentorship, or advocacy
   - Question 3: Active support, mentorship, education, or organization of community activities
   - Question 4: Help others learn, participate, contribute, or build community
   - Question 5: Clear, realistic, and achievable plan for Ambassador activities
   - Question 6: Proposed activities likely to create meaningful value for PyTorch Foundation projects and communities
   - Question 7: Ability to communicate technical concepts effectively
   - Question 8: Knowledge, engagement, and communication skills to represent PyTorch Foundation as Ambassador

3. **Select a score** by clicking the radio button (1-5) for each question

4. **Enter Reviewer Comments** in the text area provided

5. **Select a Recommendation**:
   - Strongly Recommend (32-40 total score)
   - Recommend (24-31 total score)
   - Borderline (16-23 total score)
   - Do Not Recommend (8-15 total score)

6. **Click "Save & Next"** to save your scores and move to the next applicant

### Navigation

- **Next applicant**: Click "Save & Next" or add `?nav=1` to the URL
- **Previous applicant**: Use `?nav=-1` in the URL
- **Reset all scores**: Add `?reset=1` to the URL to start fresh
- **Jump to specific applicant**: Modify the URL navigation parameters

## Scoring System

### Score Calculation
- Each of the 8 questions is scored 1-5
- **Total score** ranges from 8 (minimum) to 40 (maximum)
- Recommendation is automatically calculated based on the total:

| Total Score | Recommendation |
|-------------|----------------|
| 32-40 | Strongly Recommend |
| 24-31 | Recommend |
| 16-23 | Borderline |
| 8-15 | Do Not Recommend |

### Rubric Reference
Scores are based on the PyTorch Foundation Ambassador Program 2026 Reviewer Guide:
- **1**: Limited Evidence - Little or no relevant evidence
- **2**: Emerging Contributor - Some relevant evidence, early-stage or limited scope
- **3**: Solid Contributor - Clear evidence of meaningful contribution, consistent participation
- **4**: Strong Contributor - Substantial evidence of sustained contribution, notable impact, leadership
- **5**: Exceptional Contributor - Compelling evidence of exceptional depth, breadth, sustained impact

## Data Persistence

### scores.json
- All scores, comments, and recommendations are saved to `scores.json` in the application directory
- Data persists between sessions - you can close the browser and resume later
- The file is automatically updated when you click "Save & Next"
- To reset all scores and start fresh: add `?reset=1` to the URL or delete `scores.json`

### What's Saved Per Applicant
- 8 question scores (1-5)
- Reviewer comments
- Selected recommendation
- Total score and calculated recommendation

## Technical Requirements

### Already Installed on Your Linux Machine
- Python 3.14.6
- Flask web framework (v3.1.3)
- openpyxl for .xlsx reading (v3.1.5)

### No Additional Installation Needed
- No Streamlit required
- No pip install needed
- No database setup required

### Browser Requirements
- Any modern browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled for radio button functionality

## Customization

### Adding More Reviewers or Cycles
The application is designed for single-reviewer, single-cycle use. To adapt for:
- **Multiple reviewers**: Would require user authentication and score attribution
- **Different workbook format**: Modify the column mappings in `app.py` `get_row_data()` function
- **Different number of applicants**: The app dynamically detects the number of rows with submission IDs

### Changing the Workbook
The app reads from `Shared_PyTorch_Ambassador_Reviewer_Workbook_2026.xlsx`, sheet "Reviewer 10". To use a different:
- Replace the xlsx file in the directory with the same naming convention
- Or modify `XLSX_FILE` and `SHEET_NAME` constants in `app.py`

## Troubleshooting

### Common Issues

1. **Template not found error**:
   - Ensure `templates/` directory exists with `index.html`
   - The app was moved to run from the project root

2. **Port 5000 already in use**:
   - Stop any other Flask server or change the port in `app.py`
   - Or use a different port: `python3 app.py --port 5001` (would need minor modification)

3. **Scores not saving**:
   - Check that `scores.json` is being created in the directory
   - Ensure write permissions to the directory

4. **Application won't start**:
   - Verify the xlsx file exists: `Shared_PyTorch_Ambassador_Reviewer_Workbook_2026.xlsx`
   - Ensure you're in the correct directory
   - Check that openpyxl is installed: `python3 -c "import openpyxl"`

### Need Help?
- Check the Flask log output in the terminal for errors
- Verify the xlsx file format matches the expected structure (Reviewer 10 sheet)
- Ensure you have at least 25 applicants with submission IDs in the data range

## Closing the Application

- Press `Ctrl+C` in the terminal where the server is running
- Or close the browser window (the Flask process will continue running until stopped)
- Scores are already saved to `scores.json` before closure

## Next Steps

After reviewing all applicants:
1. All 25 applicants will be scored and saved
2. Use `scores.json` to review the collective results
3. The PyTorch Foundation program team will use reviewer evaluations alongside program priorities for final cohort composition