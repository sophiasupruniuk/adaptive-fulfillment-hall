import omni.usd
from pxr import Usd, UsdGeom, UsdPhysics, Gf, Sdf
import asyncio

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
    {"name": "Base", "length": 0.3, "radius": 0.35, "pivot_name": "base_pivot", "shape": "cylinder", "mass": 30.0},
    {"name": "Turntable", "length": 0.15, "radius": 0.30, "shape": "cylinder", "pivot_name": "BaseYaw", "mass": 8.0, "stiffness": 200000.0, "damping": 20000.0, "max_force": 200000.0, "axis": "Z"},
    {"name": "UpperArm", "length": 1.2, "radius": 0.1, "shape": "cylinder", "pivot_name": "Shoulder", "mass": 15.0, "stiffness": 200000.0, "damping": 20000.0, "max_force": 200000.0},
    {"name": "Forearm", "length": 0.9, "radius": 0.08, "shape": "cylinder", "pivot_name": "Elbow", "mass": 8.0, "stiffness":  120000.0, "damping":  12000.0, "max_force":  120000.0},
    {"name": "Gripper", "length": 0.2, "shape": "cube", "pivot_name": "Wrist", "mass": 2.0, "stiffness":  40000.0, "damping":  4000.0, "max_force":  40000.0},
]

poses = {
    "home":   {"Shoulder":  0.0, "Elbow":   0.0, "Wrist":  0.0, "BaseYaw": 0.0},
    "reach":  {"Shoulder": 75.0, "Elbow": 65.0, "Wrist": 15.0, "BaseYaw": 0.0},
    "lifted": {"Shoulder": 20.0, "Elbow": 30.0, "Wrist": 15.0, "BaseYaw": 0.0},

    "drop_A": {"BaseYaw": -60.0, "Shoulder": 60.0, "Elbow": 45.0, "Wrist": 15.0},
    "drop_B": {"BaseYaw":   90.0, "Shoulder": 60.0, "Elbow": 45.0, "Wrist": 15.0},
    "drop_C": {"BaseYaw":  60.0, "Shoulder": 60.0, "Elbow": 45.0, "Wrist": 15.0},
}
destination_poses = {"A": "drop_A", "B": "drop_B", "C": "drop_C"}

def create_robot_arm(stage, segments, root_path):
    if stage.GetPrimAtPath(root_path):
        stage.RemovePrim(root_path)

    robot_prim = UsdGeom.Xform.Define(stage, root_path)
    UsdPhysics.ArticulationRootAPI.Apply(robot_prim.GetPrim())

    joints_scope = UsdGeom.Scope.Define(stage, f"{root_path}/Joints")
    previous = None

    z_offset = 0
    bodies = {}
    joints = {}

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
            sphere = UsdGeom.Sphere.Define(stage, f"{body_path}/Sphere_prim")
            sphere.GetRadiusAttr().Set(0.08)
            sphere.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, segment["length"]/2.0))

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
            joints[segment["pivot_name"]] = joint_path
            joint = UsdPhysics.RevoluteJoint.Define(stage, joint_path)
            joint.CreateBody0Rel().SetTargets([bodies[previous["name"]]])
            joint.CreateBody1Rel().SetTargets([body_path])
            joint.CreateAxisAttr(segment.get("axis", "Y"))
            joint.CreateLocalPos0Attr(Gf.Vec3f(0.0, 0.0, previous["length"]/2))
            joint.CreateLocalPos1Attr(Gf.Vec3f(0.0, 0.0, -segment["length"]/2))
            joint.CreateLocalRot0Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
            joint.CreateLocalRot1Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
            joint.CreateLowerLimitAttr().Set(-90)
            joint.CreateUpperLimitAttr().Set(90)

            drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")
            drive.CreateTypeAttr("force")
            drive.CreateStiffnessAttr().Set(segment["stiffness"])
            drive.CreateDampingAttr().Set(segment["damping"])
            drive.CreateMaxForceAttr().Set(segment["max_force"])
            drive.CreateTargetPositionAttr(0.0)

        previous = segment
        z_offset += segment["length"]

    return bodies, joints

bodies, joints = create_robot_arm(stage, segments, "/World/RobotArm")
print(bodies, joints)

print(stage.GetRootLayer().ExportToString())

class RobotController:
    def __init__(self, stage, joints, poses):
        self.stage = stage
        self.joints = joints
        self.poses = poses

    def _drive(self, joint_name):
        prim = self.stage.GetPrimAtPath(self.joints[joint_name])
        if not prim.IsValid():
            print("Joint not found")
            return None
        return UsdPhysics.DriveAPI.Get(prim, "angular")

    def position(self, pose_name):
        if pose_name not in self.poses:
            print(f"Unkown pose:{pose_name}")
            return None

        for joint_name, angle in self.poses[pose_name].items():
            drive = self._drive(joint_name)
            if drive is not None:
                drive.GetTargetPositionAttr().Set(angle)

robot = RobotController(stage, joints, poses)

cycle = ["home", "reach", "lifted"]
step_index = 0

def next_step ():
    global step_index
    pose_name = cycle[step_index]
    robot.position(pose_name)
    step_index = (step_index + 1) % len(cycle)
    print(f"step > {pose_name}")

def parcel_spawn(stage, count):
    if stage.GetPrimAtPath("/World/Parcels"):
        stage.RemovePrim("/World/Parcels")

    destinations = ["A", "B", "C"]

    for i in range(count):
        parcel_path = f"/World/Parcels/parcel_{i:02d}"
        parcel = UsdGeom.Xform.Define(stage, f"/World/Parcels/parcel_{i:02d}")
        parcel_geom = UsdGeom.Cube.Define(stage, f"{parcel_path}/Geom")
        UsdPhysics.RigidBodyAPI.Apply(parcel.GetPrim())
        UsdPhysics.MassAPI.Apply(parcel.GetPrim()).CreateMassAttr().Set(0.5)
        UsdPhysics.CollisionAPI.Apply(parcel_geom.GetPrim())
        x = 1.4 + 0.25 * (i // 3)
        y = -0.25 + 0.25 * (i % 3)
        parcel.AddTranslateOp().Set(Gf.Vec3d(x, y, 0.1))
        parcel_geom.GetSizeAttr().Set(0.15)

        attr = parcel.GetPrim().CreateAttribute("sorting:destination", Sdf.ValueTypeNames.String)
        attr.Set(destinations[i % 3])

pickup_zone_centre = Gf.Vec3d(1.6, 0.0, 0.1)
pickup_zone_radius = 0.5

def world_position(stage, prim):
    xf = UsdGeom.Xformable(prim)
    return xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()

def find_parcels(stage):
    found = []
    for prim in stage.Traverse():
        if prim.HasAttribute("sorting:destination"):
            found.append(prim)

    return found

def in_pickup_zone(stage, prim):
    offset = world_position(stage, prim) - pickup_zone_centre
    return offset.GetLength() <= pickup_zone_radius

def parcels_in_zone(stage):
    return [p for p in find_parcels(stage) if in_pickup_zone(stage, p)]

def nearest_parcel(stage):
    candidates = [p for p in find_parcels(stage) if parcels_in_zone(stage)]
    if not candidates:
        return None
    return min(candidates,
            key=lambda p: (world_position(stage, p) - pickup_zone_centre).GetLength())

target = nearest_parcel(stage)
if target is None:
    print("Nothing in range")
else:
    print(f"Target {target.GetPath()} at {world_position(stage, target)}")

grip_joint_path = "/World/RobotArm/Joints/GripAttachment"

def grip(stage, gripper_path, parcel_prim):
    gripper_prim = stage.GetPrimAtPath(gripper_path)
    if not gripper_prim.IsValid() or not parcel_prim.IsValid():
        print("Gripper or parcel prim is invalid")
        return False

    joint = UsdPhysics.FixedJoint.Define(stage, grip_joint_path)
    joint.CreateBody0Rel().SetTargets([gripper_path])
    joint.CreateBody1Rel().SetTargets([parcel_prim.GetPath()])
    joint.CreateLocalPos0Attr(Gf.Vec3d(0.175, 0, 0))
    joint.CreateLocalPos1Attr(Gf.Vec3d(0, 0, 0))
    joint.CreateLocalRot0Attr(Gf.Quatf(1, 0, 0, 0))
    joint.CreateLocalRot1Attr(Gf.Quatf(1, 0, 0, 0))
    filter_api = UsdPhysics.FilteredPairsAPI.Apply(gripper_prim)
    filter_api.CreateFilteredPairsRel().AddTarget(parcel_prim.GetPath())

    print(f"Holding {parcel_prim.GetPath()}")
    return True

def parcel_destination(prim):
    attr = prim.GetAttribute("sorting:destination")
    if not attr.IsValid():
        print(f"{prim.GetPath()} has no destination attribute")
        return None
    return attr.Get()

def release(stage, gripper_path):
    gripper_prim = stage.GetPrimAtPath(gripper_path)
    if gripper_prim.IsValid():
        UsdPhysics.FilteredPairsAPI.Apply(gripper_prim).CreateFilteredPairsRel().ClearTargets(True)
    if stage.GetPrimAtPath(grip_joint_path):
        stage.RemovePrim(grip_joint_path)
        print("Grip released")

async def sort_one_parcel():
    target = nearest_parcel(stage)
    if target is None:
        print("Nothing in the pickup zone")
        return False

    destination = parcel_destination(target)

    if destination not in destination_poses:
        print(f"unknown destination {destination!r}, skipping")
        return False

    print(f"{target.GetPath()} -> {destination}")

    robot.position("reach")
    await asyncio.sleep(2.0)

    if not grip(stage, bodies["Gripper"], target):
        return False
    await asyncio.sleep(0.5)

    robot.position("lifted")
    await asyncio.sleep(2.0)

    robot.position(destination_poses[destination])
    await asyncio.sleep(3.0)

    release(stage, bodies["Gripper"])
    await asyncio.sleep(1.0)

    robot.position("home")
    await asyncio.sleep(2.0)

    return True

async def sort_all():
    while await sort_one_parcel():
        pass
    print("pickup zone clear")

sort_task = None

def start_sorting():
    global sort_task
    if sort_task is not None and not sort_task.done():
        print("Sort already running")
        return
    sort_task = asyncio.ensure_future(sort_all())

def stop_sorting():
    global sort_task
    if sort_task is not None:
        sort_task.cancel()
        sort_task = None
        print("[sort] stopped")
