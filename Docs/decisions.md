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
what allows the stage to open quickly.

**Everything the generator makes lives under one parent, `/World/Layout`.**
Regenerating is then "delete that branch and rebuild it" rather than hunting for
stray prims.

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

**Parcels travel at roughly 0.47 times the belt speed.** They slip rather than
tracking the belt exactly. This was measured at three different belt speeds and
came out consistent, so the figure is used to work out when the diverter should
fire. It also means the speed setting describes the belt, not the parcels.

**The curved conveyor modules and the mezzanine were not used.** The final
layout has two straight runs joined by a short cross conveyor, with no U-turn
and no upper level, so neither asset had a job to do.

---

## Simulation settings

**The simulation advances 120 times per second rather than the default 60.**
The diverter arm is the fastest-moving contact in the scene, and finer steps
make it less likely that a contact is missed between one step and the next.

**Gravity is written down rather than left at the default.** The value is the
same either way, but the brief asks for settings to be deliberate.

**Parcels weigh 1, 4 and 12 kg.** Within the range the brief specifies. Density
falls as size rises, because a large box is usually lighter for its volume than
a small dense one.

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

**Only medium and large parcels are diverted.** Small ones slip less on the
belt and so arrive slightly ahead of what the timing model predicts, which meant
they were struck late and knocked off the line. Excluding them is also more
realistic: real sorters divert selectively.

**The response delay is not on the panel.** It is worked out from belt speed,
the trigger's distance upstream, and the measured slip. Letting someone set it
independently would let them put the arm out of step with the parcels without
changing anything physical about the scenario. The panel exposes belt speed
instead. This is a deliberate deviation from the brief, which lists the delay as
a panel parameter.

---

## The extension

**Four files, one job each.** The panel, the simulation, the scene generator,
and the measurement code.

**Anything created when the extension is switched on is cleaned up when it is
switched off.** The window, the per-frame callbacks, and any parcels left in the
scene. Turning the extension on and off repeatedly leaves nothing behind.

**The panel is handed the simulation controller rather than making its own.**
There is only ever one simulation, so the panel needs a way to reach the
existing one rather than creating a second.

**Generate and Run are separate buttons.** Generating builds the layout; running
starts a simulation on it. Keeping them apart makes it possible to build once
and run several scenarios, and to show that the dropdowns work without the
extension running.

---

## Measuring

**Parcels are removed once they finish.** They used to stay in the scene
forever, which slowed the frame rate steadily over a few minutes. Removing them
at either end of the line keeps performance flat and gives a natural point to
count them.

**Spawning stops 90 seconds before the run ends.** Without this, parcels
created in the last minute were counted as sent but had no time to arrive, which
made the success rate look worse than it was.

**Storage positions are worked out and written into the results.** Rows × bays
× levels for the chosen aisle width. Without it the density scenario would have
nothing to show, since aisle width does not affect anything else the simulation
measures.

**The diversion success rate counts only parcels the diverter aimed at.**
Parcels it deliberately ignores are not failures.

---

## Known deviations and limits

**200 parcels are never on the line at once.** Parcels are removed when they
finish, which keeps the frame rate steady, so the number in flight stays around
twenty even at the highest arrival rate. The brief's 200-parcel test is not
reachable without letting them accumulate, which would defeat the reason for
removing them.

**Repeat runs are not identical.** With the same seed the parcel sequence and
the diverter's decisions repeat exactly — both baseline runs made 62 diversions
and moved the arm the same distance. Whether a pushed parcel lands cleanly
varies, because the simulation runs on real frame time rather than a fixed step.
Across two baseline runs the success rate was 95.2% and 98.4%.

**The dock door was cut.** It is optional in the brief and was dropped to
protect the required work.
