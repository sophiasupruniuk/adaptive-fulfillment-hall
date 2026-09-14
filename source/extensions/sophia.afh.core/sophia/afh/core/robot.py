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
    LINEAR_JOINT = "BaseSlide"

    def __init__(self, config, root_path="/World/RobotArm"):
        self._config = config
        self._root_path = root_path
        self._poses = config["robot"]["poses"]
        self._times = config["robot"]["move_time_s"]
        self._storage = config["robot"]["storage"]
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
        instance = "linear" if joint_name == self.LINEAR_JOINT else "angular"
        return UsdPhysics.DriveAPI.Get(prim, instance)

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

    def set_rail(self, position_m):
        """Drive the carriage to a position along the rail, in metres."""
        drive = self._drive(self.LINEAR_JOINT)
        if drive is not None:
            drive.GetTargetPositionAttr().Set(float(position_m))

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

    def _slot_rail(self, index):
        """The rail position that puts the carriage in front of slot `index`."""
        s = self._storage
        bay = index // s["slots_per_bay"]
        within = index % s["slots_per_bay"]
        bay_x = s["first_bay_x_m"] + bay * s["bay_width_m"]
        slot_x = bay_x + s["first_slot_offset_m"] + within * s["slot_spacing_m"]
        return slot_x - s["rail_origin_x_m"] + s["rail_offset_m"]

    def _slot_centre(self, index):
        """Where a parcel placed in slot `index` comes to rest, in world space."""
        s = self._storage
        bay = index // s["slots_per_bay"]
        within = index % s["slots_per_bay"]
        bay_x = s["first_bay_x_m"] + bay * s["bay_width_m"]
        x = bay_x + s["first_slot_offset_m"] + within * s["slot_spacing_m"]
        return Gf.Vec3d(x, s["shelf_y_m"], s["shelf_z_m"])

    def next_free_slot(self):
        """The lowest slot with no parcel resting in it.

        Occupancy is read from the scene, so a slot emptied by a picker
        becomes available again without the robot tracking it. Returns None
        when every slot is taken.
        """
        stage = self._stage()
        radius = self._storage["occupied_radius_m"]
        total = self._storage["bays"] * self._storage["slots_per_bay"]

        positions = []
        parcels = stage.GetPrimAtPath("/World/Parcel")
        if parcels.IsValid():
            for p in parcels.GetChildren():
                attr = p.GetAttribute("xformOp:translate")
                if attr.IsValid():
                    positions.append(attr.Get())

        for index in range(total):
            centre = self._slot_centre(index)
            if all((pos - centre).GetLength() > radius for pos in positions):
                return index
        return None

    def set_simulation(self, simulation):
        self._simulation = simulation

    async def _sort_one(self):
        """One full cycle: pick the queued parcel, rack it in the next free
        slot, return to the pickup point.

        The slot is the lowest one with nothing resting in it, read from the
        scene, so a slot emptied by a picker becomes available again.
        """
        parcel = self.parcel_at_pickup()
        if parcel is None:
            return False

        slot = self.next_free_slot()
        if slot is None:
            print("[robot] shelf is full")
            return False

        parcel_path = parcel.GetPath()
        print(f"[robot] picking {parcel_path} for slot {slot}")

        self.go_to("pick")
        await asyncio.sleep(self._times["reach"])

        if not self.grip(parcel):
            print("[robot] grip failed")
            return False
        print("[robot] gripped")
        await asyncio.sleep(self._times["grip"])

        self.go_to("home")
        print("[robot] home")
        await asyncio.sleep(self._times["lift"])

        self.set_rail(self._slot_rail(slot))
        print(f"[robot] rail -> {self._slot_rail(slot)}")
        await asyncio.sleep(self._times["rail"])

        self.go_to("transit")
        await asyncio.sleep(self._times["transit"])

        self.go_to("drop")
        await asyncio.sleep(self._times["drop"])

        self.release()
        self._placed += 1
        await asyncio.sleep(self._times["release"])

        self.go_to("transit")
        await asyncio.sleep(self._times["transit"])
        if self._simulation is not None:
            self._simulation.mark_stored(parcel_path)

        self.go_to("home")
        await asyncio.sleep(self._times["home"])

        self.set_rail(self._config["robot"]["pickup_rail_m"])
        await asyncio.sleep(self._times["rail"])
        return True

    async def _run(self):
        """Keep cycling: sort whatever arrives, wait when the run is empty."""
        print("[robot] _run entered")
        try:
            self.set_rail(self._config["robot"]["pickup_rail_m"])
            self.go_to("home")
            await asyncio.sleep(self._times["home"])
            while True:
                placed = await self._sort_one()
                if not placed:
                    self._state = "waiting"
                    await asyncio.sleep(1.0)
        except Exception as e:
            print(f"[robot] _run failed: {type(e).__name__}: {e}")
            raise


    def start(self):
        """Begin sorting, unless a cycle is already running."""
        print("[robot] start() called")
        if self._task is not None and not self._task.done():
            print("[robot] already running")
            return
        self._task = asyncio.ensure_future(self._run())
        print("[robot] task created")

    def stop(self):
        """Cancel the cycle and drop anything held."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        self.release()
        self._state = "idle"

    def get_state(self):
        return self._state, self._placed