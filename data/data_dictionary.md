# Synthetic data dictionary

All records in this package are synthetic. No public holidays are modelled; business days are Monday through Friday. Timestamps use ISO 8601 with the owning team's UTC offset.

## Event logs

Files: `event_log_A1.csv`, `event_log_A2.csv`, `event_log_B1.csv`, and `event_log_B2.csv`. Each row is one lifecycle event for one activity execution. Activities repeated after a return are separate executions with the same case identifier.

| Field | Meaning |
|---|---|
| `case_id` | Synthetic case key, prefixed by scenario |
| `activity` | Activity name from the eight-step designed path |
| `lifecycle` | `schedule`, `start`, or `complete` |
| `timestamp` | ISO 8601 timestamp with UTC offset |
| `resource` | Synthetic resource code; no real person is represented |
| `team` | Owning synthetic team/calendar key |
| `timezone` | IANA time zone of the owning team's calendar |

## Case tables

Files: `cases_A1.csv`, `cases_A2.csv`, `cases_B1.csv`, and `cases_B2.csv`.

| Field | Meaning |
|---|---|
| `case_id` | Join key to the event log |
| `scenario` | One of A1, A2, B1, or B2 |
| `rework_intensity` | `low` or `high`, as fixed by the scenario design |
| `case_type` | `standard`, `privileged`, or `emergency` |
| `region` | Synthetic requester region: India, UK, or US East |
| `priority` | Priority label derived from case type |
| `requesting_team` | Synthetic region-specific requester team |
| `channel` | Synthetic intake channel |
| `sla_target_days` | Calendar-day SLA target for the case type |
| `outcome` | `completed_within_sla` or `sla_breach` |
| `arrival_timestamp` | Initial request arrival timestamp with UTC offset |
| `information_loop_count` | Exact allocated number of return-for-information loops (0, 1, or 2) |
| `return_points` | Step numbers that returned for information, separated by semicolons |
| `provisioning_failure_count` | Simulated step-7 provisioning failure count (0 or 1); separate from information-loop allocation |
| `hold_applied` | Whether the case received its single multi-day hold |
| `hold_hours` | Sampled hold duration in business hours; zero when no hold applies |

## Activities and ownership

| Step | Activity | Owning team | Approval |
|---:|---|---|---|
| 1 | Submit request | Requesting team for the case region | No |
| 2 | Validate request | Access Service Desk | No |
| 3 | Line manager approval | Line Management using the requester's region calendar | Yes |
| 4 | SoD / access-risk check | Access Risk and Controls | No |
| 5 | Entitlement owner approval | Application Owners | Yes |
| 6 | Provision access | IAM Engineering | No |
| 7 | Confirm access works | Requesting team for the case region | No |
| 8 | Close request | Access Service Desk | No |

## Scenario mapping

| Scenario | Delay profile | Rework intensity | Seed |
|---|---|---|---:|
| A1 | A | Low | 1010 |
| A2 | A | High | 1020 |
| B1 | B | Low | 2010 |
| B2 | B | High | 2020 |

The A and B delay profiles are read from `params.json`. A1/A2 share profile A; B1/B2 share profile B. Touch means are identical across all four cells. Information-loop case counts are allocated exactly from Table 3; loop return points and the remaining stochastic draws use the scenario seed.

The total mean resubmission touch is 22.0 minutes, split across replayed steps 1 and 2 as 7.7 and 14.3 minutes. The first-pass intake touch mean is 12.0 minutes at step 2.
