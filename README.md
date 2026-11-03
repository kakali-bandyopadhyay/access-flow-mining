# Synthetic access-flow mining case study

All data and results are synthetic. This repository demonstrates process mining of a technology access-provisioning workflow, tests an owner-classification method, and models potential intake-validation automation value. The estimates do not describe a real organization or operational process.

## Setup

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest
```

For macOS or Linux, activate with `source .venv/bin/activate`.

## Pre-registration

Commit: `2e2f58cfe2a12acb79f9d9cf1fddfb22807e14a5`  
SHA-256 of `PREREGISTRATION-ANALYSIS.md`: `8B2064C477F1022AC9DF69364C56B88C0B502C1AECBD3D1DBBA626F0064323CF`.

## Synthetic results

The four cells classify as intended: A1 and A2 are APPROVER-BOUND, B1 and B2 are HANDOFF-BOUND. Their margins are `4.109527601495121`, `4.021267557523499`, `8.214814129250245`, and `8.104614825487483`. The two A-cell p95 calendar times are `20.28373032407407` and `20.17682291666665` days and miss the registered `16–20` day band; B1 and B2 are `18.77213599537037` and `18.339107638888883` days. These are reported without tuning. Hold interpretation and this reproduction difference are recorded in `DEVIATIONS.md`.

The hold-removed analysis classifies all four cells correctly; the jitter analysis classifies `20` of `20` cases correctly with margin, ranging from `3.455609557239851` to `8.730539725279423`. The synthetic value model reports payback of `9.86477688185506` months and 36-month NPV of `$21926.738826523913`.

## Exception triage gate

`mcp/triage.py` uses the model for a recommendation only; a human gate decides, with one confirmation for standard entitlements and two from different approvers (neither the requester) for privileged ones (RQ-002 and RQ-006 to RQ-010 of the ten pre-registered samples, plus RQ-011, added later and scored separately), refuses unregistered entitlements before any model call, logs every blocked attempt, and executes each request at most once (`tests/test_gate.py`).

## Triage evaluation (real model, optional)

`python -m pytest` needs no API key: the gate and evaluation tests use fake models. To run the real-model evaluation, copy `.env.example` to `.env`, fill in the key and the two prices, then:

```powershell
python mcp/smoke_openai.py RQ-001   # one call, no gate, no audit log
python mcp/eval_samples.py          # all samples, 3 repeats, stops above USD 0.05
```

Each run writes `mcp/runs/<UTC stamp>/` (git-ignored): one audit log per repeat and `results.json`, which records `rules_version`. The ten pre-registered samples and RQ-011 are scored separately. Results by run are in `FINDINGS.md`; rule changes are in `DEVIATIONS.md`.

## Limits

The model uses fixed queue parameters rather than staffing capacity, a sequential path, at most two rework loops, weekends but no public holidays, and one process represented by four parameter scenarios. The hold reinforces the planted owner signal by design. See `CASE_STUDY.md` and Part B §9 of the pre-registration for the full limitations.

PM4Py used: no. Variants are computed with pandas.
