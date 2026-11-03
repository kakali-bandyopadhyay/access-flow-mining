# Synthetic findings

All results below are synthetic and read from `analysis/results/`, `mcp/runs/`, the UiPath sample outputs, or `DEVIATIONS.md`. They demonstrate the method and workflow; they are not operational evidence.

## Per-cell results

| Cell | Intended / classified | Margin | Approver share | Handoff share | Doer share | Wait share | Median days | p95 days | Loop rate | Breach rate | Defect rate | DPMO | Sigma before | Exact-path conformance |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | APPROVER-BOUND / APPROVER-BOUND | 4.11 | 77.86% | 18.95% | 3.19% | 96.23% | 6.03 | 20.28 | 4.00% | 27.55% | 30.30% | 303,000 | 2.02 | 94.45% |
| A2 | APPROVER-BOUND / APPROVER-BOUND | 4.02 | 77.52% | 19.28% | 3.21% | 96.24% | 6.34 | 20.18 | 18.00% | 29.35% | 40.65% | 406,500 | 1.74 | 77.40% |
| B1 | HANDOFF-BOUND / HANDOFF-BOUND | 8.21 | 10.51% | 86.34% | 3.15% | 96.29% | 5.96 | 18.77 | 4.00% | 21.00% | 23.85% | 238,500 | 2.21 | 94.35% |
| B2 | HANDOFF-BOUND / HANDOFF-BOUND | 8.10 | 10.61% | 86.01% | 3.38% | 96.04% | 6.08 | 18.34 | 18.00% | 21.90% | 34.30% | 343,000 | 1.90 | 77.10% |

The classifier/verdict is correct in all four cells, all margins exceed `1.50`, and no cell is indeterminate or contradicts the wait-share check. The registered p95 band is `16–20` calendar days: A1 (`20.28`) and A2 (`20.18`) MISS; B1 (`18.77`) and B2 (`18.34`) PASS. The two A-cell misses are recorded in `DEVIATIONS.md`; no parameters were tuned.

## Triage evaluation

Each row is a separate three-repeat synthetic model run. RQ-005 was blocked before a model call, so the pre-registered recommendation denominator is 27; RQ-011 was added after pre-registration and is scored separately.

| Run (UTC) | Rules / samples | Pre-registered recommendations | Pre-registered gate outcomes | Added RQ-011 | Notes |
|---|---|---:|---:|---:|---|
| `20261103T081142Z` | v1.1; ten pre-registered samples | 27/27 correct (9/9 each repeat) | 30/30 correct | Not included | No two-approver grant path exercised. |
| `20261103T081934Z` | v1.1; ten registered plus RQ-011 separately | 26/27 correct | 30/30 correct | 3/3 recommendations and gate outcomes; 3 two-approver grants | RQ-007 returned `reject` once; expected `escalate`. |
| `20261103T082659Z` | v2; ten registered plus RQ-011 separately | 27/27 correct | 30/30 correct | 3/3 recommendations and gate outcomes; 3 two-approver grants | No recommendation misses. |

This is a small fixture evaluation (ten pre-registered samples plus one added), not a benchmark. The v2 rule was written after the RQ-007 miss: it maps each condition to one outcome and is a corrective follow-up, not an independent pre-registered result. The earlier RQ-001 smoke call also exposed a rule/fixture mismatch: the original instruction said missing approval should escalate, while standard-tier fixtures RQ-001, RQ-004, and RQ-005 expected approval. The rule was changed; the fixtures were not. See `DEVIATIONS.md` for the chronology and scope.

## PM4Py cross-check (exploratory, added after pre-registration)

| Cell | Designed-model fitness | Discovered-model fitness | Discovered precision | Fitting traces | Pandas exact-path rate |
|---|---:|---:|---:|---:|---:|
| A1 | 0.9907 | 1.0000 | 0.9933 | 94.45% | 94.45% |
| A2 | 0.9637 | 1.0000 | 0.9813 | 77.40% | 77.40% |
| B1 | 0.9907 | 1.0000 | 0.9932 | 94.35% | 94.35% |
| B2 | 0.9632 | 1.0000 | 0.9825 | 77.10% | 77.10% |

Fitting-trace shares equal pandas exact-path rates in all cells. With `noise_threshold=0`, the discovered model retains observed variants from the same log, so its fitness is approximately `1.0000`. From A2 alone the miner recovered information returns after steps 2 (344 cases), 3 (48), and 5 (28), plus the distinct step 7 → step 6 provisioning loop in 116 of 2,000 cases (5.80%). The discovered BPMN contains silent joins before step 1; the readable as-is redraw uses one explicit merge gateway for those returns. PM4Py exported the discovered BPMN without diagram coordinates (Graphviz is not installed); `lean/as_is_discovered_A2_layout.bpmn` is the same model laid out with bpmn-auto-layout.

## Hand-trace and intake bot

All three featured hand-trace checks match the component code within `0.02` business hours; the day-by-day counts and rounding method are in [`analysis/hand_trace.md`](analysis/hand_trace.md).

The UiPath intake-validation demonstration applies five rules: required requester/entitlement/manager fields, registered entitlement, manager distinct from requester, justification of at least 20 characters, and no duplicate requester-entitlement pair. On 20 synthetic requests it wrote 12 valid and 8 returned rows. This demonstrates the checks on fixtures; it is not a production control.

## Value model and interpretation

The synthetic value model estimates 683.20 saved hours per year, `$15,030` annual value, `9.86` months to payback, and `$21,927` 36-month NPV. Sensitivity payback is `12.77`, `9.12`, and `7.51` months at adoption rates of 60%, 80%, and 95%, respectively.

The pre-registered owner classifier passes its classification, margin, and wait-share conditions in all four cells. The A1/A2 p95 misses are the only registered acceptance-band misses. Exact-path non-conformance includes rework and step 7 → step 6 returns. The hold-removed run and jitter results remain as reported in `analysis/results/robustness.json`; all figures are synthetic and no parameter or band was tuned.
