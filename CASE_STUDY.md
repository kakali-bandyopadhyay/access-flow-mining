# Synthetic case study: access-flow mining

All observations, scenarios and results here are synthetic. This study evaluates a pre-registered process-mining method on generated traces; it is a method test, not evidence about a live operation.

> “This tests the method, not the process.”

## Define

The question is whether an owner-share classifier recovers the planted delay owner across four parameter scenarios, and whether the traces surface intake validation as a plausible automation target. The rule, generator parameters and acceptance bands were fixed in `PREREGISTRATION-ANALYSIS.md` before production generation. The MCP server supplies policy, prior-approval and segregation-of-duties facts; a separate triage step (`mcp/triage.py`) asks a model for a recommendation only, and a human approval gate decides: it refuses unregistered entitlements and self-approval before any model call, requires two confirmations from different approvers (neither the requester) for privileged entitlements (six of the ten sample requests: RQ-002 and RQ-006 to RQ-010), logs every blocked attempt, and executes each request at most once.

## Measure

Each cell contains `2000` synthetic cases. A1 and A2 classify as APPROVER-BOUND with margins `4.109527601495121` and `4.021267557523499`; B1 and B2 classify as HANDOFF-BOUND with margins `8.214814129250245` and `8.104614825487483`. The owner classification is correct in all four cells, while conformance to the exact eight-step trace is `0.9445`, `0.774`, `0.9435`, and `0.771` respectively. Rework loop rates are `0.04`, `0.18`, `0.04`, and `0.18`. Wait shares range from `0.9604146492279041` to `0.9628659620041152`.

The A1 and A2 p95 calendar times are `20.28373032407407` and `20.17682291666665` days; both MISS the registered `16–20` day band. B1 (`18.77213599537037` days) and B2 (`18.339107638888883` days) are within the band. This is the production-build reproduction difference logged in `DEVIATIONS.md`; no parameters were tuned, and the registered classification pass condition remains satisfied.

## Analyse

Approval ownership accounts for `0.7786400245046847` of A1 component time and `0.7751636294147489` of A2. Handoff ownership accounts for `0.8634332724259496` of B1 and `0.8600917652886751` of B2. Step-5 entitlement-owner approval queue is the largest reported A-cell component (`57976.09166666667` summed business hours in A1). The hold placement follows the logged interpretation of Part B Table 3, “Hold”: “attached by argmax of queue plus handoff in that scenario's table”. Applying Part B §9 item 6 places the hold on the scenario’s largest component: A cells use the step-5 queue (mean `20.34` h), and B cells use step-5 handoff (mean `6.01` h). Accordingly, A cells did not change from P2; B-cell holds moved from step-5 queue to step-5 handoff. `DEVIATIONS.md` records that all four classifications remain correct under both placements. The hold reinforces the planted signal by design; the hold-removed run still classifies all four cells correctly, with margins `2.9384608926223206`, `2.810689950042037`, `6.136934760975785`, and `6.221963219600613`.

## Improve

The generated traces identify intake validation as the bot target. The value model estimates annual savings of `683.2` hours (`560.0` direct handling hours and `123.19999999999999` avoided rework hours), worth `$15030.400000000001` per year. The modeled payback is `9.86477688185506` months and 36-month NPV is `$21926.738826523913`. These are synthetic scenario estimates, not a committed business case.

## Control

Use the monitoring plan in `lean/control_plan.md` to monitor validation touch, cycle-time tails, rework, conformance, and classifier stability. Escalate the two A-cell p95 band misses for review; do not change the registered parameters based on this run. The classifier and synthetic traces do not authorize production decisions.

## Limitations (Part B §9)

1. **Queues are parameters, not capacity.** A team's queue is set by assumption, not derived from arrivals against staffing. The `20.34`-hour app-owner queue stands in for senior reviewers who look at requests in batches. Capacity modelling is out of scope and is the named follow-up.
2. **Sequential path only.** The designed path runs 1 to 8 in order; no parallel SoD or manager step.
3. **Rework is capped at two loops** per case.
4. **Public holidays are out of scope.** Weekends only in all three regions; a live deployment loads the HR calendar.
5. **One process, four universes.** The four scenarios are the same process under four sets of parameters, not four teams.
6. **The hold reinforces the planted signal by design.** The 80-hour hold attaches to each scenario's largest component, so it widens the margin of whichever owner was already largest. That is a bias in the generator, stated openly, and §1.3 is the answer to it: with the hold removed entirely, margins are `2.56×–6.92×` and all four cells still classify correctly. The hold makes the tail realistic; it does not make the verdict.

`mcp/triage.py` is designed by the author, implemented with AI assistance, reviewed line by line.
