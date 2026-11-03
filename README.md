# Synthetic access-flow mining case study

All data and results are synthetic. This repository demonstrates process mining of a technology access-provisioning workflow, tests an owner-classification method, and models potential intake-validation automation value. The estimates do not describe a real organization or operational process.

## Repository map

`src/flowmining/` mining, classifier and value model · `analysis/` scripts, results, hand-trace and PM4Py cross-check · `data/` synthetic event logs and calendar · `mcp/` reference-data server, triage gate and evaluation · `lean/` BPMN, value stream map, control plan · `uipath/IntakeValidationBot/` intake-validation bot · `tests/` pytest suite.

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

The four cells classify as intended: A1 and A2 are APPROVER-BOUND, B1 and B2 are HANDOFF-BOUND, with margins 4.11, 4.02, 8.21, and 8.10. The A-cell p95 calendar times are 20.28 and 20.18 days and MISS the registered 16–20 day band; B1 and B2 are 18.77 and 18.34 days and PASS. These results are reported without tuning. Hold interpretation and the reproduction difference are recorded in `DEVIATIONS.md`.

The hold-removed analysis classifies all four cells correctly. The jitter analysis classifies 20 of 20 cell-runs correctly with margin, ranging from 3.46 to 8.73. The synthetic value model reports payback of 9.86 months and 36-month NPV of `$21,927`.

## How to run the bot

Open `uipath/IntakeValidationBot/project.json` in UiPath Studio and press **F5**. The sample workflow reads `Data/intake_requests.csv` and `Data/entitlements.csv`, then writes `Output/valid.csv` and `Output/returned.csv`. The included fixture run has 12 valid and 8 returned requests out of 20; this is a synthetic demonstration.

## Exception triage gate

`mcp/triage.py` uses the model for a recommendation only; a human gate decides, with one confirmation for standard entitlements and two from different approvers (neither the requester) for privileged ones (RQ-002 and RQ-006 to RQ-010 of the ten pre-registered samples, plus RQ-011, added later and scored separately), refuses unregistered entitlements before any model call, logs every blocked attempt, and executes each request at most once (`tests/test_gate.py`).

## Triage evaluation (real model, optional)

`python -m pytest` needs no API key: the gate and evaluation tests use fake models. To run the real-model evaluation, copy `.env.example` to `.env`, fill in the key and the two prices, then:

```powershell
python mcp/smoke_openai.py RQ-001   # one call, no gate, no audit log
python mcp/eval_samples.py          # all samples, 3 repeats, stops above USD 0.05
```

Each run writes `mcp/runs/<UTC stamp>/` (git-ignored): one audit log per repeat and `results.json`, which records `rules_version`. The ten pre-registered samples and RQ-011 are scored separately. Results by run are in `FINDINGS.md`; rule changes are in `DEVIATIONS.md`.

## Intake-validation bot (UiPath)

Open `uipath/IntakeValidationBot/project.json` in UiPath Studio (Community edition, VB.NET expressions) and run `Main.xaml`. It reads `Data/intake_requests.csv` (20 synthetic requests), applies five rules (required fields, registered entitlement, manager distinct from requester, justification of at least 20 characters, no duplicate request), and writes `Output/valid.csv` (12 rows) and `Output/returned.csv` (8 rows, each with every rule it failed). It is a demonstration on fixtures, not a production control.

## Limits

The model uses fixed queue parameters rather than staffing capacity, a sequential path, at most two rework loops, weekends but no public holidays, and one process represented by four parameter scenarios. The hold reinforces the planted owner signal by design. See `CASE_STUDY.md` and Part B §9 of the pre-registration for the full limitations.

PM4Py used: yes, as an exploratory cross-check only (`analysis/pm4py_crosscheck.py`: Inductive Miner discovery and alignment-based conformance). The pre-registered analysis uses pandas. PM4Py is an optional dependency (`requirements-optional.txt`, AGPL-3.0 licence); it is imported only by the cross-check script.

Repository map: `src/` contains the analysis package; `analysis/` scripts and saved results; `data/` synthetic inputs; `lean/` BPMN diagrams and control plan; `mcp/` the policy-data server and triage demonstration; `uipath/IntakeValidationBot/` the attended intake-validation workflow.
