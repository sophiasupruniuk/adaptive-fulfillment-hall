import omni.kit.app

class SimulationController:
    def __init__(self):
        self._time_since_spawn = 0.0
        self._spawn_rate_per_hour = 600
        self._subscription = None

    def start(self):
        stream = omni.kit.app.get_app().get_update_event_stream()
        self._subscription = stream.create_subscription_to_pop(self._on_update, name="Parcel Spawner")

    def stop(self):
        self._subscription = None

    def _on_update(self, event):
        dt = event.payload["dt"]
        self._time_since_spawn += dt
        spawn_interval = 3600.0 / self._spawn_rate_per_hour
        if self._time_since_spawn >= spawn_interval:
            print("spawn")
            self._time_since_spawn = 0.0