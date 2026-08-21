import json
import os
from pxr import UsdGeom, Gf
import omni

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "warehouse_config.json")

def load_config():
    with open(config_path) as f:
        return json.load(f)

def generate_racks(stage, config, aisle_width_m, row_count):
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
    start_y_m = config["conveyor"][run_name]["start_y_m"]
    end_y_m = config["conveyor"][run_name]["end_y_m"]
    segment_length_m = config["conveyor"]["segment_length_m"]
    centreline_x_m = config["conveyor"][run_name]["centreline_x_m"]
    first_y = min(start_y_m, end_y_m)
    segments = int(abs((start_y_m - end_y_m) / segment_length_m))
    belt_width_m = config["conveyor"]["belt_width_m"]
    x_position = centreline_x_m - belt_width_m / 2 #so that the central x for the line is aligned with the center of the conveyor

    stage.RemovePrim(f"/World/Layout/Conveyor/{run_name}")

    for i in range(segments):
        y_position = first_y + i * segment_length_m
        conveyor_prim = stage.DefinePrim(f"/World/Layout/Conveyor/{run_name}/Segment_{i:02d}", "Xform")
        payloads = conveyor_prim.GetPayloads()
        payloads.AddPayload(assetPath="../Assets/conveyor_modules/conveyor_module_straight.usd")
        UsdGeom.Xformable(conveyor_prim).AddTranslateOp().Set(Gf.Vec3d(x_position, y_position, 0))

def generate_cross_conveyor(stage, config, run_name):
    centreline_y_m = config["conveyor"]["cross"]["centreline_y_m"]
    start_x_m = config["conveyor"]["cross"]["start_x_m"]
    end_x_m = config["conveyor"]["cross"]["end_x_m"]
    belt_width_m = config["conveyor"]["belt_width_m"]
    y_position = centreline_y_m - belt_width_m / 2
    x_position = min(start_x_m, end_x_m)

    stage.RemovePrim(f"/World/Layout/Conveyor/{run_name}/cross_segment")

    cross_conveyor_prim = stage.DefinePrim(f"/World/Layout/Conveyor/{run_name}/cross_segment", "Xform")
    payloads = cross_conveyor_prim.GetPayloads()
    payloads.AddPayload(assetPath = "../Assets/conveyor_modules/conveyor_module_straight.usd")
    UsdGeom.Xformable(cross_conveyor_prim).AddTranslateOp().Set(Gf.Vec3d(x_position, y_position, 0))
    UsdGeom.Xformable(cross_conveyor_prim).AddRotateZOp().Set(-90)
