import omni.kit.app
import omni.usd

class SimulationController:
    def __init__(self):
        self._time_since_spawn = 0.0
        self._spawn_rate_per_hour = 600
        self._subscription = None
        self._parcel_count = 0


    def start(self):
        stream = omni.kit.app.get_app().get_update_event_stream()
        self._subscription = stream.create_subscription_to_pop(self._on_update, name="Parcel Spawner")

    def stop(self):
        self._subscription = None
        stage = omni.usd.get_context().get_stage()
        stage.RemovePrim("/World/Parcel")

    def _on_update(self, event):
        dt = event.payload["dt"]
        self._time_since_spawn += dt
        spawn_interval = 3600.0 / self._spawn_rate_per_hour
        if self._time_since_spawn >= spawn_interval:
            self._parcel_count += 1
            stage = omni.usd.get_context().get_stage()
            parcel = stage.DefinePrim(f"/World/Parcel/Parcel_{self._parcel_count:02d}", "Xform")
            self._time_since_spawn = 0.0