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
