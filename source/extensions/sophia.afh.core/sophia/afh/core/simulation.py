import omni.kit.app
import omni.usd
import random
from pxr import UsdGeom, Gf, PhysxSchema, UsdPhysics
from .measurement import EventLog
from .scene_generation import load_config

class SimulationController:
    def __init__(self):
        self._time_since_spawn = 0.0
        self._spawn_rate_per_hour = 600
        self._subscription = None
        self._parcel_count = 0
        self._trigger_path = "/World/Layout/Conveyor/DiverterTrigger"
        self._joint_path = "/World/Layout/Conveyor/Diverter/divider_arm/PusherJoint"
        self._run_time = 0.0
        self._event_log = EventLog()
        self._fallen = set()
        self._parcel_state = {}
        self._jammed = set()
        self._parcel_assets = ["../Assets/parcels/parcel_small.usd", "../Assets/parcels/parcel_medium.usd", "../Assets/parcels/parcel_large.usd"]

    def start(self, spawn_rate_per_hour, speed, aisle_width, automation_level, seed):
        self._run_time = 0.0
        self._event_log.reset()
        self._spawn_rate_per_hour = spawn_rate_per_hour
        self._apply_conveyor_speed(speed)
        self._apply_aisle_width(aisle_width)
        self._apply_automation_level(automation_level)
        random.seed(seed)
        stream = omni.kit.app.get_app().get_update_event_stream()
        self._subscription = stream.create_subscription_to_pop(self._on_update, name="Parcel Spawner")

    def stop(self):
        self._subscription = None
        stage = omni.usd.get_context().get_stage()
        stage.RemovePrim("/World/Parcel")

    def _on_update(self, event):
        stage = omni.usd.get_context().get_stage()
        dt = event.payload["dt"]
        self._run_time += dt
        joint_prim = stage.GetPrimAtPath(self._joint_path)
        drive = UsdPhysics.DriveAPI(joint_prim, "linear")
        self._time_since_spawn += dt
        spawn_interval = 3600.0 / self._spawn_rate_per_hour

        if self._time_since_spawn >= spawn_interval:
            self._parcel_count += 1
            parcel = stage.DefinePrim(f"/World/Parcel/Parcel_{self._parcel_count:02d}", "Xform")
            payload = parcel.GetPayloads()
            payload.AddPayload(random.choice(self._parcel_assets))
            UsdGeom.Xformable(parcel).AddTranslateOp().Set(Gf.Vec3d(22.7, 1.0, 2.0))
            self._time_since_spawn = 0.0
        trigger_prim = stage.GetPrimAtPath(self._trigger_path)
        state = PhysxSchema.PhysxTriggerStateAPI(trigger_prim)
        rel = state.GetTriggeredCollisionsRel()
        targets = rel.GetTargets() if rel else []
        parcels = [t for t in targets if "/World/Parcel/" in str(t)]

        if parcels:
            drive.CreateTargetPositionAttr().Set(0.0)
        else:
            drive.CreateTargetPositionAttr().Set(-0.6)

        get_parcel_path = stage.GetPrimAtPath("/World/Parcel")
        if not get_parcel_path.IsValid():
            return
        parcel_children = get_parcel_path.GetChildren()

        for parcel in parcel_children:
            parcel_transform = parcel.GetAttribute("xformOp:translate").Get()
            if parcel_transform[2] < 0.3 and parcel.GetPath() not in self._fallen:
                self._fallen.add(parcel.GetPath())
                self._event_log.record("fall", self._run_time, parcel_transform)

            if parcel.GetPath() not in self._parcel_state:
                self._parcel_state[parcel.GetPath()] = {"last_pos": parcel_transform, "still_time": 0.0}
            else:
                last = self._parcel_state[parcel.GetPath()]["last_pos"]
                moved = (parcel_transform - last).GetLength()
                if moved < 0.01:
                    self._parcel_state[parcel.GetPath()]["still_time"] += dt
                else:
                    self._parcel_state[parcel.GetPath()]["still_time"] = 0.0
                self._parcel_state[parcel.GetPath()]["last_pos"] = parcel_transform

        stalled = [path for path, s in self._parcel_state.items() if s["still_time"] > 3.0]
        for a in stalled:
            neighbors = 0
            for b in stalled:
                if a == b:
                    continue
                pos_a = self._parcel_state[a]["last_pos"]
                pos_b = self._parcel_state[b]["last_pos"]
                distance = (pos_a - pos_b).GetLength()
                if distance < 0.5:
                    neighbors += 1

            if neighbors >= 2:
                if a not in self._jammed:
                    self._jammed.add(a)
                    self._event_log.record("jam", self._run_time, self._parcel_state[a]["last_pos"])
                    print("JAM", self._run_time, a)

    def _apply_conveyor_speed(self, speed):
        print("APPLY SPEED CALLED, speed =", speed)
        stage = omni.usd.get_context().get_stage()
        config = load_config()
        unit = {"+y": (0, 1, 0), "-y": (0, -1, 0), "+x": (1, 0, 0), "-x": (-1, 0, 0)}
        for run_name in ["inbound", "outbound", "cross"]:
            direction = config ["conveyor"][run_name]["direction"]
            u = unit[direction]
            velocity = Gf.Vec3f(u[0] * speed, u[1] * speed, u[2] * speed)
            run_prim = stage.GetPrimAtPath(f"/World/Layout/Conveyor/{run_name}")
            print("   ", run_name, direction, run_prim.IsValid())
            if not run_prim.IsValid():
                continue
            for segment in run_prim.GetChildren():
                velocity_api = PhysxSchema.PhysxSurfaceVelocityAPI(segment)
                velocity_api.CreateSurfaceVelocityAttr().Set(velocity)
                velocity_api.CreateSurfaceVelocityLocalSpaceAttr().Set(False)

    def _apply_aisle_width(self, aisle_width):
        stage = omni.usd.get_context().get_stage()
        aisle_prim = stage.GetPrimAtPath("/World/Layout")
        names = ["Narrow", "Wide"]
        aisle_prim.GetVariantSet("AisleWidth").SetVariantSelection(names[aisle_width])

    def _apply_automation_level(self, automation_level):
        stage = omni.usd.get_context().get_stage()
        automation_prim = stage.GetPrimAtPath("/World/Layout")
        names = ["Manual", "Conveyor", "ConveyorPlusDiverter"]
        automation_prim.GetVariantSet("AutomationLevel").SetVariantSelection(names[automation_level])