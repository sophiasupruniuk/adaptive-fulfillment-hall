# Adaptive Fulfillment Hall

A warehouse digital twin built in NVIDIA Omniverse Kit. The scene is a 27 × 42 m
fulfillment hall with a rack storage area and a conveyor sortation loop. Parcels
arrive on one conveyor run; a light-curtain sensor detects each one and a
diverter arm pushes medium and large parcels across to a second run, bound for
despatch. Small parcels are left on the line, continue to the end of the run,
and are collected by a rail-mounted robot arm that picks them up and stores
them in the nearest rack bays. A control panel sets the layout and run
parameters, shows live KPIs, and writes results to CSV.

The layout is generated from a configuration file rather than placed by hand,
and two switches — aisle width and automation level — change the scene through
USD variants.

---

## Before you start

You need:

- A Windows machine with an RTX GPU
- Git
- The repository cloned to a path with no spaces in it

Nothing else has to be installed first. The build step downloads the Kit SDK and
everything else it needs.

---

## Getting it running

**1. Open a terminal in the repository root.**

That is the folder containing `repo.bat` — `kit-app-template`. Any terminal will
do: PowerShell, Windows Terminal, or the terminal inside VS Code.

**2. Build.**

```
./repo.bat build
```

The first build downloads dependencies and takes around four minutes. Later
builds take a few seconds.

**3. Launch.**

```
./repo.bat launch
```

The application opens. It starts with an empty stage.

**4. Open the scene.**

File → Open, then `content/adaptive_fulfillment_hall.usd`.

**5. Find the control panel.**

The extension loads automatically and its window appears in the middle of the
screen. Drag it to a side dock so it is out of the way of the viewport.

Total time from clone to a running scene is under ten minutes on a machine that
has not built it before.

---

## Running a scenario

The panel is in three groups, top to bottom: build the layout, run a simulation
on it, export the results.

**1. Choose the layout.** Set aisle width, automation level and rack rows, then
press **Generate Layout**. The status line underneath reports what was built,
or why a row count was refused.

Choose **ConveyorPlusDiverter** as the automation level if you want parcels to
be sorted and the robot arm to run. The other levels build a conveyor with no
diverter, or no conveyor at all, so every parcel travels to the door end
undivided and the diversion and storage KPIs stay at zero.

**2. Set the run.** Set arrival rate, conveyor speed, random seed and duration,
then press **Run**. The KPI display updates once a second. The run stops itself
when the duration is up, or press **Stop** to end it early.

The robot arm starts with the run and stops with it. It watches the end of the
pickup conveyor, picks up whatever small parcels are queued there, and places
them into the nearest free rack shelf within its reach; when nothing is
waiting it idles. Its current pose and the number of parcels it has racked are
shown below the KPIs.

**3. Export.** Type a scenario name and press **Export Results**. Two CSV files
are written and the status line shows where they went.

Results are written to:

```
source/extensions/sophia.afh.core/data/results/
```

Each run produces `<scenario>_<timestamp>_results.csv` with the parameters and
KPIs, and `<scenario>_<timestamp>_events.csv` with one row per parcel event.

Running also saves a copy of the scenario's override layer to
`content/Layers/05_<scenario>.usd`, so a scenario's settings can be reproduced
by copying that file over `05_scenario_overrides.usd`.

---

## The control panel

| Control | What it does | Range |
|---|---|---|
| Aisle Width | Narrow or wide rack spacing. Narrow fits more rows. | Narrow / Wide |
| Automation Level | Which conveyor equipment is present. ConveyorPlusDiverter is the one that sorts and stores parcels. | Manual / Conveyor / ConveyorPlusDiverter |
| Rack Rows | How many rack rows to build. Each variant fits as many as its aisle width allows, up to this number. | 4–12 |
| **Generate Layout** | Builds the racks, equipment, sensor and robot arm rail from the configuration file. | |
| Parcel Arrival Rate | How many parcels arrive per hour. | 200–1200 |
| Conveyor Speed | Belt speed. Parcels travel slower than this, and by a different amount per size — see limitations. | 0.5–2.0 m/s |
| Random Seed | Fixes which parcel sizes arrive in which order. | any whole number |
| Simulation Duration | How long the run lasts. Spawning stops 90 seconds before the end so parcels in transit can finish. | 60–600 s |
| **Run** | Applies the run settings, starts the simulation, the diverter and the robot arm. | |
| **Stop** | Ends the run, stops the arm and clears parcels from the scene (except parcels already racked). | |
| Scenario Name | Names the exported files and the saved override layer. | any text |
| **Export Results** | Writes the finished run's results and event log. | |

The KPI panel below the buttons shows parcels spawned, completed, fallen,
missed, diverted, the diversion success rate, jam count, average transit time
and total diverter travel. Below it, the robot line shows the arm's current
pose and how many parcels it has racked.

---

## Switching configurations without the panel

Both switches are USD variants, so they work with the extension turned off.
Select `/World/Layout` in the Stage window and change **AisleWidth** or
**AutomationLevel** in the Property panel. The racks respace and the conveyor
equipment appears or disappears immediately.

---

## What is where

```
content/
  adaptive_fulfillment_hall.usd   the stage to open
  Assets/                         the modelled parts: hall, racks, conveyor,
                                  diverter, light-curtain sensor, robot arm,
                                  parcels
  Layers/
    01_geometry.usd               the hall shell
    02_layout.usd                 everything the generator builds
    03_physics.usd                gravity and simulation settings
    04_lighting.usd
    05_scenario_overrides.usd     written when a run starts
    05_<scenario>.usd             saved copies, one per scenario run

source/
  apps/sophia.afh.editor.kit      the application definition
  extensions/sophia.afh.core/
    data/warehouse_config.json    every dimension the generator uses,
                                  including the robot's rail, poses and
                                  joint settings
    data/results/                 exported CSVs
    sophia/afh/core/
      extension.py                starts and stops everything
      ui.py                       the control panel
      simulation.py               runs the simulation, drives the diverter
                                  and the light-curtain sensor
      robot.py                    the sorting arm: rail, poses, gripping,
                                  placement, the cycle
      scene_generation.py         builds the layout, the sensor and the
                                  arm's rail from the config
      measurement.py              KPIs, event log, CSV export

docs/
  decisions.md                    every technical choice and why
  comparison.md                   the three scenarios compared
```

All dimensions live in `warehouse_config.json`. No positions are written into
the Python source, so changing the hall means editing the configuration file and
pressing Generate again. The arm's rail bounds, link lengths, masses, joint
drive settings and every pose it moves through are in the same file.

---

## Known limitations

**Parcels slip against the belt, and by a different amount per size.** The
conveyor speed setting describes the belt, not the parcels — each size's
actual travel speed is derived from it using a separately measured ratio.

**The diverter is calibrated for 1.2 m/s.** Above about 1.6 m/s parcels carry
too much momentum through the transfer and are lost at the cross conveyor. The
scenario comparison in `docs/comparison.md` measures this.

**Only medium and large parcels are diverted — small parcels are stored
instead.** This is by design, not a gap: small parcels continue to the end of
the pickup run and are collected by the robot arm and placed into the racks,
so the exclusion from diversion is what makes the storage path meaningful,
rather than a parcel type the system has no answer for.

**The robot serves one row of bays.** Its rail covers `Bay_00` through
`Bay_04` of `Row_00` — five bays, five shelf slots each. Other rows, and any
row's higher levels beyond the rail's reach, are not stocked by the robot even
when the aisle-width variant generates more rows than that.

**The robot grips with a fixed joint, not by friction.** When the gripper
reaches a parcel, a `PhysicsFixedJoint` is authored between them at run time and
collision between the two is filtered out. Contact-based grasping is unstable at
this scale and would need tuned contact materials and a much smaller time step.
The trade-off is that the gripper cannot drop a parcel by accident, which a real
one can. Once a parcel is placed on a shelf, the joint is released and the
parcel's rigid body is switched off so PhysX stops solving it and it stays put
for the rest of the run.

**The arm moves between fixed poses, not to computed positions.** Each pose is a
set of joint angles in the configuration file, tuned by hand. There is no
inverse kinematics, so the arm repeats the same motion for every parcel rather
than solving for an arbitrary point. The drop pose eases the shoulder back
slightly for each parcel in a stack rather than solving for a new height.

**Racked parcels are excluded from flow tracking.** Once the robot places a
parcel it is marked as stored, so the jam detector does not count a stack of
stationary parcels on a shelf as a jam. They remain in the scene until the run
ends.

**Storage capacity and sortation are linked but not exhaustively tested.** The
robot's occupancy is checked against the hall's total storage capacity
(rows × bays × levels), and a full bay is treated as a real failure rather
than assumed away — but at the arrival rates used for the scenario runs,
storage does not actually fill within a run.

**Repeat runs are not identical.** With a fixed seed the parcel sequence and the
diverter's decisions repeat exactly, but whether a pushed parcel lands cleanly
varies by around 3%, because the simulation runs on real frame time rather than
a fixed step. The robot's cycle is driven by timed waits rather than by checking
whether a pose has been reached, so it is subject to the same variation.

**Never more than about twenty parcels are on the line at once.** Parcels are
removed when they finish, which keeps the frame rate steady. The brief's
200-parcel test would need them to accumulate instead. Parcels the robot has
stored are the exception — they stay in the scene, physics disabled, until the
run ends.

**The diverter response delay is not a panel control.** It is derived from
belt speed and each size's measured slip. `docs/decisions.md` explains why.

**The dock door mechanism was not built.**

**Two warnings appear in the console and can be ignored.** One mentions
`conveyor_module_straight.usd` and a bad menu item — a leftover registration
that does not affect the scene. The other says
`physxTrigger:triggeredCollisions not found` and appears when the sensor's
trigger volume is read before the physics engine has populated it, which
happens on the first frame of a run.

---

## Further reading

- `docs/decisions.md` — every technical choice and the reasoning behind it
- `docs/comparison.md` — the three scenarios compared, with a recommendation
