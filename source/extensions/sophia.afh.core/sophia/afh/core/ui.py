import omni.ui as ui
import omni.kit.app

class ControlPanel:
    """Creates a Control Panel window for the Adaptive Fulfillment Hall simulation."""

    def __init__(self, controller):
        """Build the panel and wire its buttons to the simulation controller.

        The controller is passed in rather than created here, so the panel
        drives the same simulation the extension already owns.
        """
        self._controller = controller

        def on_run():
            """Read every parameter from the panel and start a run."""
            rate = self._rate_slider.model.get_value_as_int()
            speed = self._speed_slider.model.get_value_as_float()
            aisle_width = self._aisle_width_option.model.get_item_value_model().get_value_as_int()
            automation_level = self._automation_level_option.model.get_item_value_model().get_value_as_int()
            seed = self._seed_field.model.get_value_as_int()
            duration = self._duration_slider.model.get_value_as_float()
            scenario = self._scenario_field.model.get_value_as_string()
            self._controller.start(rate, speed, aisle_width, automation_level, seed, duration, scenario)

        def on_stop():
            """End the run and clear any parcels still in the scene."""
            self._controller.stop()

        def on_export():
            """Write the finished run's results and event log to CSV."""
            name = self._scenario_field.model.get_value_as_string()
            results, events = self._controller.export(name)
            self._status_label.text = f"Exported to {results}"

        def on_generate():
            """Build the layout, reporting any refusal or row-count warning."""
            rows = self._rows_slider.model.get_value_as_int()
            aisle_width = self._aisle_width_option.model.get_item_value_model().get_value_as_int()
            automation_level = self._automation_level_option.model.get_item_value_model().get_value_as_int()
            errors = self._controller.generate(rows, aisle_width, automation_level)
            if errors:
                self._status_label.text = "\n".join(errors)
            else:
                self._status_label.text = f"Generated {rows} rows in both variants"

        self._window = ui.Window("Adaptive Fulfillment Hall", width=300, height=300)
        with self._window.frame:
            with ui.VStack():
                # Layout parameters, applied when the layout is generated.
                ui.Label("Aisle Width:")
                self._aisle_width_option = ui.ComboBox(0, "Narrow", "Wide")
                ui.Label("Automation Level:")
                self._automation_level_option = ui.ComboBox(0, "Manual", "Conveyor", "ConveyorPlusDiverter")
                ui.Label("Rack Rows:")
                self._rows_slider = ui.IntSlider(min=4, max=12)
                self._rows_slider.model.set_value(6)
                self._status_label = ui.Label("")
                ui.Button("Generate Layout", clicked_fn=on_generate)

                # Run parameters, applied when a run starts.
                ui.Label("Parcel Arrival Rate (per hour):")
                self._rate_slider = ui.IntSlider(min=200, max=1200)
                self._rate_slider.model.set_value(600)
                ui.Label("Conveyor Speed (m/s):")
                self._speed_slider = ui.FloatSlider(min=0.5, max=2.0)
                self._speed_slider.model.set_value(1.2)
                ui.Label("Random Seed:")
                self._seed_field = ui.IntField()
                self._seed_field.model.set_value(22)
                ui.Label("Simulation Duration (s):")
                self._duration_slider = ui.FloatSlider(min=60, max=600)
                self._duration_slider.model.set_value(300)
                ui.Button("Run", clicked_fn=on_run)
                ui.Button("Stop", clicked_fn=on_stop)

                # Live KPIs.
                self._kpi_label = ui.Label("")

                # Exporting the finished run.
                ui.Label("Scenario Name:")
                self._scenario_field = ui.StringField()
                self._scenario_field.model.set_value("baseline")
                ui.Button("Export Results", clicked_fn=on_export)

        self._kpi_timer =0.0

        def on_ui_update(event):
            """Refresh the KPI display once a second while a run is going."""
            self._kpi_timer += event.payload["dt"]
            if self._kpi_timer < 1.0:
                return
            self._kpi_timer =0.0
            kpis = self._controller.get_kpis()
            self._kpi_label.text = "\n".join(f"{k}: {round(v, 2)}" for k, v in kpis.items())

        stream = omni.kit.app.get_app().get_update_event_stream()
        self._kpi_subscription = stream.create_subscription_to_pop(on_ui_update, name="KPI Display")

    def destroy(self):
        """Destroys the Control Panel window."""
        self._window.destroy()
        self._window = None
        self._kpi_subscription = None