import omni.ui as ui

class ControlPanel:
    """Creates a Control Panel window for the Adaptive Fulfillment Hall simulation."""

    def __init__(self, controller):
        self._controller = controller
        def on_click():
            self._controller.start()
        self._window = ui.Window("Adaptive Fulfillment Hall", width=300, height=300)
        with self._window.frame:

            with ui.VStack():
                ui.Button("Run", clicked_fn=on_click)

    def destroy(self):
        """Destroys the Control Panel window."""
        self._window.destroy()
        self._window = None