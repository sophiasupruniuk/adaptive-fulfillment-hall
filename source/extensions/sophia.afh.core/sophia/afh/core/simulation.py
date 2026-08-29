import omni.kit.app
import omni.usd
import random
from pxr import UsdGeom, Gf, PhysxSchema, UsdPhysics
from .measurement import EventLog, KPICollector
from .scene_generation import (
    load_config,
    generate_automation,
    generate_layout
)

class SimulationController:
    def __init__(self):
        self._time_since_spawn = 0.0
        self._spawn_rate_per_hour = 600
        self._subscription = None
        self._parcel_count = 0
        self._trigger_path = "/World/Layout/Conveyor/Diverter_Trigger"
        self._joint_path = "/World/Layout/Conveyor/Diverter/divider_arm/PusherJoint"
        self._run_time = 0.0
        self._event_log = EventLog()
        self._kpis = KPICollector()
        self._fallen = set()
        self._completed = set()
        self._missed = set()
        self._parcel_state = {}
        self._jammed = set()
        self._parcel_sizes = {}
        self._targeted_sizes = ("medium", "large")
        self._targeted = set()
        self._arm_state = "home"
        self._arm_timer = 0.0
        self._parcel_assets = ["../Assets/parcels/parcel_small.usd", "../Assets/parcels/parcel_medium.usd", "../Assets/parcels/parcel_large.usd", ]

    def start(self, spawn_rate_per_hour, speed, aisle_width, automation_level, seed):
        config = load_config()
        self._run_time = 0.0
        self._event_log.reset()
        self._kpis.reset()
        self._completed.clear()
        self._missed.clear()
        self._jammed.clear()
        self._fallen.clear()
        self._parcel_sizes.clear()
        self._parcel_state.clear()
        self._targeted.clear()
        self._spawn_rate_per_hour = spawn_rate_per_hour
        self._apply_aisle_width(aisle_width)
        self._apply_automation_level(automation_level)
        self._apply_conveyor_speed(speed)
        self._centreline_x = config["conveyor"]["outbound"]["centreline_x_m"]
        self._inbound_x = config["conveyor"]["inbound"]["centreline_x_m"]
        self._midpoint_x = (self._inbound_x + self._centreline_x) / 2
        self._belt_width = config["conveyor"]["belt_width_m"]
        self._belt_height = config["conveyor"]["belt_height_m"]
        self._drop_height = config["spawn"]["drop_height_m"]
        self._inbound_end = config["conveyor"]["inbound"]["start_y_m"]
        self._outbound_end = config["conveyor"]["outbound"]["end_y_m"]
        self._spawn_point = Gf.Vec3d(
            self._centreline_x - config["spawn"]["start_offset_x"],
            config["conveyor"]["outbound"]["start_y_m"] - config["spawn"]["start_offset_y"],
            self._belt_height + self._drop_height,
        )
        random.seed(seed)
        trigger_offset_m = config["diverter"]["trigger_offset_m"]
        arm_travel_time_s = config["diverter"]["arm_travel_time_s"]
        self._dwell_time = config["diverter"]["dwell_time_s"]
        self._retracted_position = config["diverter"]["retracted_position_m"]
        self._extended_position = config["diverter"]["extended_position_m"]
        ratio = config["conveyor"]["parcel_speed_ratio"]
        self._response_delay = max(0.0, trigger_offset_m / (speed * ratio) - arm_travel_time_s)
        stream = omni.kit.app.get_app().get_update_event_stream()
        self._subscription = stream.create_subscription_to_pop(self._on_update, name="Parcel Spawner")

    def stop(self):
        self._subscription = None
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        parcels = stage.GetPrimAtPath("/World/Parcel")
        if parcels.IsValid():
            stage.RemovePrim("/World/Parcel")


    def get_kpis(self):
        """Return the current KPI values."""
        return self._kpis.get_KPI()

    def generate(self, row_count, aisle_width, automation_level):
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return ["Stage not opened"]

        config = load_config()

        errors = generate_layout(stage, config, row_count)

        generate_automation(stage, config)

        self._apply_aisle_width(aisle_width)
        self._apply_automation_level(automation_level)

        return errors

    def _on_update(self, event):
        stage = omni.usd.get_context().get_stage()
        dt = event.payload["dt"]
        self._run_time += dt
        joint_prim = stage.GetPrimAtPath(self._joint_path)
        drive = UsdPhysics.DriveAPI(joint_prim, "linear") if joint_prim.IsValid() else None
        self._time_since_spawn += dt
        spawn_interval = 3600.0 / self._spawn_rate_per_hour

        if self._time_since_spawn >= spawn_interval:
            self._parcel_count += 1
            parcel = stage.DefinePrim(f"/World/Parcel/Parcel_{self._parcel_count:02d}", "Xform")
            payload = parcel.GetPayloads()
            asset = random.choice(self._parcel_assets)
            payload.AddPayload(asset)
            if "small" in asset:
                self._parcel_sizes[parcel.GetPath()] = "small"
            elif "medium" in asset:
                self._parcel_sizes[parcel.GetPath()] = "medium"
            else:
                self._parcel_sizes[parcel.GetPath()] = "large"
            UsdGeom.Xformable(parcel).AddTranslateOp().Set(self._spawn_point)
            self._time_since_spawn = 0.0
            self._kpis.record_spawn()
        trigger_prim = stage.GetPrimAtPath(self._trigger_path)
        parcels = []
        if trigger_prim.IsValid():
            state = PhysxSchema.PhysxTriggerStateAPI(trigger_prim)
            rel = state.GetTriggeredCollisionsRel()
            targets = rel.GetTargets() if rel else []
            parcels = [t for t in targets if "/World/Parcel/" in str(t)]

        if drive:
            if self._arm_state == "home":
                targeted = False
                for t in parcels:
                    parcel_path = t.GetParentPath()
                    if self._parcel_sizes.get(parcel_path) in self._targeted_sizes:
                        targeted = True
                        self._targeted.add(parcel_path)
                        self._kpis.record_targeted()
                        break
                if targeted:
                    self._arm_state = "waiting"
                    self._arm_timer = 0.0

            elif self._arm_state == "waiting":
                self._arm_timer += dt
                if self._arm_timer >= self._response_delay:
                    drive.CreateTargetPositionAttr().Set(self._extended_position)
                    self._arm_state = "extended"
                    self._arm_timer = 0.0
                    self._kpis.record_diverted()
                    self._kpis.record_diverter_travel(
                        abs(self._extended_position - self._retracted_position)
                    )

            elif self._arm_state == "extended":
                self._arm_timer += dt
                if self._arm_timer >= self._dwell_time and not parcels:
                    drive.CreateTargetPositionAttr().Set(self._retracted_position)
                    self._arm_state = "home"
                    self._kpis.record_diverter_travel(
                        abs(self._extended_position - self._retracted_position)
                    )

        get_parcel_path = stage.GetPrimAtPath("/World/Parcel")
        if not get_parcel_path.IsValid():
            return
        parcel_children = get_parcel_path.GetChildren()

        to_remove = []

        for parcel in parcel_children:
            parcel_transform = parcel.GetAttribute("xformOp:translate").Get()
            if parcel_transform[2] < 0.6 and parcel.GetPath() not in self._fallen:
                self._fallen.add(parcel.GetPath())
                self._event_log.record("fall", self._run_time, parcel_transform)
                self._kpis.record_fall()
                to_remove.append(parcel.GetPath())

            if parcel_transform[1] >= self._inbound_end:
                self._completed.add(parcel.GetPath())
                self._event_log.record("Completed", self._run_time, parcel_transform)
                tracked = self._parcel_state.get(parcel.GetPath())
                transit = self._run_time - tracked["spawn_time"] if tracked else 0.0
                self._kpis.record_completion(transit, parcel.GetPath() in self._targeted)
                to_remove.append(parcel.GetPath())
            elif parcel_transform[1] <= self._outbound_end:
                self._missed.add(parcel.GetPath())
                self._event_log.record("Missed", self._run_time, parcel_transform)
                self._kpis.record_missed()
                to_remove.append(parcel.GetPath())

            if parcel.GetPath() not in self._parcel_state:
                self._parcel_state[parcel.GetPath()] = {
                    "last_pos": parcel_transform,
                    "still_time": 0.0,
                    "spawn_time": self._run_time,
                }
            else:
                last = self._parcel_state[parcel.GetPath()]["last_pos"]
                moved = (parcel_transform - last).GetLength()
                if moved < 0.01:
                    self._parcel_state[parcel.GetPath()]["still_time"] += dt
                else:
                    self._parcel_state[parcel.GetPath()]["still_time"] = 0.0
                self._parcel_state[parcel.GetPath()]["last_pos"] = parcel_transform

        for path in to_remove:
            stage.RemovePrim(path)
            self._parcel_state.pop(path, None)
            self._fallen.discard(path)
            self._jammed.discard(path)
            self._targeted.discard(path)
            self._parcel_sizes.pop(path, None)

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
                    self._kpis.record_jammed()

    def _apply_conveyor_speed(self, speed):
        stage = omni.usd.get_context().get_stage()
        config = load_config()
        unit = {"+y": (0, 1, 0), "-y": (0, -1, 0), "+x": (1, 0, 0), "-x": (-1, 0, 0)}
        for run_name in ["inbound", "outbound", "cross"]:
            direction = config ["conveyor"][run_name]["direction"]
            u = unit[direction]
            velocity = Gf.Vec3f(u[0] * speed, u[1] * speed, u[2] * speed)
            run_prim = stage.GetPrimAtPath(f"/World/Layout/Conveyor/{run_name}")
            if not run_prim.IsValid():
                continue
            for segment in run_prim.GetChildren():
                if not segment.IsValid():
                    continue
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