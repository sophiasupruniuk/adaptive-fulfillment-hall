# Decision log

Choices made while building the Adaptive Fulfillment Hall, and why.

---

## Tools and setup

**Kit Base Editor rather than USD Composer.** Both are allowed by the brief.
Base Editor is the lighter of the two, which helps with the frame-rate and
stage-open-time requirements.

**Shapr3D for modelling.** It is parametric CAD, so typing 2.7 m produces
exactly 2.7 m. The brief grades dimensional accuracy, not modelling technique.

**Assets exported as USDZ, then converted.** Shapr3D cannot write plain `.usd`.
USDZ is a zipped package that cannot be edited, so each asset is converted to
`.usd` before physics is added to it.

**The physics extension is declared in the `.kit` file.** Enabling it through
the Extensions window would be a setting on this machine only, invisible to
anyone else who clones the repository.

---

## Units

**Everything is in metres.**

**Changing the unit label was not enough on its own.** `metersPerUnit` only
says what one unit means — it does not resize anything. The hall was modelled
with vertex values like 2700 under a centimetre label. Switching the label to
metres would have left 2700 in place and reinterpreted it as 2700 metres. The
vertex values had to be divided by 100 at the same time as the label changed.

---

## Scene structure

**Five layers, stacked so the scenario overrides win.** Geometry, layout,
physics, lighting, scenario overrides. The overrides layer is strongest because
it is written when a run starts and has to be able to override everything
beneath it.

**Heavy assets arrive as payloads.** A payload can be left unloaded, which is
what allows the stage to open quickly. The robot arm's link meshes and the
light-curtain sensor model follow the same pattern.

**Everything the generator makes lives under one parent, `/World/Layout`.**
Regenerating is then "delete that branch and rebuild it" rather than hunting for
stray prims. The robot arm is generated the same way, as part of the same
branch, so it is rebuilt along with everything else on Generate.

**Asset paths are always relative.** The project has to run from any folder on
any machine.

---

## The two configuration switches

**Both variant sets sit on `/World/Layout` and control separate parts of the
scene.** Aisle width owns the racks; automation level owns the conveyor
equipment. They never touch the same prims, so they cannot conflict.

**Each variant contains finished geometry, not a setting for code to read.**
The narrow variant holds twelve rack rows at narrow spacing; the wide variant
holds eight at wide spacing. Both exist in the file at once, and USD swaps
between them. This is what allows the dropdown in the Property panel to work
with the extension switched off, which the brief requires.

**The rack row count is a maximum, not a fixed number.** Each variant fits as
many rows as its aisle width allows, up to the number requested. Asking for
twelve gives twelve narrow rows and eight wide ones. Asking for more than
narrow aisles can fit is refused, with the required and available lengths in the
message.

**Conveyor physics disappears along with the conveyor.** The equipment and its
physics are the same prims, so selecting the manual automation level removes
both together. Nothing has to be switched off separately.

---

## Physics on the assets

**Scene-wide settings live in the physics layer.** Gravity and the simulation
timestep are there. Everything specific to an object — its collider, its mass,
its surface velocity — is authored into that object's own file, so a copy of the
asset arrives ready to simulate.

**Physics materials are stored in the assets too.** They were originally in the
physics layer, on the reasoning that friction describes a pair of surfaces
rather than one object. That version never worked, because parcels are created
while the simulation is running and nothing ever attached the material to them.
Moving the material into each asset made every asset self-contained and matched
how the rest of the physics is organised.

**Collision goes on the prim that has the shape.** Mass and rigid-body settings
describe the whole object and sit on its top-level prim; collision describes a
shape and sits on the mesh.

**Collider shapes were chosen per asset rather than by one rule:**

| Asset | Shape | Why |
|---|---|---|
| Parcels | Box | A parcel is a box, so this is exact rather than an approximation. |
| Rack bays | Box | Open frames, but nothing is ever stored inside them, so the openings never matter. |
| Mezzanine, hall shell, door | Exact mesh | Things pass underneath or through, so the real shape matters. |
| Conveyor belt and legs | Exact mesh | Static shapes, cheap enough to use as they are. |
| Diverter arm | Convex hull | The pushing face has to be the real shape; the inside does not matter. |
| Light-curtain sensor frame | None | Decoration — see "The light-curtain sensor" below; detection is a separate, invisible prim. |

**A moving object cannot use its own mesh as a collider.** PhysX rejects it.
This is the concrete reason parcels use a box: simple shapes are faster, more
stable, and for moving objects they are the only option.

**The conveyor legs have colliders.** They stand higher than the belt, so
parcels can hit them. That is a realistic way for the line to jam, so they were
left in rather than removed.

**Rack bays are rotated when placed.** The rack asset is modelled with its
width running along Y, but the layout needs it along X, so the generator turns
each bay 90°. Re-exporting the model would remove the rotation, but a single
line in the generator was cheaper than repeating the whole asset pipeline.

---

## The conveyor

**The belt does not move; the surface it presents does.** The conveyor is a
kinematic object with a surface velocity, so parcels are carried along by
friction while the belt geometry stays still.

**Surface velocity is set in world coordinates, not the belt's own.** By
default it is read in the belt's local frame. The cross conveyor is rotated 90°,
so a velocity meaning "+X" was being applied as "−Y" and parcels travelled the
wrong way. Setting it explicitly to world space fixed it and makes every run's
direction mean what the configuration says.

**Parcels slip against the belt, and the slip is not the same for every size.**
Early measurement used one ratio (about 0.47× belt speed) across all parcels.
Retuning the diverter's timing showed the sizes actually slip by different
amounts, so the single ratio was replaced with three —
`parcel_speed_ratio_small` / `_medium` / `_large` in configuration — each
measured the same way (three belt speeds, averaged). The conveyor speed
setting on the panel still describes the belt, not the parcels; each size's
travel speed is derived from it.

**The curved conveyor modules and the mezzanine were not used.** The final
layout has two straight runs joined by a short cross conveyor, with no U-turn
and no upper level, so neither asset had a job to do.

---

## Simulation settings

**The simulation runs at the default 60 steps per second.** It was originally
set to 120, on the reasoning that the diverter arm is the fastest-moving
contact in the scene and finer steps make it less likely that a contact is
missed between one step and the next. It was changed back to 60 to recover
frame rate once the robot arm was added — running both the diverter and the
robot at double the default step rate cost more than the finer step bought.

**Gravity is written down rather than left at the default.** The value is the
same either way, but the brief asks for settings to be deliberate.

**Parcels weigh 1, 4 and 12 kg.** Within the range the brief specifies. Density
falls as size rises, because a large box is usually lighter for its volume than
a small dense one.

---

## The light-curtain sensor (R1.1 correction)

**The original detector was an invisible cube spanning the belt.** It worked,
but it was pure geometry with no in-world justification — a reviewer flagged
this: R1.1 asks for equipment, and an invisible box is not equipment.

**The fix keeps the two jobs separate: a visible sensor, and an invisible
detection volume.** A modelled light curtain — two posts and a base, styled on
a real through-beam photoelectric sensor — sits beside the belt and carries no
collision at all; it is decoration, the ninth asset for R1.1. Between the
posts, spanning the belt, sits an invisible box carrying `CollisionAPI`,
`PhysxTriggerAPI` and `PhysxTriggerStateAPI` — the actual beam. Real light
curtains work the same way: the beams that do the detecting are infrared and
invisible, so modelling the posts but not the beams is the accurate version,
not a shortcut.

**The trigger schemas ended up on a child mesh, not the prim the code
expected.** After conversion, the beam's collision and trigger schemas landed
on a child prim (originally auto-named by the converter) rather than the
prim's root. Polling code has to read the exact prim carrying
`PhysxTriggerStateAPI`, so the path was corrected and the child was given a
stable name so a re-export does not silently break detection again.

**Detection and timing are now two separate questions, which matches how real
sortation works.** The sensor still does the selecting — it is what tells the
system a parcel exists and roughly how big it is, and without it nothing would
enter the arm's pending queue. But the exact moment the arm fires is decided
by a separate position check downstream, tuned once slip made the sensor's own
timing too imprecise on its own. A scanner reads the parcel; a separate sensor
decides the moment of action. R3.2 still holds — the trigger volume detects
the parcel and starts the sequence that fires the arm, via one more step than
originally documented.

**One offset value replaced a per-size timing model for the final approach.**
Parcels' origins sit at their leading corner, not their centre, so the
position check was firing on the parcel's leading edge rather than its
middle. A single `fire_lead_m` offset (0.05 m) corrects for this across both
diverted sizes; the earlier per-size model turned out to be solving a bigger
problem than the one that remained once the sensor and the position check were
split apart.

---

## The diverter

**The base is fixed and only the arm moves.** They are joined by a sliding
joint along X, across the belt. Nothing needs to hold the base still except
having no rigid body on it.

**The joint's numbers run backwards.** The arm was modelled already extended,
so zero is "out" and −0.6 is "retracted". Recorded here because the signs are
not obvious from the values.

**The trigger volume is placed by the generator, not carried in the asset.**
How far upstream it should sit depends on belt speed, which the panel can
change, so it cannot be fixed inside the asset file.

**The trigger is checked every frame rather than reporting for itself.**
Omniverse trigger volumes do not offer a Python callback that fires when
something enters. The documented approach is to ask the trigger, each frame,
what is currently inside it. The extension already runs code every frame, so
this added nothing new.

**The arm runs on three states: home, waiting, extended.** A parcel arriving
starts a countdown; when it expires the arm extends; after a set time it
retracts. An earlier version simply held the arm out while a parcel was in the
trigger, which gave a push far too short to be useful.

**The arm stays out long enough to act as a guide.** Increasing the time it
holds its extended position stopped medium parcels from being knocked off the
far side of the cross conveyor. Instead of striking them and withdrawing, the
arm now holds still while the parcel transfers across, and gives it something to
lean on. Failures at the transfer dropped from around fifteen a run to one or
two.

**Only medium and large parcels are diverted — and now that is the point,
not a workaround.** The original reasoning was defensive: small parcels slip
less and arrive ahead of the timing model, so they were struck late and
knocked off the line, and excluding them was framed as "more realistic." Once
small parcels were given a real destination — rack storage, via the robot arm
— the exclusion stopped being an excuse for a limitation and became the
actual shape of the system: small parcels are put away, medium and large are
sorted for despatch. The slip problem is now just the reason the diverter
doesn't have to handle small parcels, not the reason they're skipped.

**The response delay is not on the panel.** It is worked out from belt speed,
the trigger's distance upstream, and each size's measured slip. Letting
someone set it independently would let them put the arm out of step with the
parcels without changing anything physical about the scenario. The panel
exposes belt speed instead. This is a deliberate deviation from the brief,
which lists the delay as a panel parameter.

---

## The robot arm

**Built as a portfolio extension of the hall, then folded into the main
integration.** The arm was developed and proven in a standalone test scene
first — hierarchy, physics, joints, drives, named poses, grip logic, an
async sorting cycle — and only moved into the hall once each piece worked on
its own. Rebuilding a working mechanism inside a much larger scene, with a
running simulation and a reviewer's clock, was judged too risky to do in one
step.

**The arm rides a linear rail rather than staying fixed in one spot.** A
fixed arm can only reach one bay, which caps how much storage the system can
actually use regardless of how many rows exist. A 16 m rail (a
`UsdPhysics.PrismaticJoint` with a linear drive, the `BaseSlide` joint) lets
one arm serve five bays — `Bay_00` through `Bay_04` of `Row_00` — each with
five shelf slots at 0.5 m spacing. This is what makes the aisle-width
comparison mean something for the robot's work as well as for raw storage
count: more bays in reach, not just more bays existing.

**A storage index maps to a world position the same way `generate_racks`
does.** `bay_position(config, aisle_width_m, index)` in `scene_generation.py`
turns a slot number into a row, a bay and a level using the same arithmetic
the layout generator uses to place the racks, then returns the world
position: `row = index // (bays_per_row × levels)`,
`bay = remainder // levels`, `level = remainder % levels`. Reusing the
generator's own arithmetic means a slot always lands inside a real bay,
without a second source of truth for where the racks are.

**Gripping is a runtime joint, not friction.** When the gripper reaches a
parcel, a `PhysicsFixedJoint` is authored between them and collision between
the two is filtered out with `FilteredPairsAPI`. Contact-based grasping was
tried and is unstable at this scale without a much smaller time step and
tuned contact materials. The trade-off is that the gripper cannot drop a
parcel by accident, which a real one can.

**Placing a parcel breaks the grip joint and freezes the parcel in place.**
Once the arm sets a parcel on a shelf, the fixed joint is removed and
`physics:rigidBodyEnabled` is set to `False` on the parcel. PhysX stops
solving it entirely rather than it being made kinematic, which was simpler
and confirmed not to cost the frame rate the way accumulating active bodies
used to (see "Parcels are removed once they finish", below).

**The arm moves between fixed poses, not to computed positions.** Each pose
is a set of joint angles in configuration, tuned by hand. There is no inverse
kinematics, so the arm repeats the same motion for every parcel rather than
solving for an arbitrary point; the drop pose eases back slightly for each
parcel added to a stack rather than computing a new height.

**All of the arm's dimensions, poses, joint settings, rail bounds and timing
are in `warehouse_config.json`**, alongside the rest of the hall's
configuration, for the same reason nothing else is hard-coded: changing the
arm means editing the file, not the Python.

**Occupancy is tracked, and a full bay is treated as a real failure, not an
impossibility.** The count of stored parcels is checked against capacity
(`rows × bays × levels`, the same figure already used for the results CSV).
At the arrival rates and run lengths the scenarios use, storage does not
actually fill — roughly fifty-five small parcels arrive in a ten-minute run
against well over a hundred positions — but the check exists and is reachable
in principle, so a longer run or a higher small-parcel share would exercise
it rather than assume it away.

---

## The extension

**Four files, one job each, plus a fifth for the robot.** The panel, the
simulation, the scene generator, and the measurement code, with the robot's
poses, gripping and cycle logic in its own module rather than folded into the
simulation file. It reads the same configuration and reports into the same
KPI system rather than keeping its own.

**Anything created when the extension is switched on is cleaned up when it is
switched off.** The window, the per-frame callbacks, any parcels left in the
scene, and the robot's own per-frame update. Turning the extension on and off
repeatedly leaves nothing behind.

**The panel is handed the simulation controller rather than making its own.**
There is only ever one simulation, so the panel needs a way to reach the
existing one rather than creating a second.

**Generate and Run are separate buttons.** Generating builds the layout,
including the arm and its rail; running starts a simulation on it, and the
arm starts and stops with the run. Keeping them apart makes it possible to
build once and run several scenarios, and to show that the dropdowns work
without the extension running.

---

## Measuring

**Parcels are removed once they finish — except parcels the robot has
stored.** Diverted and despatched parcels used to stay in the scene forever,
which slowed the frame rate steadily over a few minutes; removing them at
either end of the line keeps performance flat. Stored parcels are the
exception: they stay, with physics switched off, until the run ends, since
the whole point is to show the racks filling.

**Spawning stops 90 seconds before the run ends.** Without this, parcels
created in the last minute were counted as sent but had no time to arrive,
which made the success rate look worse than it was.

**Storage positions are worked out and written into the results.** Rows ×
bays × levels for the chosen aisle width. This same figure is now also the
capacity the robot's occupancy count is checked against.

**The diversion success rate counts only parcels the diverter aimed at.**
Parcels it deliberately ignores — small parcels bound for storage — are not
failures.

**A separate count tracks parcels the robot has racked, shown on the panel
next to its current pose.** It is not folded into the main KPI block, since
it belongs to a different subsystem with its own success condition (stored
vs. not stored) rather than the diverter's (diverted vs. missed).

**Stored parcels are marked out of the jam detector's view, not just left
motionless.** A growing stack of placed, physics-disabled parcels on a shelf
looks superficially like the "several stationary parcels in contact" pattern
the jam detector watches for. Rather than rely on the detector never
mistaking one for the other, storing a parcel removes it from flow tracking
entirely, so it is never a candidate for jam detection in the first place.

---

## Known deviations and limits

**200 parcels are never on the line at once.** Parcels are removed when they
finish, which keeps the frame rate steady, so the number in flight stays
around twenty even at the highest arrival rate. The brief's 200-parcel test
is not reachable without letting them accumulate, which would defeat the
reason for removing them.

**Repeat runs are not identical.** With the same seed the parcel sequence and
the diverter's decisions repeat exactly — both baseline runs made 62
diversions and moved the arm the same distance. Whether a pushed parcel lands
cleanly varies, because the simulation runs on real frame time rather than a
fixed step. Across two baseline runs the success rate was 95.2% and 98.4%.
The robot's cycle, driven by timed waits rather than pose-reached checks, is
subject to the same variation.

**The robot serves one row of bays, not the whole rack area.** The rail
covers `Bay_00`–`Bay_04` of `Row_00`; other rows and higher levels beyond the
rail's reach are not stocked by the robot, even though the aisle-width
variant may generate more rows than that.

**The dock door was cut.** It is optional in the brief and was dropped to
protect the required work.
