import json
import os
from pxr import UsdGeom, Gf, UsdPhysics, PhysxSchema

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
    x_position = centreline_x_m - belt_width_m / 2 #so that the central x for the line is aligned with the center of the conveyor

    for i in range(segments):
        y_position = first_y + i * segment_length_m
        conveyor_prim = stage.DefinePrim(f"/World/Layout/Conveyor/{run_name}/Segment_{i:02d}", "Xform")
        payloads = conveyor_prim.GetPayloads()
        payloads.AddPayload(assetPath="../Assets/conveyor_modules/conveyor_module_straight.usd")
        UsdGeom.Xformable(conveyor_prim).AddTranslateOp().Set(Gf.Vec3d(x_position, y_position, 0))

def generate_cross_conveyor(stage, config, run_name):
    """Build the short conveyor that carries diverted parcels across.

    It is rotated 90 degrees, so its surface velocity is set to world space —
    left in local space it would move parcels along the wrong axis.
    """
    centreline_y_m = config["conveyor"]["cross"]["centreline_y_m"]
    start_x_m = config["conveyor"]["cross"]["start_x_m"]
    end_x_m = config["conveyor"]["cross"]["end_x_m"]
    belt_width_m = config["conveyor"]["belt_width_m"]
    y_position = centreline_y_m - belt_width_m / 2
    x_position = min(start_x_m, end_x_m)

    cross_conveyor_prim = stage.DefinePrim(f"/World/Layout/Conveyor/{run_name}/cross_segment", "Xform")
    payloads = cross_conveyor_prim.GetPayloads()
    payloads.AddPayload(assetPath="../Assets/conveyor_modules/conveyor_module_straight.usd")
    UsdGeom.Xformable(cross_conveyor_prim).AddTranslateOp().Set(Gf.Vec3d(x_position, y_position, 0))
    UsdGeom.Xformable(cross_conveyor_prim).AddRotateZOp().Set(-90)
    velocity_api = PhysxSchema.PhysxSurfaceVelocityAPI(cross_conveyor_prim)
    velocity_api.CreateSurfaceVelocityLocalSpaceAttr().Set(False)

def diverter_arm(stage, config):
    """Place the diverter arm and the trigger volume that fires it.

    The trigger sits a fixed distance upstream of the arm; how long the arm
    waits before extending is worked out at run time from the belt speed.
    """
    position_x_m = config["diverter"]["position_x_m"]
    position_y_m = config["diverter"]["position_y_m"]
    position_z_m = config["conveyor"]["belt_height_m"] + config["diverter"]["height_offset_m"]
    trigger_depth_m = config["diverter"]["trigger_depth_m"]
    trigger_height_m = config["diverter"]["trigger_height_m"]
    trigger_offset_m = config["diverter"]["trigger_offset_m"]
    trigger_y_m = position_y_m + trigger_offset_m
    centreline_x_m = config["conveyor"]["outbound"]["centreline_x_m"]
    belt_width_m = config["conveyor"]["belt_width_m"]
    retracted_position_m = config["diverter"]["retracted_position_m"]

    diverter_prim = stage.DefinePrim("/World/Layout/Conveyor/Diverter", "Xform")
    payloads = diverter_prim.GetPayloads()
    payloads.AddPayload(assetPath="../Assets/divider_arm.usd")
    UsdGeom.Xformable(diverter_prim).AddTranslateOp().Set(Gf.Vec3d(position_x_m, position_y_m, position_z_m))
    joint_prim = stage.GetPrimAtPath("/World/Layout/Conveyor/Diverter/divider_arm/PusherJoint")
    if joint_prim.IsValid():
        drive = UsdPhysics.DriveAPI(joint_prim, "linear")
        drive.CreateTargetPositionAttr().Set(retracted_position_m)

    trigger = UsdGeom.Cube.Define(stage, "/World/Layout/Conveyor/Diverter_Trigger")
    xform = UsdGeom.Xformable(trigger)
    xform.AddTranslateOp().Set(Gf.Vec3d(centreline_x_m, trigger_y_m, position_z_m + trigger_height_m / 2.0))
    xform.AddScaleOp().Set(Gf.Vec3f(
        belt_width_m / 2.0,
        trigger_depth_m / 2.0,
        trigger_height_m / 2.0
    ))

    trigger_prim = trigger.GetPrim()
    UsdPhysics.CollisionAPI.Apply(trigger_prim)
    PhysxSchema.PhysxTriggerAPI.Apply(trigger_prim)
    PhysxSchema.PhysxTriggerStateAPI.Apply(trigger_prim)

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
        diverter_arm(stage, config)

    automation_level.SetVariantSelection(previous)