#!/usr/bin/env python3
"""
Parse the PyTorch Ambassador Reviewer 10 XLSX workbook and output clean JSON.

Usage:
    python3 parse_xlsx.py > applicants.json
"""
import openpyxl
import json
import sys

# Load the workbook with data_only=True to get computed values
wb = openpyxl.load_workbook(
    'Shared_PyTorch_Ambassador_Reviewer_Workbook_2026.xlsx',
    data_only=True
)

# Find the "Reviewer 10" sheet
ws = None
for name in wb.sheetnames:
    if 'Reviewer 10' in name:
        ws = wb[name]
        break

if not ws:
    print("Error: Could not find Reviewer 10 sheet", file=sys.stderr)
    sys.exit(1)

# Find header row
header_row, header_idx = None, None
for i, row in enumerate(ws.iter_rows(min_row=1, max_row=10, values_only=False), 1):
    for cell in row:
        if cell.value and 'Submission ID' in str(cell.value):
            header_row, header_idx = row, i
            break
    if header_idx:
        break

if not header_row:
    print("Error: Could not find header row", file=sys.stderr)
    sys.exit(1)

# Build normalized header mapping (normalize curly apostrophes and whitespace)
def norm(h):
    return h.replace('\n', ' ').replace('  ', ' ').strip()

raw_headers = [norm(str(cell.value)) for cell in header_row if cell.value]

# Parse applicant rows
applicants = []
for row in ws.iter_rows(min_row=header_idx + 1, values_only=True):
    if not row or not row[0]:
        continue
    try:
        app_id = int(float(row[0]))
    except (ValueError, TypeError):
        continue

    applicant = {'_id': app_id}
    for i, header in enumerate(raw_headers):
        if i >= len(row):
            break
        val = row[i]
        if val is None:
            applicant[header] = ''
        elif isinstance(val, (int, float)):
            applicant[header] = str(int(val)) if val == int(val) else str(val)
        elif isinstance(val, str):
            applicant[header] = val.replace('\r', '').strip()
        else:
            applicant[header] = str(val)

    applicants.append(applicant)

# Output JSON
print(json.dumps(applicants, indent=2, ensure_ascii=False))
print(f"Parsed {len(applicants)} applicants", file=sys.stderr)
