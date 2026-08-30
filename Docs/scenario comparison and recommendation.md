# Scenario comparison

Three scenarios were run in the Adaptive Fulfillment Hall simulation. All three
used random seed 22, a 600-second run with a 510-second spawn window, 12
requested rack rows, and the `ConveyorPlusDiverter` automation level. The
diverter targets medium and large parcels only.

## Configurations

| | Baseline | High throughput | High density |
|---|---|---|---|
| Arrival rate | 600 /hr | 1200 /hr | 1200 /hr |
| Conveyor speed | 1.2 m/s | 1.6 m/s | 1.2 m/s |
| Aisle width | Wide (3.2 m) | Wide (3.2 m) | Narrow (1.8 m) |

## Results

| | Baseline | High throughput | High density |
|---|---|---|---|
| Parcels spawned | 85 | 169 | 169 |
| Parcels completed | 61 | 89 | **108** |
| Completed per hour | 366 | 534 | **648** |
| Diversion success rate | 98.4% | 80.9% | **98.2%** |
| Fall-off events | 1 | **19** | 2 |
| Jam events | 0 | 0 | 0 |
| Average transit time | 69.5 s | **53.0 s** | 71.1 s |
| Storage positions | 120 | 120 | **180** |
| Diverter cycles | 62 | 110 | 110 |
| Diverter travel | 74.4 m | 132.0 m | 132.0 m |

## What the numbers show

Raising the arrival rate from 600 to 1200 parcels per hour increased completed
throughput by 77% with no measurable loss of accuracy: high density diverted
98.2% of targeted parcels against the baseline's 98.4%, and produced two
fall-off events against one. The sortation loop absorbed the extra load without
degrading.

Raising the belt speed did not behave the same way. High throughput ran 33%
faster than baseline and cut average transit time by 24%, but its diversion
success rate fell to 80.9% and fall-off events rose from 1 to 19. Every one of
those failures occurred at the same place: parcels struck by the diverter carry
their inbound momentum into the cross-conveyor transfer, and above roughly
1.2 m/s that momentum takes them off the far edge before the cross conveyor's
surface velocity can turn them.

The clearest comparison is between the two 1200 /hr scenarios. They differ in
belt speed and aisle width, but aisle width has no throughput consequence in
this model (see limitations), so the difference is attributable to speed alone.
Running at 1.2 m/s completed 108 parcels against 89 at 1.6 m/s — **21% more
throughput from the slower belt**, because the faster belt loses more parcels at
the transfer than it gains in flow.

Aisle width contributed the storage difference independently. Narrow aisles fit
12 rack rows against 8 at wide aisles, giving 180 storage positions against 120
— a 50% gain at no throughput cost.

## Recommendation

**Run the hall at 1200 parcels per hour on a 1.2 m/s belt with narrow aisles.**
This configuration delivered the highest completed throughput of the three
(648 parcels per hour), the joint-best diversion accuracy (98.2%), near-zero
failures, and 50% more storage capacity than the wide-aisle layouts.

**What it costs:** narrow aisles reduce clearance for handling equipment, which
this simulation does not model — the 1.8 m aisle meets the configured minimum
clearance but leaves no margin. Average transit time is also marginally worse
than baseline (71.1 s against 69.5 s) because the belt runs at the same speed
while carrying twice as many parcels.

**What it does not buy:** increasing belt speed. The transfer between the
outbound run and the cross conveyor is the throughput bottleneck, not the belt.
Any future capacity increase should address the transfer geometry — a guide rail
on the cross conveyor, or a longer transfer surface — before the belt speed is
raised again.

## Limitations of the model

**Storage and sortation do not interact.** Parcels never enter the racks in this
simulation; they travel the conveyor loop and exit. Aisle width therefore
changes storage capacity and nothing else, and the "high density" scenario's
throughput gain comes entirely from its arrival rate. The two effects are
reported separately above for that reason.

**Parcels travel at roughly 0.47× the commanded belt speed.** Under
surface-velocity transport the parcels slip rather than tracking the belt
exactly. This ratio was measured across three belt speeds and is used to derive
the diverter's firing delay. It means the "conveyor speed" parameter describes
the belt, not the parcels.

**Physical outcomes are not bit-reproducible.** With a fixed seed the parcel
sequence and the diverter's decisions repeat exactly — both baseline runs
produced 62 diversions and 74.4 m of arm travel. Whether an individual pushed
parcel lands cleanly varies, because the simulation advances on variable frame
time. Across the two baseline runs the diversion success rate was 95.2% and
98.4%, a spread of about 3%.
