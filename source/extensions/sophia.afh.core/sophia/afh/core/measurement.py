class EventLog:
    """Records failure events during a simulation run."""

    def __init__(self):
        """Initializes the EventLog."""
        self._events = []

    def reset(self):
        """Clears the recorded events."""
        self._events.clear()

    def record(self, event_type, time, location):
        """Records a failure event."""
        event = {"type": event_type, "time": time, "location": location}
        self._events.append(event)

    def get_events(self):
        """Returns the recorded events."""
        return self._events

class KPICollector:
    """Collects aggregate KPIs during a simulation run."""

    def __init__(self):
        self._spawned = 0
        self._completed = 0
        self._fallen = 0
        self._missed = 0
        self._diverted = 0
        self._jammed = 0
        self._transit_total = 0.0
        self._transit_count = 0
        self._diverter_travel = 0.0

    def record_spawn(self):
        self._spawned += 1

    def record_completion(self, transit_time):
        self._completed += 1
        self._transit_total += transit_time
        self._transit_count += 1

    def record_fall(self):
        self._fallen += 1

    def record_missed(self):
        self._missed += 1

    def record_diverted(self):
        self._diverted += 1

    def record_jammed(self):
        self._jammed += 1

    def record_diverter_travel(self, distance):
        self._diverter_travel += distance

    def get_KPI(self):
        """Return all KPIs as a dictionary."""
        read = {
            "Parcels Spawned": self._spawned,
            "Successful Transit": self._completed,
            "Fallen": self._fallen,
            "Missed": self._missed,
            "Diverted": self._diverted,
            "Diversion Success Rate": self._completed / self._diverted if self._diverted else 0.0,
            "Jammed": self._jammed,
            "Average Transit Time": self._transit_total / self._transit_count if self._transit_count else 0.0,
            "Diverter Travel": self._diverter_travel
        }

        return read

    def reset(self):
        """Zero all counters at the start of a run."""
        self._spawned = 0
        self._completed = 0
        self._fallen = 0
        self._missed = 0
        self._diverted = 0
        self._jammed = 0
        self._transit_total = 0.0
        self._transit_count = 0
        self._diverter_travel = 0.0