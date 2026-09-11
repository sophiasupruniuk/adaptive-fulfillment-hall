# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ext
import omni.ui as ui
from .simulation import SimulationController
from .scene_generation import load_config
from .robot import RobotController
from .ui import ControlPanel

class SimulationExtension(omni.ext.IExt):

    def on_startup(self, _ext_id):
        """This is called every time the extension is activated."""
        print("[sophia.afh.core] Extension startup")
        self._simulation_controller = SimulationController()
        self._robot = RobotController(load_config())
        self._robot.set_simulation(self._simulation_controller)
        self._simulation_controller.set_robot(self._robot)
        self._control_panel = ControlPanel(self._simulation_controller)

    def on_shutdown(self):
        """This is called every time the extension is deactivated. It is used
        to clean up the extension state."""
        print("[sophia.afh.core] Extension shutdown")
        self._robot.stop()
        self._robot = None
        self._simulation_controller.stop()
        self._simulation_controller = None
        self._control_panel.destroy()
        self._control_panel = None
