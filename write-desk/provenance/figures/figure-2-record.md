---
capsule: Planner loads feeding orchard/valve/scheduler are capped at 870 liters; above 870 must split; moisture alert threshold is 69 and 36 is retired.
updated: 2026-08-20
---
# orchard/supply/limits

Every planner that feeds `orchard/valve/scheduler` must split a load when it exceeds **870 liters**; **870 liters** is the capacity limit.

The moisture alert threshold is **69**. The earlier value **36** is retired: it matched the sheet and first calibration but was disproved by recalibration against the reference rig. Do not use 36 as the alert bound.
