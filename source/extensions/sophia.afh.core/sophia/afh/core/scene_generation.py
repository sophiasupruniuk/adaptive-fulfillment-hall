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
    for i in range(row_count):
        y_position = interior_min_y_m + i * (bay_depth_m + aisle_width_m)
        rack_prim = stage.DefinePrim(f"/World/Layout/Racks/Row_{i:02d}", "Xform")
        UsdGeom.Xformable(rack_prim).AddTranslateOp().Set(Gf.Vec3d(storage_start_x_m, y_position, 0))