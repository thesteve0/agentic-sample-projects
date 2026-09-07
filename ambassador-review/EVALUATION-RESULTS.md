# PyTorch Ambassador Review Tool — Evaluation Results

**Date:** 2026-08-26
**Evaluator:** stpousty

## Final Scores

| Dimension | QWen 3.6 35b | Meta Glimmer | NVIDIA Nemotron Lightning |
|---|---|---|---|
| **Autonomy** | Neutral | Good | Bad |
| **Correctness** | Bad | Good | Bad |
| **Completeness** | Neutral | Good | Neutral |
| **Usability** | Neutral | Good | Bad |
| **UI/Design** | Good | Good | Good |
| **Error Recovery** | Neutral | Good | Bad |
| **Code Quality** | Bad | Good | Bad |

## Score Rationales

### QWen 3.6 35b

- **Autonomy: Neutral** — Only 4 conversational turns, but ran extremely long autonomous loops (72 LLM calls in one turn, 25 min). Low interaction despite few turns.
- **Correctness: Bad** — Silent data loss. Saves free text fields but drops numeric scores. Worse than a visible error because the reviewer might not notice until after reviewing multiple applicants.
- **Completeness: Neutral** — All features present in the UI (scoring, navigation, rubric display) but save functionality broken for numeric scores.
- **Usability: Neutral** — Looks nice and feels usable, but cannot trust it with data.
- **UI/Design: Good** — Clean dark theme, good layout, solved the readability problem visually.
- **Error Recovery: Neutral** — Bug was not caught during the session so no iteration occurred. Scored neutral rather than N/A because the model didn't self-test its save functionality.
- **Code Quality: Bad** — Save function silently drops half the data. Standalone HTML approach was correct but implementation buggy.

### Meta Glimmer

- **Autonomy: Good** — 11 focused conversational turns across 2 sessions. Natural iteration pattern with scoped work per turn.
- **Correctness: Good** — Runs correctly, loads all data, scoring and save work. Used for actual ambassador reviews of all 25 applicants.
- **Completeness: Good** — All features present and working: layout, scoring, rubric reference, navigation, reviewer comments.
- **Usability: Good** — Actually used this tool to complete the real ambassador review task.
- **UI/Design: Good** — Clean readable layout, good info density, clearly solves the Google Sheets readability problem.
- **Error Recovery: Good** — Iterated across two sessions and converged to a working solution.
- **Code Quality: Good** — Standalone HTML (248 lines) with no server dependencies. Clean and maintainable.

### NVIDIA Nemotron Lightning

- **Autonomy: Bad** — Many iterations across multiple turns and the navigation issue was never resolved.
- **Correctness: Bad** — App loads but cannot navigate between applicants. Tested in both Firefox and Edge with same result.
- **Completeness: Neutral** — All features were present in the UI (scoring, rubric, navigation controls, comments) but the implementation was broken for navigation across multiple applicants.
- **Usability: Bad** — Cannot complete the review task if you can't navigate applicants.
- **UI/Design: Good** — The UI itself was well-designed with all the features needed, but non-functional.
- **Error Recovery: Bad** — Spiraled across many turns without fixing the navigation bug.
- **Code Quality: Bad** — Chose Flask (Python server + templates) when a standalone HTML file would have worked. Overengineered architecture that still produced a broken result.

**Note:** Nemotron traces were not captured in MLFlow (OTEL export failed). Assessments could not be attached to traces. Scores are based on the evaluator's direct experience with the tool.

## Quantitative Trace Data

### QWen 3.6 35b (Experiment 3)

| Turn | Time | Duration | LLM Calls | Tool Execs | Input Tokens | Output Tokens |
|---|---|---|---|---|---|---|
| 1 | 2026-08-17 20:16 | 1.6m | 8 | 14 | 227,853 | 9,357 |
| 2 | 2026-08-18 13:50 | 23.3m | 43 | 42 | 4,738,108 | 99,704 |
| 3 | 2026-08-18 14:14 | 25.7m | 72 | 47 | 9,490,674 | 106,587 |
| 4 | 2026-08-18 16:29 | 10.3m | 50 | 0 | — | — |
| **Total** | | **60.9m** | **173** | **103** | **14,456,635** | **215,648** |

Turn 4 was stuck IN_PROGRESS (50 chat spans, 0 tool executions, no token data recorded).

### Meta Glimmer (Experiment 4)

| Turn | Time | Duration | LLM Calls | Tool Execs | Input Tokens | Output Tokens |
|---|---|---|---|---|---|---|
| 1 | 2026-08-18 22:58 | 12.8m | 16 | 15 | 692,010 | 15,597 |
| 2 | 2026-08-19 12:10 | 13.1m | 20 | 19 | 694,005 | 16,263 |
| 3 | 2026-08-19 13:28 | 4.6m | 4 | 3 | 223,902 | 5,958 |
| 4 | 2026-08-19 13:56 | 23.3m | 6 | 5 | 391,776 | 6,150 |
| 5 | 2026-08-19 16:29 | 20.4m | 10 | 0 | 53,043 | 1,122 |
| 6 | 2026-08-19 16:52 | 7.8m | 13 | 12 | 532,173 | 7,458 |
| 7 | 2026-08-19 17:10 | 6.1m | 5 | 4 | 342,948 | 7,806 |
| 8 | 2026-08-19 18:02 | 5.3m | 3 | 2 | 253,296 | 2,862 |
| 9 | 2026-08-19 18:30 | 0.1m | 1 | 0 | — | — |
| 10 | 2026-08-19 18:31 | 3.3m | 1 | 0 | 74,037 | 3,912 |
| 11 | 2026-08-19 18:36 | 12.5m | 6 | 5 | 407,259 | 16,428 |
| **Total** | | **109.3m** | **85** | **65** | **3,664,449** | **83,556** |

### Head-to-Head

| Metric | QWen 3.6 35b | Meta Glimmer |
|---|---|---|
| Conversational turns | 4 | 11 |
| Total wall-clock time | 60.9m | 109.3m |
| Total LLM calls | 173 | 85 |
| Total tool executions | 103 | 65 |
| Total tokens | 14,672,283 | 3,748,005 |
| Avg tokens per turn | 3,668,070 | 340,727 |
| Avg time per turn | 15.2m | 9.9m |
| **Outcome** | **Broken (silent bug)** | **Working (used IRL)** |

QWen consumed ~4x more tokens to produce a broken result. Glimmer took more wall-clock time overall (more turns of human interaction) but each turn was smaller and more focused.

## MLFlow Assessment Locations

- **QWen assessments:** Attached to trace `tr-513aedc056c8a9c6ffbd06b79b3fd749` in experiment 3
- **Glimmer assessments:** Attached to trace `tr-ec1d38df9e5f9a65d73ba63d3a590f97` in experiment 4
- **Nemotron assessments:** Not in MLFlow (no traces captured). Scores documented in this file only.

## Summary

**Winner: Meta Glimmer** — The only model that produced a working tool. Scored Good on all 7 dimensions. Efficient token usage (3.7M total) with a natural conversational iteration pattern.

**QWen 3.6 35b** produced a polished-looking but fundamentally broken tool. The silent data loss bug (saves text but drops scores) is the most dangerous failure mode — it looks like it works until you realize your data is incomplete. It also consumed 4x the tokens of Glimmer.

**NVIDIA Nemotron Lightning** overengineered the solution with a Flask server when a standalone HTML file would have sufficed, and the result was visibly broken. Despite many iterations, it never fixed the navigation bug. The UI design itself was good, but it never reached a usable state. Traces were also not captured, limiting evaluation.
