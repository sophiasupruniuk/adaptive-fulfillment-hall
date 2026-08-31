# Adaptive Fulfillment Hall

A warehouse digital twin built in NVIDIA Omniverse Kit. The scene is a 27 × 42 m
fulfillment hall with a rack storage area and a conveyor sortation loop. Parcels
arrive on one conveyor run, a diverter arm pushes selected ones across to a
second run, and the rest continue to the door end. A control panel sets the
layout and run parameters, shows live KPIs, and writes results to CSV.

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
be sorted. The other levels build a conveyor with no diverter, or no conveyor at
all, so every parcel travels to the door end and the diversion KPIs stay at
zero.

**2. Set the run.** Set arrival rate, conveyor speed, random seed and duration,
then press **Run**. The KPI display updates once a second. The run stops itself
when the duration is up, or press **Stop** to end it early.

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
| Automation Level | Which conveyor equipment is present. ConveyorPlusDiverter is the one that sorts parcels. | Manual / Conveyor / ConveyorPlusDiverter |
| Rack Rows | How many rack rows to build. Each variant fits as many as its aisle width allows, up to this number. | 4–12 |
| **Generate Layout** | Builds the racks and equipment from the configuration file. | |
| Parcel Arrival Rate | How many parcels arrive per hour. | 200–1200 |
| Conveyor Speed | Belt speed. Parcels travel at roughly half this — see limitations. | 0.5–2.0 m/s |
| Random Seed | Fixes which parcel sizes arrive in which order. | any whole number |
| Simulation Duration | How long the run lasts. Spawning stops 90 seconds before the end so parcels in transit can finish. | 60–600 s |
| **Run** | Applies the run settings and starts the simulation. | |
| **Stop** | Ends the run and clears parcels from the scene. | |
| Scenario Name | Names the exported files and the saved override layer. | any text |
| **Export Results** | Writes the finished run's results and event log. | |

The KPI panel below the buttons shows parcels spawned, completed, fallen,
missed, diverted, the diversion success rate, jam count, average transit time
and total diverter travel.

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
                                  diverter, parcels
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
    data/warehouse_config.json    every dimension the generator uses
    data/results/                 exported CSVs
    sophia/afh/core/
      extension.py                starts and stops everything
      ui.py                       the control panel
      simulation.py               runs the simulation, drives the diverter
      scene_generation.py         builds the layout from the config
      measurement.py              KPIs, event log, CSV export

docs/
  decisions.md                    every technical choice and why
  comparison.md                   the three scenarios compared
```

All dimensions live in `warehouse_config.json`. No positions are written into
the Python source, so changing the hall means editing the configuration file and
pressing Generate again.

---

## Known limitations

**Parcels travel at about half the belt speed.** They slip rather than tracking
the belt exactly. The ratio was measured at three belt speeds and is used to
work out when the diverter should fire, but it means the conveyor speed setting
describes the belt, not the parcels.

**The diverter is calibrated for 1.2 m/s.** Above about 1.6 m/s parcels carry
too much momentum through the transfer and are lost at the cross conveyor. The
scenario comparison in `docs/comparison.md` measures this.

**Only medium and large parcels are diverted.** Small parcels slip less and
arrive ahead of the timing model, so they are not targeted and pass through to
the door end.

**Repeat runs are not identical.** With a fixed seed the parcel sequence and the
diverter's decisions repeat exactly, but whether a pushed parcel lands cleanly
varies by around 3%, because the simulation runs on real frame time rather than
a fixed step.

**Storage and sortation do not interact.** Parcels never enter the racks, so
aisle width changes storage capacity and nothing else.

**Never more than about twenty parcels are on the line at once.** Parcels are
removed when they finish, which keeps the frame rate steady. The brief's
200-parcel test would need them to accumulate instead.

**The diverter response delay is not a panel control.** It is derived from belt
speed and the measured slip. `docs/decisions.md` explains why.

**The dock door mechanism was not built.**

**Two warnings appear in the console and can be ignored.** One mentions
`conveyor_module_straight.usd` and a bad menu item — a leftover registration
that does not affect the scene. The other says
`physxTrigger:triggeredCollisions not found` and appears when the diverter's
trigger volume is read before the physics engine has populated it, which
happens on the first frame of a run.

---

## Further reading

- `docs/decisions.md` — every technical choice and the reasoning behind it
- `docs/comparison.md` — the three scenarios compared, with a recommendation
