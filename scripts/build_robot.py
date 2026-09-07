import omni.usd
from pxr import Usd, UsdGeom, UsdPhysics, Gf

stage = omni.usd.get_context().get_stage()

UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)

world = UsdGeom.Xform.Define(stage, "/World")
stage.SetDefaultPrim(world.GetPrim())

def create_physics_scene(stage):
    if stage.GetPrimAtPath("/World/PhysicsScene"):
        stage.RemovePrim("/World/PhysicsScene")
    scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
    scene.CreateGravityMagnitudeAttr().Set(9.81)

def create_ground_plane(stage):
    if stage.GetPrimAtPath("/World/Surface"):
        stage.RemovePrim("/World/Surface")
    surface = UsdGeom.Xform.Define(stage, "/World/Surface")
    surface_prim = UsdGeom.Cube.Define(stage, "/World/Surface/Plane")
    surface_prim.GetSizeAttr().Set(1.0)
    surface_prim.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.05))
    surface_prim.AddScaleOp().Set(Gf.Vec3d(10.0, 10.0, 0.1))
    UsdPhysics.CollisionAPI.Apply(surface_prim.GetPrim())

create_physics_scene(stage)
create_ground_plane(stage)

segments = [
    {"name": "Base", "length": 0.2, "radius": 0.3, "pivot_name": "base_pivot", "shape": "cylinder", "mass": 50.0},
    {"name": "UpperArm", "length": 0.8, "radius": 0.08, "shape": "cylinder", "pivot_name": "Shoulder", "mass": 20.0},
    {"name": "Forearm", "length": 0.6, "radius": 0.06, "shape": "cylinder", "pivot_name": "Elbow", "mass": 15.0},
    {"name": "Gripper", "length": 0.15, "shape": "cube", "pivot_name": "Wrist", "mass": 5.0},
]

def create_robot_arm(stage, segments, root_path):
    if stage.GetPrimAtPath(root_path):
        stage.RemovePrim(root_path)

    UsdGeom.Xform.Define(stage, root_path)

    joints_scope = UsdGeom.Scope.Define(stage, f"{root_path}/Joints")
    previous = None

    z_offset = 0
    bodies = {}

    for segment in segments:
        body_path = f"{root_path}/{segment['name']}"
        body = UsdGeom.Xform.Define(stage, body_path)
        UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
        UsdPhysics.MassAPI.Apply(body.GetPrim()).CreateMassAttr().Set(segment["mass"])
        body.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, z_offset + segment["length"] / 2.0))

        if segment["shape"] == "cylinder":
            tube = UsdGeom.Cylinder.Define(stage, f"{body_path}/Geom")
            tube.GetHeightAttr().Set(segment["length"])
            tube.GetRadiusAttr().Set(segment["radius"])
            UsdPhysics.CollisionAPI.Apply(tube.GetPrim())

        elif segment["shape"] == "cube":
            gripper = UsdGeom.Cube.Define(stage, f"{body_path}/Geom")
            gripper.GetSizeAttr().Set(segment["length"])
            UsdPhysics.CollisionAPI.Apply(gripper.GetPrim())

        joint_path = f"{root_path}/Joints/{segment['pivot_name']}"
        bodies[segment["name"]] = body_path

        if previous is None:
            weld = UsdPhysics.FixedJoint.Define(stage, joint_path)
            weld.CreateBody1Rel().SetTargets([f"{root_path}/Base"])

        else:
            joint = UsdPhysics.RevoluteJoint.Define(stage, joint_path)
            joint.CreateBody0Rel().SetTargets([bodies[previous["name"]]])
            joint.CreateBody1Rel().SetTargets([body_path])
            joint.CreateAxisAttr("Y")
            joint.CreateLocalPos0Attr(Gf.Vec3f(0.0, 0.0, previous["length"]/2))
            joint.CreateLocalPos1Attr(Gf.Vec3f(0.0, 0.0, -segment["length"]/2))
            joint.CreateLocalRot0Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
            joint.CreateLocalRot1Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
            joint.CreateLowerLimitAttr().Set(-90)
            joint.CreateUpperLimitAttr().Set(90)

        previous = segment
        z_offset += segment["length"]

    return bodies

bodies = create_robot_arm(stage, segments, "/World/RobotArm")
print(bodies)

print(stage.GetRootLayer().ExportToString())