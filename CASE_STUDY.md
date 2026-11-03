# Synthetic case study: access-flow mining

All data and results here are synthetic. This study evaluates a pre-registered process-mining method on generated traces; it is a method test, not evidence about a live operation.

> “This tests the method, not the process.”

## Define

The question is whether an owner-share classifier recovers the planted delay owner across four parameter scenarios, and whether the traces surface intake validation as a plausible automation target. The rule, generator parameters, and acceptance bands were fixed in `PREREGISTRATION-ANALYSIS.md` before production generation. The MCP server supplies policy, prior-approval, and segregation-of-duties facts; the triage model recommends only, and the human gate decides. It blocks unregistered entitlements and self-approval before any model call, requires two confirmations from different approvers (neither the requester) for privileged grants, logs blocked attempts, and executes each request at most once.

## Measure

Each cell contains 2,000 synthetic cases. A1 and A2 classify as APPROVER-BOUND with margins 4.11 and 4.02; B1 and B2 classify as HANDOFF-BOUND with margins 8.21 and 8.10. The owner classification is correct in all four cells. Exact-path conformance is 94.45%, 77.40%, 94.35%, and 77.10%; loop rates are 4.00%, 18.00%, 4.00%, and 18.00%. Wait shares range from 96.04% to 96.29%.

The A1 and A2 p95 calendar times are 20.28 and 20.18 days; both MISS the registered 16–20 day band. B1 (18.77 days) and B2 (18.34 days) PASS. This production-build reproduction difference is logged in `DEVIATIONS.md`; no parameters were tuned, and the registered classification pass condition remains satisfied.

## Analyse

Approval ownership accounts for 77.86% of A1 component time and 77.52% of A2. Handoff ownership accounts for 86.34% of B1 and 86.01% of B2. The step-5 entitlement-owner approval queue is the largest reported A-cell component (57,976.09 summed business hours in A1). Part B Table 3 says “Hold” is “attached by argmax of queue plus handoff in that scenario's table”; applying Part B §9 item 6 places the hold on each scenario’s largest component: the step-5 queue in A cells (mean 20.34 h) and step-5 handoff in B cells (mean 6.01 h). A cells were unchanged from P2; B-cell placement moved from queue to handoff. `DEVIATIONS.md` records correct classification under both placements. With the hold removed, all four cells still classify correctly; margins range from 2.81× to 6.22×.

The exploratory PM4Py miner recovered both A2 loop types from the event log: information returns to step 1 after steps 2, 3, and 5, and provisioning failure returns step 7 to step 6. The written as-is BPMN uses one merge gateway before Submit request; see [`FINDINGS.md`](FINDINGS.md) for loop counts and the PM4Py fitness table.

## Improve

The generated traces identify intake validation as a plausible bot target. The UiPath demonstration checks required fields, registered entitlements, independent manager, justification length, and duplicate requests; it classified 12 of 20 synthetic requests as valid and returned 8 for correction. It demonstrates the five checks on sample data, not a production control.

The to-be BPMN adds an intake-validation bot between submission and service-desk validation, a triage recommendation before approval, a privileged-request gateway, and a second approver confirmation after entitlement-owner approval. The annotation states: “Model recommends only; human decides; blocked attempts logged”. The synthetic value model estimates 683.20 saved hours per year, worth `$15,030` annually, with 9.86 months to payback and `$21,927` 36-month NPV. These are scenario estimates, not a committed business case. The gain is deliberately small: the bot removes intake touch time and the resubmission loops it prevents, and leaves the approval and handoff waits alone, so the SLA breach rate does not change. The delay itself sits with approvers or handoffs, which is what the classifier found.

## Control

Use [`lean/control_plan.md`](lean/control_plan.md) to monitor validation touch, cycle-time tails, rework, conformance, and classifier stability. Escalate the two A-cell p95 band misses for review; do not change registered parameters based on this run. The classifier and synthetic traces do not authorize production decisions.

## Limitations (Part B §9)

1. **Queues are parameters, not capacity.** A team's queue is set by assumption, not derived from arrivals against staffing. The 20.34-hour app-owner queue stands in for senior reviewers who look at requests in batches. Capacity modelling is out of scope and is the named follow-up.
2. **Sequential path only.** The designed path runs steps 1 to 8 in order; no parallel SoD or manager step.
3. **Rework is capped at two loops per case.**
4. **Public holidays are out of scope.** Weekends only in all three regions; a live deployment loads the HR calendar.
5. **One process, four universes.** The scenarios represent the same process under four parameter sets, not four teams.
6. **The hold reinforces the planted signal by design.** The 80-hour hold attaches to each scenario's largest component, widening the margin of whichever owner was already largest. This generator bias is stated openly. With the hold removed, margins are 2.81×–6.22× and all four cells still classify correctly. The hold makes the tail realistic; it does not make the verdict.

The triage gate was designed by the author, implemented with AI assistance, and reviewed line by line. The BPMN diagrams were generated by a script written by the author with AI assistance and reviewed in demo.bpmn.io. The UiPath intake-validation bot was designed by the author, implemented with AI assistance and reviewed in UiPath Studio.
