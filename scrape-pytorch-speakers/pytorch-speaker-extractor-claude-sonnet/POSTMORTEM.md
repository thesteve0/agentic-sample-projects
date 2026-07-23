# Postmortem: Wrong Company Extraction Approach

## What Went Wrong

The initial code extracted speaker company affiliations from the wrong field in the Sessionize API response, producing dirty values like `"Machine Learning Engineer"`, `"Meta FAIR"`, and `"Applied Scientist at Amazon Ads | Secure Agentic AI & Multi-Agent Systems"` instead of clean company names.

## Root Cause

The Sessionize API returns speaker records with several fields. Without carefully inspecting the full data structure, I reached for the most obviously named field — `tagLine` — and assumed it contained the company name:

```json
{
  "fullName": "Aaresh Sharma",
  "tagLine": "Sr. Specialist SA - Containers",
  ...
}
```

`tagLine` is a free-form bio field that speakers fill in however they like. Its contents varied wildly:

| tagLine value | Problem |
|---|---|
| `"Machine Learning Engineer"` | Job title only, no company |
| `"Open Source AI @ Meta FAIR"` | Role + team, not canonical company |
| `"Applied Scientist at Amazon Ads | Secure Agentic AI & Multi-Agent Systems"` | Role + org unit, not company |
| `"AMD"` | Clean — but this was the exception |

## The Wrong Fix

Rather than inspect the API response more carefully, I compounded the mistake by writing a regex/heuristic `extract_company()` function to parse company names out of the tagLine strings. This produced inconsistent results and still leaked job titles into the company column. It was solving the wrong problem.

## The Correct Approach

The Sessionize API speaker record includes a `questionAnswers` array containing structured CFP form responses. For this event, question ID `128058` is explicitly the company name field — filled in by each speaker themselves:

```json
{
  "fullName": "Aaresh Sharma",
  "tagLine": "Sr. Specialist SA - Containers",
  "questionAnswers": [
    { "questionId": 128058, "answerValue": "Amazon Web Services" },
    { "questionId": 128059, "answerValue": "Sr. Specialist SA - Containers" }
  ]
}
```

Using `questionAnswers` gave clean, speaker-supplied company names with zero parsing required. The fix was a one-line lookup replacing the entire heuristic function:

```python
qa = {q["questionId"]: q["answerValue"] for q in sp.get("questionAnswers", [])}
company = (qa.get(QUESTION_COMPANY) or "").strip()  # QUESTION_COMPANY = 128058
```

## Impact

| Metric | Wrong (tagLine) | Correct (questionAnswers) |
|---|---|---|
| Unique "companies" | 74 | 52 |
| Meta count | 16 | 29 |
| AMD count | 5 | 5 |
| Junk values | Many | None |

## Lesson

When an API returns structured data, read the full response schema before writing parsing logic. The correct field (`questionAnswers`) was present all along — it just required inspecting a few complete records rather than grabbing the first plausible-looking field.
