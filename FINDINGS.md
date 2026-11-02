# Synthetic findings

All figures below are synthetic and read from `analysis/results/` or `DEVIATIONS.md`. Values are reproduced exactly as stored.

## Per-cell results

| Cell | Intended / classified | Margin | Approver share | Handoff share | Doer share | Wait share | Median days | p95 days | Loop rate | Breach rate | Defect rate | DPMO | Sigma before | Exact-path conformance |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | APPROVER-BOUND / APPROVER-BOUND | 4.109527601495121 | 0.7786400245046847 | 0.1894719052918397 | 0.031888070203475505 | 0.9622972182084114 | 6.034623842592593 | 20.28373032407407 | 0.04 | 0.2755 | 0.303 | 303000.0 | 2.0157915570468274 | 0.9445 |
| A2 | APPROVER-BOUND / APPROVER-BOUND | 4.021267557523499 | 0.7751636294147489 | 0.192765991898369 | 0.03207037868688205 | 0.9623741161731642 | 6.339224537037037 | 20.17682291666665 | 0.18 | 0.2935 | 0.4065 | 406500.0 | 1.736557621780165 | 0.774 |
| B1 | HANDOFF-BOUND / HANDOFF-BOUND | 8.214814129250245 | 0.10510685437806175 | 0.8634332724259496 | 0.031459873195988544 | 0.9628659620041152 | 5.95941550925926 | 18.77213599537037 | 0.04 | 0.21 | 0.2385 | 238500.0 | 2.2111359409013778 | 0.9435 |
| B2 | HANDOFF-BOUND / HANDOFF-BOUND | 8.104614825487483 | 0.10612370653122824 | 0.8600917652886751 | 0.03378452818009661 | 0.9604146492279041 | 6.084045138888889 | 18.339107638888883 | 0.18 | 0.219 | 0.343 | 343000.0 | 1.9042892902985789 | 0.771 |

The classifier/verdict output reports all four cells correct, all margins at least `1.5`, no indeterminate cells, no wait-share contradiction, and overall verdict `pass: true`. The two A-cell p95 values, `20.28373032407407` days (A1) and `20.17682291666665` days (A2), MISS the registered `16–20` day band. B1 (`18.77213599537037`) and B2 (`18.339107638888883`) are within it. These exact A-cell misses and the conclusion that they do not change the registered classifier pass condition are recorded in `DEVIATIONS.md`.

## Hold placement and robustness

The recorded Part B Table 3 “Hold” interpretation is “attached by argmax of queue plus handoff in that scenario's table”, read with Part B §9 item 6. The current generator therefore places the hold on step-5 queue in A cells (mean `20.34` h), and step-5 handoff in B cells (mean `6.01` h). A cells were unchanged from P2; B-cell placement moved from queue to handoff. `DEVIATIONS.md` records that classifications are correct under both placements. The hold is a deliberate reinforcing bias, but the hold-removed run also classifies all four cells correctly: margins are `2.9384608926223206`, `2.810689950042037`, `6.136934760975785`, and `6.221963219600613`. Under jitter, `20` of `20` cell-runs classify correctly with margin; observed margin range is `3.455609557239851` to `8.730539725279423`.

## Value model

The synthetic value model reports `683.2` saved hours per year and `$15030.400000000001` annual value, with `9.86477688185506` months payback and `$21926.738826523913` 36-month NPV. Sensitivity payback is `12.768945923514014` months at adoption `0.6`, `9.12172947990939` at `0.8`, and `7.51239545249662` at `0.95`.

## Interpretation

The registered owner classifier behaves as intended for all four synthetic cells and remains correct in the saved robustness runs. A1/A2 p95 calendar time misses are the sole reported acceptance-band misses; they are disclosed without tuning. High exact-path conformance in the low-loop cells and lower conformance in high-loop cells reflect that loop traces are non-conforming under the exact-path definition. These results test the method on generated data, not operational performance.
