import omni.ui as ui

class ControlPanel:
    """Creates a Control Panel window for the Adaptive Fulfillment Hall simulation."""

    def __init__(self, controller):
        self._controller = controller
        def on_run():
            rate = self._rate_slider.model.get_value_as_int()
            speed = self._speed_slider.model.get_value_as_float()
            aisle_width = self._aisle_width_option.model.get_item_value_model().get_value_as_int()
            automation_level = self._automation_level_option.model.get_item_value_model().get_value_as_int()
            seed = self._seed_field.model.get_value_as_int()
            self._controller.start(rate, speed, aisle_width, automation_level, seed)

        def on_stop():
            self._controller.stop()

        def on_generate():
            rows = self._rows_slider.model.get_value_as_int()
            aisle_width = self._aisle_width_option.model.get_item_value_model().get_value_as_int()
            automation_level = self._automation_level_option.model.get_item_value_model().get_value_as_int()
            errors = self._controller.generate(rows, aisle_width, automation_level)
            if errors:
                self._status_label.text = "\n".join(errors)
            else:
                self._status_label.text = f"Generated {rows} rows"

        self._window = ui.Window("Adaptive Fulfillment Hall", width=300, height=300)
        with self._window.frame:
            with ui.VStack():
                ui.Label("Parcel Arrival Rate (per hour):")
                self._rate_slider = ui.IntSlider(min=200, max=1200)
                self._rate_slider.model.set_value(600)
                ui.Label("Conveyor Speed (m/s):")
                self._speed_slider = ui.FloatSlider(min=0.5, max=2.0)
                self._speed_slider.model.set_value(1.2)
                ui.Label("Aisle Width:")
                self._aisle_width_option = ui.ComboBox(0, "Narrow", "Wide")
                ui.Label("Automation Level:")
                self._automation_level_option = ui.ComboBox(0, "Manual", "Conveyor", "ConveyorPlusDiverter")
                ui.Label("Random Seed:")
                self._seed_field = ui.IntField()
                self._seed_field.model.set_value(22)
                ui.Label("Rack Rows:")
                self._rows_slider = ui.IntSlider(min = 4, max = 12)
                self._rows_slider.model.set_value(6)
                self._status_label = ui.Label("")
                ui.Button("Generate Layout", clicked_fn = on_generate)
                ui.Button("Run", clicked_fn=on_run)
                ui.Button("Stop", clicked_fn=on_stop)

    def destroy(self):
        """Destroys the Control Panel window."""
        self._window.destroy()
        self._window = None