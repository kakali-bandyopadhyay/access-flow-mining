# Synthetic value-stream map

The table reports mean wait (queue plus handoff) and mean touch per case, in business hours, averaged across the four synthetic parameter cells. Source: `analysis/results/step_components.json`. The average is a derived summary; use the cell-specific values in that JSON when comparing scenarios. This map describes generated data only.

| Step | Activity | Mean wait (business h/case) | Mean touch (business h/case) |
|---:|---|---:|---:|
| 1 | Submit request | 0.5146646875 | 0.06631746527777778 |
| 2 | Validate request | 2.571305138888889 | 0.2306834722222222 |
| 3 | Line manager approval | 5.957943541666667 | 0.1025932986111111 |
| 4 | SoD / access-risk check | 2.2274895833333335 | 0.2518198958333333 |
| 5 | Entitlement owner approval | 24.047204340277776 | 0.15046993055555558 |
| 6 | Provision access | 3.4790955555555554 | 0.7292302777777778 |
| 7 | Confirm access works | 2.596584548611111 | 0.10366649305555556 |
| 8 | Close request | 1.2438451736111111 | 0.04989430555555555 |

## Eight wastes

| Waste category | Mark | Evidence / interpretation in this synthetic map |
|---|---|---|
| Defects | Present | Rework loops occur in the generated cases; loop rates by cell are in the scenario result JSON. |
| Overproduction | Not evidenced | No demand-versus-output measure is present in the available results. |
| Waiting | Present | Wait exceeds touch at every listed step; step 5 has the largest mean wait (`24.047204340277776` business hours per case). |
| Non-utilized talent | Not evidenced | The generated results contain no skills or staff-utilization measure. |
| Transportation | Not evidenced | The trace data does not measure physical or information-transfer distance. |
| Inventory | Present | Open requests are represented in queues; no WIP inventory count is reported here. |
| Motion | Not evidenced | No movement measure is present in the result data. |
| Extra-processing | Present | Rework loops are recorded, although this simulation does not identify every activity as avoidable processing. |

The “not evidenced” marks mean the synthetic result set does not measure the category; they are not findings that the waste is absent in a real process.
