import omni.usd
from pxr import Usd, UsdGeom, Gf

stage = omni.usd.get_context().get_stage()

UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)

world = UsdGeom.Xform.Define(stage, "/World")
stage.SetDefaultPrim(world.GetPrim())

base = {"name": "Base", "length": 0.2, "radius": 0.3}

segments = [
    {"name": "UpperArm", "length": 0.8, "radius": 0.08, "shape": "cylinder", "pivot_name": "Shoulder"},
    {"name": "Forearm", "length": 0.6, "radius": 0.06, "shape": "cylinder", "pivot_name": "Elbow"},
    {"name": "Gripper", "length": 0.15, "shape": "cube", "pivot_name": "Wrist"}
]

def create_robot_arm(stage, base,segments, root_path):
    if stage.GetPrimAtPath(root_path):
        stage.RemovePrim(root_path)

    UsdGeom.Xform.Define(stage, root_path)
    base_prim = UsdGeom.Cylinder.Define(stage, f"{root_path}/Base")
    base_prim.GetHeightAttr().Set(base["length"])
    base_prim.GetRadiusAttr().Set(base["radius"])
    base_prim.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, base["length"] / 2))

    present_path = root_path
    z_offset = base["length"]

    for segment in segments:
        segment_path = f"{present_path}/{segment['pivot_name']}"
        body_path = f"{segment_path}/{segment['name']}"
        pivot = UsdGeom.Xform.Define(stage, segment_path)
        pivot.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, z_offset))
        if segment["shape"] == "cylinder":
            tube = UsdGeom.Cylinder.Define(stage, body_path)
            tube.GetHeightAttr().Set(segment["length"])
            tube.GetRadiusAttr().Set(segment["radius"])
            tube.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, segment["length"] / 2))

        elif segment["shape"] == "cube":
            gripper = UsdGeom.Cube.Define(stage, body_path)
            gripper.GetSizeAttr().Set(segment["length"])
            gripper.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, segment["length"] / 2))

        present_path = segment_path
        z_offset = segment["length"]

    return present_path

end_path = create_robot_arm(stage, base, segments, "/World/RobotArm")

print(stage.GetRootLayer().ExportToString())