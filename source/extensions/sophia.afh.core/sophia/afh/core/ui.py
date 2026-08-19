import omni.ui as ui

class ControlPanel:
    """Creates a Control Panel window for the Adaptive Fulfillment Hall simulation."""

    def __init__(self, controller):
        self._controller = controller
        def on_run():
            rate = self._rate_slider.model.get_value_as_int()
            speed = self._speed_slider.model.get_value_as_float()
            self._controller.start(rate, speed)

        def on_stop():
            self._controller.stop()

        self._window = ui.Window("Adaptive Fulfillment Hall", width=300, height=300)
        with self._window.frame:
            with ui.VStack():
                ui.Label("Parcel Arrival Rate (per hour):")
                self._rate_slider = ui.IntSlider(min=200, max=1200)
                self._rate_slider.model.set_value(600)
                ui.Label("Conveyor Speed (m/s):")
                self._speed_slider = ui.FloatSlider(min=0.5, max=2.0)
                self._speed_slider.model.set_value(1.2)
                ui.Button("Run", clicked_fn=on_run)
                ui.Button("Stop", clicked_fn=on_stop)

    def destroy(self):
        """Destroys the Control Panel window."""
        self._window.destroy()
        self._window = None