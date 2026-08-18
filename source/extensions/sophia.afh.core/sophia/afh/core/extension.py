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
from .ui import ControlPanel

class SimulationExtension(omni.ext.IExt):

    def on_startup(self, _ext_id):
        """This is called every time the extension is activated."""
        print("[sophia.afh.core] Extension startup")
        self._simulation_controller = SimulationController()
        self._control_panel = ControlPanel()

    def on_shutdown(self):
        """This is called every time the extension is deactivated. It is used
        to clean up the extension state."""
        print("[sophia.afh.core] Extension shutdown")
        self._simulation_controller.stop()
        self._simulation_controller = None
        self._control_panel.destroy()
        self._control_panel = None
