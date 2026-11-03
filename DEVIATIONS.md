# DEVIATIONS

## 2026-11-02 - Illustrative DST example corrected
- Where: PREREGISTRATION-ANALYSIS.md, Part B, Table 1 note ("Friday 17:00 London to Monday 09:00 London is 8.5 business hours, not 64").
- Issue: with the pre-registered London hours (09:00-17:30), that interval is 0.5 business hours. 8.5 hours applies from Friday 09:00.
- Effect: none. The example is illustrative; the rule, the hours table and all parameters are unchanged. The calendar code follows the pre-registered hours table, and tests cover both intervals.
- Found by: calendar-maths test run (deliverable 1).

## 2026-11-02 - Hold placement interpretation
- Where: Part B Table 3, "Hold ... attached by argmax of queue plus handoff in that scenario's table".
- Issue: wording does not say which component receives the hold. Applied Part B Section 9 item 6 ("attaches to each scenario's largest component"): A cells = step-5 queue (20.34 h), B cells = step-5 handoff (6.01 h).
- Effect: A cells unchanged; B cells' hold moved from step-5 queue to step-5 handoff. Classification correct in all four cells under both placements.

## 2026-11-02 - p95 acceptance band missed in A1 and A2
- Band: p95 calendar days 16-20 (Part B Section 1.4). Production build: A1 20.28, A2 20.18 (calibration run: 18.94, 17.78). B1 18.77, B2 18.34 within band.
- Not caused by hold placement (A-cell values identical under both placements). No parameters tuned.
- Effect on the pre-registered test: none. Pass condition (Part A Section 3.4) is classification, margin and no contradiction; all four cells pass. Reported as a reproduction difference between independent implementations.

## 2026-11-03 - Triage prompt rule inconsistent with the sample fixtures
- Where: `mcp/triage.py`, `_SYSTEM_RULES` (model instructions for exception triage). Not part of the pre-registered process-mining analysis.
- Issue: the rule said "a missing ... approval ... is 'escalate'", but three standard-tier samples with no prior approval (RQ-001, RQ-004, RQ-005) expect 'approve'. Found on the first real model call (gpt-5.4-mini-2026-03-17, RQ-001 returned 'escalate', following the rule as written). RQ-006 (embedded instruction) returned 'escalate', as expected.
- Change: the rule was corrected, not the fixtures. For standard tier with no conflict and no duplicate, a missing prior approval is not a reason to escalate, because a human confirms every grant; an expired or incomplete prior approval, a conflict, a duplicate, or a privileged request without a live, complete prior approval still escalates or rejects. Checked against all ten fixtures before re-running.
- Effect: the ten-sample evaluation runs on the corrected rule. Two smoke calls were made before the change (cost USD 0.000623 and 0.000661); they are not part of the evaluation.

## 2026-11-03 - Sample RQ-011 added after pre-registration
- Where: `mcp/sample_requests.json` and `mcp/data/prior_approvals.json`; Part B Table 4b pre-registers ten samples (RQ-001 to RQ-010).
- Issue: none of the ten privileged samples should be approved, so with a correct model the two-approver grant path is never reached in a real-model run (first evaluation, gpt-5.4-mini-2026-03-17, 3 repeats: 9/9 recommendations and 10/10 gate outcomes per repeat, 0 two-approver grants).
- Change: added RQ-011 (ci-pipeline-admin, privileged, prior approval 30 of 180 days, manager and app owner confirmed, no conflict, no duplicate; expected approve, granted only after two different approvers). The ten pre-registered samples and their expectations are unchanged.
- Effect: `eval_samples.py` scores the pre-registered ten and the added sample separately; the pre-registered result is reported first and is never combined with RQ-011.

## 2026-11-03 - Triage rule v2: one outcome per condition
- Where: `mcp/triage.py`, `_SYSTEM_RULES`; `RULES_VERSION` set to `v2` and written into every evaluation result.
- Issue: rule v1.1 said an expired or incomplete approval, a conflict, a duplicate or a privileged request without approval "is 'escalate' or 'reject'", so it allowed either outcome. Run `20261103T081934Z` (rules v1.1, gpt-5.4-mini-2026-03-17, 3 repeats) returned 'reject' for RQ-007 (SoD conflict, expected 'escalate') in one repeat: pre-registered ten 26/27 recommendations, 30/30 gate outcomes; RQ-011 3/3 and 3/3. The gate outcome was correct in every case (no grant).
- Change: each condition now maps to one outcome - 'reject' only for a duplicate; 'escalate' for expired or incomplete approval, a conflict, or a privileged request without a live, complete approval; 'approve' otherwise as before; precedence reject > escalate > approve. Checked against all eleven fixtures; no fixture changed.
- Effect: v1.1 results stand as reported and are not replaced. v2 runs are reported separately, labelled by `rules_version`.

## 2026-11-03 - PM4Py cross-check added after pre-registration
- Where: `analysis/pm4py_crosscheck.py`, `analysis/results/pm4py_crosscheck.json`, `lean/as_is_discovered_A2.bpmn`. The pre-registered analysis (Part A) uses pandas; PM4Py was optional in the build brief and not used in the original run.
- Change: added an exploratory cross-check with PM4Py 2.7.23.11 - Inductive Miner (noise threshold 0) discovery per cell, alignment-based fitness against the designed 8-step path, and precision of the discovered model.
- Effect: none on the pre-registered result. The share of fitting traces against the designed path equals the pandas exact-path conformance rate in all four cells (0.9445, 0.774, 0.9435, 0.771).
