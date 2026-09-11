import json
import os
from pxr import Usd, UsdGeom, Gf, UsdPhysics, PhysxSchema

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "warehouse_config.json")

def load_config():
    """Read the warehouse layout configuration from disk."""
    with open(config_path) as f:
        return json.load(f)

def generate_layout(stage, config, row_count):
    """Fill both aisle-width variants with rack rows.

    Each variant gets as many rows as its aisle width allows, up to row_count.
    Returns a list of messages: a refusal if even narrow aisles cannot fit the
    request, or a note if wide aisles had to be capped. An empty list means
    both variants got the full count.
    """
    length = config["hall"]["interior_max_y_m"] - config["hall"]["interior_min_y_m"]
    bay_depth = config["rack"]["bay_depth_m"]
    narrow_w = config["aisle"]["narrow_m"]
    wide_w = config["aisle"]["wide_m"]
    def max_rows(aisle_w):
        return int((length - aisle_w) / (bay_depth + aisle_w))

    errors = []

    if row_count > max_rows(narrow_w):
        required = narrow_w + row_count * (bay_depth + narrow_w)
        errors.append(
            f"{row_count} rows at {narrow_w} m aisles requires "
            f"{required:.1f} m but only {length:.1f} m is available."
        )
        return errors

    layout = stage.GetPrimAtPath("/World/Layout")
    aisle = layout.GetVariantSet("AisleWidth")
    previous = aisle.GetVariantSelection()
    aisle.SetVariantSelection("Narrow")
    with aisle.GetVariantEditContext():
        generate_racks(stage, config, narrow_w, min(row_count, max_rows(narrow_w)))
    aisle.SetVariantSelection("Wide")
    with aisle.GetVariantEditContext():
        generate_racks(stage, config, wide_w, min(row_count, max_rows(wide_w)))

    wide_max = max_rows(wide_w)
    if row_count > wide_max:
        errors.append(
            f"Narrow: {min(row_count, max_rows(narrow_w))} rows. "
            f"Wide: capped at {wide_max} rows "
            f"({row_count} would need {wide_w + row_count * (bay_depth + wide_w):.1f} m of {length:.1f} m)."
        )

    aisle.SetVariantSelection(previous)
    return errors

def generate_racks(stage, config, aisle_width_m, row_count):
    """Build one set of rack rows at the given aisle spacing.

    Rows run along X across the storage band and are spaced along Y. Each bay
    is rotated 90 degrees because the rack asset is modelled with its width
    along Y.
    """
    interior_min_y_m = config["hall"]["interior_min_y_m"]
    bay_depth_m = config["rack"]["bay_depth_m"]
    storage_start_x_m = config["bands"]["storage_start_x_m"]
    bay_width_m = config["rack"]["bay_width_m"]
    storage_end_x_m = config["bands"]["storage_end_x_m"]
    bays_per_row = int((storage_end_x_m - storage_start_x_m) / bay_width_m)
    row_x = storage_end_x_m - bays_per_row * bay_width_m

    stage.RemovePrim("/World/Layout/Racks")

    for i in range(row_count):
        y_position = interior_min_y_m + aisle_width_m + i * (bay_depth_m + aisle_width_m)
        row_prim = stage.DefinePrim(f"/World/Layout/Racks/Row_{i:02d}", "Xform")
        UsdGeom.Xformable(row_prim).AddTranslateOp().Set(Gf.Vec3d(row_x, y_position, 0))

        for j in range(bays_per_row):
            rack_prim = stage.DefinePrim(f"/World/Layout/Racks/Row_{i:02d}/Bay_{j:02d}", "Xform")
            payloads = rack_prim.GetPayloads()
            payloads.AddPayload(assetPath="../Assets/rack_bay.usd")
            UsdGeom.Xformable(rack_prim).AddTranslateOp().Set(Gf.Vec3d(j * bay_width_m, 0, 0))
            UsdGeom.Xformable(rack_prim).AddRotateZOp().Set(-90)

def generate_conveyor(stage, config, run_name):
    """Build one straight conveyor run from its entry in the config."""
    start_y_m = config["conveyor"][run_name]["start_y_m"]
    end_y_m = config["conveyor"][run_name]["end_y_m"]
    segment_length_m = config["conveyor"]["segment_length_m"]
    centreline_x_m = config["conveyor"][run_name]["centreline_x_m"]
    first_y = min(start_y_m, end_y_m)
    segments = int(abs((start_y_m - end_y_m) / segment_length_m))
    belt_width_m = config["conveyor"]["belt_width_m"]
    x_position = centreline_x_m - belt_width_m / 2

    for i in range(segments):
        y_position = first_y + i * segment_length_m
        conveyor_prim = stage.DefinePrim(f"/World/Layout/Conveyor/{run_name}/Segment_{i:02d}", "Xform")
        payloads = conveyor_prim.GetPayloads()
        payloads.AddPayload(assetPath="../Assets/conveyor_modules/conveyor_module_straight.usd")
        UsdGeom.Xformable(conveyor_prim).AddTranslateOp().Set(Gf.Vec3d(x_position, y_position, 0))

def generate_cross_conveyor(stage, config, run_name):
    """Build a cross conveyor run from its entry in the config.

    Runs along X, so each segment is rotated 90 degrees and its surface
    velocity is set in world space — left in local space it would move
    parcels along the wrong axis.
    """
    centreline_y_m = config["conveyor"][run_name]["centreline_y_m"]
    start_x_m = config["conveyor"][run_name]["start_x_m"]
    end_x_m = config["conveyor"][run_name]["end_x_m"]
    segment_length_m = config["conveyor"]["segment_length_m"]
    belt_width_m = config["conveyor"]["belt_width_m"]

    y_position = centreline_y_m - belt_width_m / 2
    first_x = min(start_x_m, end_x_m)
    segments = max(1, int(abs(end_x_m - start_x_m) / segment_length_m))

    for i in range(segments):
        x_position = first_x + i * segment_length_m
        segment_prim = stage.DefinePrim(
            f"/World/Layout/Conveyor/{run_name}/Segment_{i:02d}", "Xform"
        )
        payloads = segment_prim.GetPayloads()
        payloads.AddPayload(assetPath="../Assets/conveyor_modules/conveyor_module_straight.usd")
        UsdGeom.Xformable(segment_prim).AddTranslateOp().Set(Gf.Vec3d(x_position, y_position, 0))
        UsdGeom.Xformable(segment_prim).AddRotateZOp().Set(-90)
        velocity_api = PhysxSchema.PhysxSurfaceVelocityAPI(segment_prim)
        velocity_api.CreateSurfaceVelocityLocalSpaceAttr().Set(False)

def diverter_arm(stage, config):
    """Place the diverter arm and the trigger volume that fires it.

    The trigger sits a fixed distance upstream of the arm; how long the arm
    waits before extending is worked out at run time from the belt speed.
    """
    position_x_m = config["diverter"]["position_x_m"]
    position_y_m = config["diverter"]["position_y_m"]
    position_z_m = config["conveyor"]["belt_height_m"] + config["diverter"]["height_offset_m"]
    trigger_height_m = config["diverter"]["trigger_height_m"]
    trigger_offset_m = config["diverter"]["trigger_offset_m"]
    trigger_y_m = position_y_m + trigger_offset_m
    centreline_x_m = config["conveyor"]["outbound"]["centreline_x_m"]
    retracted_position_m = config["diverter"]["retracted_position_m"]

    diverter_prim = stage.DefinePrim("/World/Layout/Conveyor/Diverter", "Xform")
    payloads = diverter_prim.GetPayloads()
    payloads.AddPayload(assetPath="../Assets/divider_arm.usd")
    UsdGeom.Xformable(diverter_prim).AddTranslateOp().Set(Gf.Vec3d(position_x_m, position_y_m, position_z_m))
    joint_prim = stage.GetPrimAtPath("/World/Layout/Conveyor/Diverter/divider_arm/PusherJoint")
    if joint_prim.IsValid():
        drive = UsdPhysics.DriveAPI(joint_prim, "linear")
        drive.CreateTargetPositionAttr().Set(retracted_position_m)

    trigger = stage.DefinePrim("/World/Layout/Conveyor/Diverter_Trigger", "Xform")
    payload = trigger.GetPayloads()
    payload.AddPayload(assetPath="../Assets/trigger_poles.usd")
    xform = UsdGeom.Xformable(trigger)
    xform.AddTranslateOp().Set(Gf.Vec3d(centreline_x_m, trigger_y_m, trigger_height_m))
    UsdGeom.Xformable(trigger).AddRotateZOp().Set(-90)


def generate_automation(stage, config):
    """Fill each automation-level variant with its equipment.

    Manual gets nothing, Conveyor gets the three runs, and ConveyorPlusDiverter
    adds the arm. The conveyor branch is cleared inside each variant before
    building, because a removal authored in one variant does not reach prims
    authored in another.
    """
    layout = stage.GetPrimAtPath("/World/Layout")
    automation_level = layout.GetVariantSet("AutomationLevel")

    previous = automation_level.GetVariantSelection()

    automation_level.SetVariantSelection("Manual")
    with automation_level.GetVariantEditContext():
        stage.RemovePrim("/World/Layout/Conveyor")
        pass
    automation_level.SetVariantSelection("Conveyor")
    with automation_level.GetVariantEditContext():
        stage.RemovePrim("/World/Layout/Conveyor")
        generate_conveyor(stage, config, "inbound")
        generate_cross_conveyor(stage, config, "cross")
        generate_conveyor(stage, config, "outbound")

    automation_level.SetVariantSelection("ConveyorPlusDiverter")
    with automation_level.GetVariantEditContext():
        stage.RemovePrim("/World/Layout/Conveyor")
        generate_conveyor(stage, config, "outbound")
        generate_conveyor(stage, config, "inbound")
        generate_cross_conveyor(stage, config, "cross")
        generate_cross_conveyor(stage, config, "pickup_cross")
        diverter_arm(stage, config)
        generate_end_stop(stage, config, "pickup_cross")
        generate_robot_arm(stage, config)

    automation_level.SetVariantSelection(previous)

def bay_position(config, aisle_width_m, index):
    """Return the world position of a storage slot, by index.

    Slots are numbered along each row, level by level, then row by row.
    The arithmetic mirrors generate_racks so a slot lands inside a bay."""
    interior_min_y_m = config["hall"]["interior_min_y_m"]
    bay_depth_m = config["rack"]["bay_depth_m"]
    bay_width_m = config["rack"]["bay_width_m"]
    shelf_spacing_m = config["rack"]["shelf_spacing_m"]
    levels = config["rack"]["levels_per_bay"]
    storage_start_x_m = config["bands"]["storage_start_x_m"]
    storage_end_x_m = config["bands"]["storage_end_x_m"]
    lowest_shelf_m = config["rack"]["lowest_shelf_height_m"]
    inset_x_m = config["rack"]["slot_inset_x_m"]
    inset_y_m = config["rack"]["slot_inset_y_m"]

    bays_per_row = int((storage_end_x_m - storage_start_x_m) / bay_width_m)
    row_x = storage_end_x_m - bays_per_row * bay_width_m

    slots_per_row = bays_per_row * levels
    row = index // slots_per_row
    remainder = index % slots_per_row
    bay = remainder // levels
    level = remainder % levels

    x = row_x + bay * bay_width_m + bay_width_m / 2 - inset_x_m
    y = interior_min_y_m + aisle_width_m + row * (bay_depth_m + aisle_width_m) - bay_depth_m / 2 - inset_y_m
    z = lowest_shelf_m + level * shelf_spacing_m

    return Gf.Vec3d(x, y, z)

def generate_end_stop(stage, config, run_name):
    """A static plate at the end of a cross run so parcels queue instead of falling off.

    Collision only, no rigid body — parcels press against it and are held there
    by belt friction, giving the robot a repeatable pickup position. Its
    position is derived the same way the run's segments are, so it stays
    flush with the belt when the run moves.
    """
    print(f"[end_stop] building for {run_name}")
    start_x_m = config["conveyor"][run_name]["start_x_m"]
    end_x_m = config["conveyor"][run_name]["end_x_m"]
    segment_length_m = config["conveyor"]["segment_length_m"]
    belt_width_m = config["conveyor"]["belt_width_m"]
    belt_height_m = config["conveyor"]["belt_height_m"]
    thickness_m = config["conveyor"]["end_stop"]["thickness_m"]
    height_m = config["conveyor"]["end_stop"]["height_m"]

    first_x = min(start_x_m, end_x_m)
    segments = max(1, int(abs(end_x_m - start_x_m) / segment_length_m))
    belt_end_x = first_x + segments * segment_length_m

    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default'])
    last_segment = stage.GetPrimAtPath(
        f"/World/Layout/Conveyor/{run_name}/Segment_{segments - 1:02d}")
    belt_box = cache.ComputeWorldBound(last_segment).ComputeAlignedBox()
    belt_centre_y = (belt_box.GetMin()[1] + belt_box.GetMax()[1]) / 2

    print(f"[end_stop] centre_y={belt_centre_y} end_x={belt_end_x}")

    stop = UsdGeom.Cube.Define(stage, f"/World/Layout/Conveyor/{run_name}/EndStop")
    stop.GetSizeAttr().Set(1.0)
    stop.AddTranslateOp().Set(Gf.Vec3d(
        belt_end_x - thickness_m / 2,
        belt_centre_y,
        belt_height_m + height_m / 2,
    ))
    stop.AddScaleOp().Set(Gf.Vec3f(thickness_m, belt_width_m, height_m))
    UsdPhysics.CollisionAPI.Apply(stop.GetPrim())

def generate_robot_arm(stage, config, root_path="/World/RobotArm"):
    """Build the sorting arm as a PhysX articulation of jointed rigid bodies.

    Links are siblings, not nested, because PhysX cannot simulate a rigid body
    inside another; the chain is expressed by joints instead. Each link is an
    Xform carrying the body, with a Geom child carrying the collider.

    Returns (bodies, joints): two dicts of name -> prim path.
    """
    robot = config["robot"]
    links = robot["links"]
    limit_deg = robot["joint_limit_deg"]
    base_x = robot["position_x_m"]
    base_y = robot["position_y_m"]
    base_z = robot["position_z_m"]

    if stage.GetPrimAtPath(root_path):
        stage.RemovePrim(root_path)

    root = UsdGeom.Xform.Define(stage, root_path)
    root.AddTranslateOp().Set(Gf.Vec3d(base_x, base_y, base_z))
    root.AddRotateZOp().Set(robot["position_yaw_deg"])
    UsdPhysics.ArticulationRootAPI.Apply(root.GetPrim())
    UsdGeom.Scope.Define(stage, f"{root_path}/Joints")

    bodies = {}
    joints = {}
    previous = None
    z_offset = 0.0

    for link in links:
        body_path = f"{root_path}/{link['name']}"
        body = UsdGeom.Xform.Define(stage, body_path)
        body.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, z_offset + link["length_m"] / 2.0))
        UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
        UsdPhysics.MassAPI.Apply(body.GetPrim()).CreateMassAttr().Set(link["mass_kg"])

        geom_path = f"{body_path}/Geom"
        if link["shape"] == "cylinder":
            geom = UsdGeom.Cylinder.Define(stage, geom_path)
            geom.GetHeightAttr().Set(link["length_m"])
            geom.GetRadiusAttr().Set(link["radius_m"])
        else:
            geom = UsdGeom.Cube.Define(stage, geom_path)
            geom.GetSizeAttr().Set(link["length_m"])
        UsdPhysics.CollisionAPI.Apply(geom.GetPrim())

        bodies[link["name"]] = body_path
        joint_path = f"{root_path}/Joints/{link['joint']}"

        if previous is None:
            weld = UsdPhysics.FixedJoint.Define(stage, joint_path)
            weld.CreateBody1Rel().SetTargets([body_path])
        else:
            joints[link["joint"]] = joint_path
            joint = UsdPhysics.RevoluteJoint.Define(stage, joint_path)
            joint.CreateBody0Rel().SetTargets([bodies[previous["name"]]])
            joint.CreateBody1Rel().SetTargets([body_path])
            joint.CreateAxisAttr(link.get("axis", "Y"))
            joint.CreateLocalPos0Attr(Gf.Vec3f(0.0, 0.0, previous["length_m"] / 2.0))
            joint.CreateLocalPos1Attr(Gf.Vec3f(0.0, 0.0, -link["length_m"] / 2.0))
            joint.CreateLocalRot0Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
            joint.CreateLocalRot1Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
            link_limit = link.get("limit_deg", limit_deg)
            joint.CreateLowerLimitAttr().Set(-link_limit)
            joint.CreateUpperLimitAttr().Set(link_limit)

            drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")
            drive.CreateTypeAttr("force")
            drive.CreateStiffnessAttr().Set(link["stiffness"])
            drive.CreateDampingAttr().Set(link["damping"])
            drive.CreateMaxForceAttr().Set(link["max_force"])
            drive.CreateTargetPositionAttr(0.0)

        previous = link
        z_offset += link["length_m"]

    return bodies, joints