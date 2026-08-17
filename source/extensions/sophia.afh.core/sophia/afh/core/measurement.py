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