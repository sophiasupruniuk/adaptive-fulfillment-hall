import asyncio
import omni.usd
from pxr import Usd, UsdGeom, UsdPhysics, Gf


class RobotController:
    """Drives the sorting arm: commands poses, grips parcels, stacks them on a rack.

    Poses are read from the config rather than hard-coded, so the arm can be
    retuned without touching this module. Gripping is done with a fixed joint
    authored at run time — a simulation shortcut, since contact-based grasping
    is unstable at this scale.
    """

    GRIP_JOINT_PATH = "/World/RobotArm/Joints/GripAttachment"

    def __init__(self, config, root_path="/World/RobotArm"):
        self._config = config
        self._root_path = root_path
        self._poses = config["robot"]["poses"]
        self._times = config["robot"]["move_time_s"]
        self._gripper_path = f"{root_path}/Gripper"
        self._placed = 0
        self._task = None
        self._state = "idle"
        self._simulation = None

    def _stage(self):
        return omni.usd.get_context().get_stage()

    def _drive(self, joint_name):
        """The angular drive on one joint, or None if the joint isn't there."""
        stage = self._stage()
        prim = stage.GetPrimAtPath(f"{self._root_path}/Joints/{joint_name}")
        if not prim.IsValid():
            print(f"[robot] no joint prim named {joint_name}")
            return None
        return UsdPhysics.DriveAPI.Get(prim, "angular")

    def go_to(self, pose_name, shoulder_offset=0.0):
        """Command every joint to the named pose's angles."""
        if pose_name not in self._poses:
            print(f"[robot] unknown pose {pose_name!r}")
            return
        for joint_name, angle in self._poses[pose_name].items():
            drive = self._drive(joint_name)
            if drive is None:
                continue
            if joint_name == "Shoulder":
                angle += shoulder_offset
            drive.GetTargetPositionAttr().Set(float(angle))
        self._state = pose_name

    def world_position(self, prim):
        xf = UsdGeom.Xformable(prim)
        return xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()

    def parcel_at_pickup(self):
        """The parcel queued at the end stop, or None if there isn't one."""
        stage = self._stage()
        zone = self._config["robot"]["pickup_zone"]
        centre = Gf.Vec3d(zone["centre_x_m"], zone["centre_y_m"], zone["centre_z_m"])
        radius = zone["radius_m"]

        group = stage.GetPrimAtPath("/World/Parcel")
        if not group.IsValid():
            return None

        candidates = []
        for parcel in group.GetChildren():
            translate = parcel.GetAttribute("xformOp:translate")
            if not translate.IsValid():
                continue
            if (translate.Get() - centre).GetLength() <= radius:
                candidates.append(parcel)

        if not candidates:
            return None
        return min(candidates,
                   key=lambda p: (p.GetAttribute("xformOp:translate").Get() - centre).GetLength())

    def grip(self, parcel_prim):
        """Weld a parcel to the gripper and stop the two colliding."""
        stage = self._stage()
        gripper = stage.GetPrimAtPath(self._gripper_path)
        if not gripper.IsValid() or not parcel_prim.IsValid():
            print("[robot] gripper or parcel invalid")
            return False

        offset = self._config["robot"]["grip_offset_m"]
        joint = UsdPhysics.FixedJoint.Define(stage, self.GRIP_JOINT_PATH)
        joint.CreateBody0Rel().SetTargets([self._gripper_path])
        joint.CreateBody1Rel().SetTargets([parcel_prim.GetPath()])
        joint.CreateLocalPos0Attr(Gf.Vec3f(offset["x"], offset["y"], offset["z"]))
        joint.CreateLocalPos1Attr(Gf.Vec3f(0.0, 0.0, 0.0))
        joint.CreateLocalRot0Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
        joint.CreateLocalRot1Attr(Gf.Quatf(1.0, 0.0, 0.0, 0.0))

        UsdPhysics.FilteredPairsAPI.Apply(gripper).CreateFilteredPairsRel().AddTarget(
            parcel_prim.GetPath())
        return True

    def release(self):
        """Remove the grip joint and clear the collision filter."""
        stage = self._stage()
        gripper = stage.GetPrimAtPath(self._gripper_path)
        if gripper.IsValid():
            UsdPhysics.FilteredPairsAPI.Apply(gripper).CreateFilteredPairsRel().ClearTargets(True)
        if stage.GetPrimAtPath(self.GRIP_JOINT_PATH):
            stage.RemovePrim(self.GRIP_JOINT_PATH)

    def set_simulation(self, simulation):
        self._simulation = simulation

    async def _sort_one(self):
        """One full cycle: pick the queued parcel, stack it, return home.

        Returns True if a parcel was placed, False if there was nothing to do.
        """
        parcel = self.parcel_at_pickup()
        if parcel is None:
            return False

        parcel_path = parcel.GetPath()
        print(f"[robot] picking {parcel_path}")

        self.go_to("reach")
        await asyncio.sleep(self._times["reach"])

        if not self.grip(parcel):
            return False
        await asyncio.sleep(self._times["grip"])

        self.go_to("lifted")
        await asyncio.sleep(self._times["lift"])

        self.go_to("transit")
        await asyncio.sleep(self._times["transit"])

        step = self._config["robot"]["drop_shoulder_step_deg"]
        capacity = self._config["robot"]["drop_capacity"]
        self.go_to("drop", shoulder_offset=step * (self._placed % capacity))
        await asyncio.sleep(self._times["drop"])

        self.release()
        if self._simulation is not None:
            self._simulation.mark_stored(parcel_path)
        self._placed += 1
        await asyncio.sleep(self._times["release"])

        self.go_to("transit")
        await asyncio.sleep(self._times["transit"])
        self.go_to("home")
        await asyncio.sleep(self._times["home"])
        return True

    async def _run(self):
        """Keep cycling: sort whatever arrives, wait when the run is empty."""
        self.go_to("home")
        await asyncio.sleep(2.0)
        while True:
            placed = await self._sort_one()
            if not placed:
                self._state = "waiting"
                await asyncio.sleep(1.0)

    def start(self):
        """Begin sorting, unless a cycle is already running."""
        if self._task is not None and not self._task.done():
            print("[robot] already running")
            return
        self._task = asyncio.ensure_future(self._run())

    def stop(self):
        """Cancel the cycle and drop anything held."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        self.release()
        self._state = "idle"

    def get_state(self):
        return self._state, self._placed