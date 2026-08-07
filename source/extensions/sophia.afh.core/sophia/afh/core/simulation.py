import omni.kit.app
import omni.usd
from pxr import UsdGeom, Gf, PhysxSchema, UsdPhysics

class SimulationController:
    def __init__(self):
        self._time_since_spawn = 0.0
        self._spawn_rate_per_hour = 600
        self._subscription = None
        self._parcel_count = 0
        self._trigger_path = "/World/Layout/Conveyor/DiverterTrigger"
        self._joint_path = "/World/Layout/Conveyor/Diverter/divider_arm/PusherJoint"
        self._arm_extended = False
        self._time_arm_extended = 0.0
        self._arm_extend_duration = 1.0


    def start(self):
        stream = omni.kit.app.get_app().get_update_event_stream()
        self._subscription = stream.create_subscription_to_pop(self._on_update, name="Parcel Spawner")

    def stop(self):
        self._subscription = None
        stage = omni.usd.get_context().get_stage()
        stage.RemovePrim("/World/Parcel")

    def _on_update(self, event):
        stage = omni.usd.get_context().get_stage()
        dt = event.payload["dt"]
        joint_prim = stage.GetPrimAtPath(self._joint_path)
        drive = UsdPhysics.DriveAPI(joint_prim, "linear")
        self._time_since_spawn += dt
        spawn_interval = 3600.0 / self._spawn_rate_per_hour
        if self._time_since_spawn >= spawn_interval:
            self._parcel_count += 1
            parcel = stage.DefinePrim(f"/World/Parcel/Parcel_{self._parcel_count:02d}", "Xform")
            payload = parcel.GetPayloads()
            payload.AddPayload(assetPath="../Assets/parcels/parcel_small.usd")
            UsdGeom.Xformable(parcel).AddTranslateOp().Set(Gf.Vec3d(22.7, 1.0, 2.0))
            self._time_since_spawn = 0.0
        trigger_prim = stage.GetPrimAtPath(self._trigger_path)
        state = PhysxSchema.PhysxTriggerStateAPI(trigger_prim)
        rel = state.GetTriggeredCollisionsRel()
        targets = rel.GetTargets() if rel else []
        if targets:
            drive.CreateTargetPositionAttr().Set(0.0)
        else:
            drive.CreateTargetPositionAttr().Set(-0.6)