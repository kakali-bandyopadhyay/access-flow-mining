# Synthetic control plan

This plan is for monitoring a future process using the synthetic study as a template. No synthetic threshold authorizes a production decision. “Registered band” refers to the fixed acceptance bands in `PREREGISTRATION-ANALYSIS.md`; use them unchanged.

| KPI | Target | Source | Frequency | Owner | Escalation trigger |
|---|---|---|---|---|---|
| Intake-validation touch time | Stay within the registered touch-time band | Step 2 events; `analysis/results/step_components.json` | Each review cycle | Service desk process owner | Any review outside the registered band, or sustained upward movement |
| Calendar cycle-time p95 by cell | Within the registered p95 band | Case completion timestamps; `analysis/results/scenario_*.json` | Each review cycle | Process owner | Any miss; current synthetic A1 and A2 misses require explicit review |
| Rework loop rate | Match the expected scenario band; investigate changes | Case attributes and event logs; `analysis/results/scenario_*.json` | Each review cycle | Process owner | Rate outside the registered range or a material increase |
| Exact-path conformance | Track deviations from exact trace `1,2,3,4,5,6,7,8` | Event logs; scenario result `conformance_rate_exact_path` | Each review cycle | Process owner and controls owner | Decline, unexplained trace variation, or evidence of repeated steps/returns |
| Owner classification and margin | Intended owner class with registered minimum margin | Component totals; `analysis/results/scenario_*.json` and `verdict.json` | Each model refresh | Process analytics owner | Wrong or indeterminate class, margin below registered minimum, or wait-share contradiction |
| Policy, prior-approval and SoD facts | Tool output consistent with the maintained reference data | MCP reference JSON and sample requests | On reference-data update and before release | Access-controls owner | Any missing, stale, or conflicting fact; triage must not itself gate access |

The numeric values in the result files are synthetic baseline observations. The escalation criteria use the preregistered bands rather than tuned thresholds.
