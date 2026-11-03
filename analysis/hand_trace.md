# Hand trace (synthetic data)

All values are synthetic. Inputs: `analysis/trace_events.csv` (case A1-C0001) and `analysis/trace_events_C0007.csv` (case A1-C0007), counted by hand and then compared with the output of `components.py` (`analysis/trace_code.csv`, `analysis/trace_code_C0007.csv`).

## Rounding rule

Convert timestamps to the activity team’s time zone, ignore seconds, and count working minutes separately for each day. Count zero minutes on non-working days. Divide the total minutes by 60 and round only the total to two decimal places. For comparison, round the code value to two decimals too; differences of 0.02 h or less count as a match.

## Business-hours hand-trace

| Case / activity | Team calendar | Day-by-day working minutes | Hand total | Code total (2 d.p.) | Match |
| --- | --- | --- | --- | --- | --- |
| A1-C0001, Validate request: handoff | Access Service Desk, Asia/Kolkata, 09:00–18:00 | Mon 1 Jun after 18:00 IST: 0; Tue 2 Jun 09:00–09:19: 19 | 19 ÷ 60 = **0.32 h** | **0.32 h** | Yes |
| A1-C0001, Validate request: queue | Access Service Desk, Asia/Kolkata, 09:00–18:00 | Tue 2 Jun 09:19–09:56: 37 | 37 ÷ 60 = **0.62 h** | **0.62 h** | Yes |
| A1-C0001, Validate request: touch | Access Service Desk, Asia/Kolkata, 09:00–18:00 | Tue 2 Jun 09:56–10:07: 11 | 11 ÷ 60 = **0.18 h** | **0.19 h** | Yes (0.01 h difference) |
| A1-C0007, Line manager approval | Line Management India, Asia/Kolkata, 09:00–18:00 | Fri 20 Mar: 57; Sat: 0; Sun: 0; Mon 23 Mar: 230 | 287 ÷ 60 = **4.78 h** | **4.78 h** | Yes |
| A1-C0001, Entitlement owner approval | Application Owners, America/New_York, 09:00–17:00 | Tue 2 Jun: 297; Wed 3 Jun: 480; Thu 4 Jun: 419 | 1196 ÷ 60 = **19.93 h** | **19.94 h** | Yes (0.01 h difference) |

A1-C0007 weekend breakdown: Friday 17:03–18:00 = 57 min; Saturday = 0 min; Sunday = 0 min; Monday 09:00–12:50 = 230 min. Total = 287 min = **4.78 business hours**. The schedule-to-start interval is about **67.8 calendar hours**; the weekend contributes no business hours.

Time-zone handoff (A1-C0001, step 1 → step 2): step 1 completed at 16:35 London (21:05 IST), after the India service desk's 18:00 close, so the handoff counts only 09:00–09:19 IST on 2 June: 19 business minutes against about 12 hours of clock time. Each interval is counted on the calendar of the team that owns the receiving activity.

## Payback hand check

Use the saved synthetic inputs from `analysis/results/value_model.json`: annual gross savings **$15,030.40** , build cost **$8,000.00**, monthly run cost **$125.00**, with adoption at **0.60** for months 1–4, **0.80** for months 5–8, then **0.95**. For each month, net cash flow = annual gross savings ÷ 12 × adoption − monthly run cost. Start cumulative value at negative build cost. Keep full precision in the calculation; display currency to two decimals.

- Months 1–4: monthly net = $15,030.40 ÷ 12 × 0.60 − $125.00 = **$626.52**; cumulative after month 4 = **−$5,493.92**.
- Months 5–8: monthly net = $15,030.40 ÷ 12 × 0.80 − $125.00 = **$877.03**; cumulative after month 8 = **−$1,985.81**.
- Month 9 net = $15,030.40 ÷ 12 × 0.95 − $125.00 = **$1,064.91**; cumulative after month 9 = **−$920.91**.
- Month 10 has the same net flow and brings cumulative value to **$144.00**, so payback occurs during month 10.

Interpolate within month 10: 9 + $920.91 ÷ $1,064.91 = **9.86 months** (rounded to two decimals), matching the saved payback in `analysis/results/value_model.json` when rounded.

This is an undiscounted payback; the 12% discount rate applies only to the 36-month NPV ($21,927).