# Readiness scoring

The score and label are pure functions of the saved validation results. Gemini output is never an input. Tune the numbers in `backend/app/report/scoring.py`.

## Constants

| Name | Default | Meaning |
| --- | --- | --- |
| `FAIL_PENALTY` | 40 | Subtracted from one document for each of its fail results |
| `WARNING_PENALTY` | 10 | Subtracted from one document for each of its warning results |
| `CROSS_FAIL_PENALTY` | 15 | Subtracted from the overall score for each application-level fail |
| `CROSS_WARNING_PENALTY` | 5 | Subtracted from the overall score for each application-level warning |
| `MANDATORY_WEIGHT` | 2 | Weight of a mandatory document in the average |
| `OPTIONAL_WEIGHT` | 1 | Weight of an optional document in the average |
| `READY_MIN_SCORE` | 85 | Lowest score that can be labelled ready |
| `ALMOST_READY_MIN_SCORE` | 60 | Lowest score that can be labelled almost ready |

A missing-document fail is already a 0 on that slot, so it is not also a cross-document penalty.

## Document score

Start at 100. Subtract `FAIL_PENALTY` for each fail and `WARNING_PENALTY` for each warning on that file. Floor at 0.

- Mandatory slot with no file: **0**
- Optional slot with no file: **excluded** from the average
- A file that is still `uploaded` or `processing` is not scored. The report endpoint returns HTTP 409 instead.

## Overall score

Weighted average of the document scores, then subtract cross-document penalties, floor at 0, round to an integer from 0 to 100.

## Label

- **ready** only if there are zero fail results anywhere, no missing mandatory document, and score ≥ `READY_MIN_SCORE`
- **almost_ready** if there is no missing mandatory document, at most two fails in total, and score ≥ `ALMOST_READY_MIN_SCORE`
- otherwise **not_ready**

A fail or a missing mandatory document can never be labelled ready.

## Worked example A – mixed documents

Three files: mandatory photo with one fail (60, weight 2), mandatory ID with no issues (100, weight 2), optional extra with one warning (90, weight 1).

Average = (60×2 + 100×2 + 90×1) / (2+2+1) = 410 / 5 = **82**.

One fail, nothing missing, 82 ≥ 60 → **almost_ready**.

## Worked example B – warnings plus a cross-document fail

Two mandatory documents at 100. One application-level name-match fail.

Average = 100. Minus `CROSS_FAIL_PENALTY` 15 → **85**.

There is still a fail, so the label is **not_ready**, not ready.

## How to tune

Edit the constants at the top of `backend/app/report/scoring.py`. Re-run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q tests/test_report.py
.\.venv\Scripts\python.exe scripts\report_demo.py
```
