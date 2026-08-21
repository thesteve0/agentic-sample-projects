# PyTorch Ambassador Review Tool — Model Evaluation Plan

## Goal

Compare three models via Goose on the same task: build a better format for reviewing PyTorch Ambassador Program applicants. The applicant data is currently in a Google Sheet with small font and poor readability. The tool needs to present applicant info clearly and support scoring each candidate against a rubric with reasons.

## Models Under Evaluation

| Model | Directory |
|---|---|
| QWen (baseline) | `ambassador-review-goose-qwen/` |
| Meta Glimmer | `ambassador-review-goose-glimmer/` |
| NVIDIA Nemotron Lightning | `ambassador-review-goose-nemotron/` |

## Input Files (in this directory)

- Applicant data CSV exported from the Google Sheet
- Rubric document describing how to evaluate each applicant

## Evaluation Approach

**Conversational** — iterate with each model until the output is usable or you hit the turn cap. Use the same initial prompt for all three models.

### Protocol

1. Write the initial prompt once and paste it verbatim into each Goose session
2. Use the same types of follow-up guidance across models — if one model gets "the font is too small, fix it," give the same correction to the others if they make the same mistake
3. Cap at 8-10 conversational turns per model so no model gets infinite chances
4. Score all three models after all runs are complete (not during) to avoid anchoring bias

## Scoring

3-point scale for all dimensions: **Good / Neutral / Bad**

| Dimension | Good | Neutral | Bad |
|---|---|---|---|
| **Autonomy** | 0-1 follow-ups beyond initial prompt | 2-3 follow-ups | 4+ or went in circles |
| **Correctness** | Runs first try, loads all data | Runs with minor fixes | Broken or missing data |
| **Completeness** | All features: layout, scoring, rubric, reasons | Most features present | Missing core features |
| **Usability** | Would actually use this to review applicants | Functional but clunky | Wouldn't use it |
| **UI/Design** | Readable, good info density, solves the Sheets problem | Marginal improvement over the sheet | Same or worse than the sheet |
| **Error Recovery** | Self-corrected cleanly | Recovered with a nudge | Spiraled or gave up |
| **Code Quality** | Clean, reasonable stack | Messy but functional | Unmaintainable or wrong stack |

## MLFlow Organization

Traces are captured automatically via Goose's OTEL export to the MLFlow 3.10.1 server.

### Experiments

One experiment per model, named to match the directory structure:

- `ambassador-review-goose-qwen`
- `ambassador-review-goose-glimmer`
- `ambassador-review-goose-nemotron`

### Scoring in MLFlow

After all three runs are complete, attach assessments to each model's traces using either:

- The MLFlow UI (open trace → Assessments → annotate)
- `mlflow.log_feedback()` with `source_type=HUMAN`

Log one assessment per scoring dimension per trace, using the dimension name (e.g., `autonomy`, `correctness`) as the feedback name and `good`/`neutral`/`bad` as the value. Include a rationale for each score.

### Comparison

Use MLFlow's Evaluation Comparison UI to compare across experiments at the summary level.
