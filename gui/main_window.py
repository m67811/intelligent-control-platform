"""Main window for the furnace digital twin GUI."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from control.controllers import FurnaceController, GasAirRatioController, RatioControlConfig
from control.pid import PIDConfig, PIDController
from physics.combustion import CombustionModel, CombustionParams
from physics.disturbances import DisturbanceModel, DisturbanceToggles
from physics.furnace_model import FurnaceModel, FurnaceParams
from utils.real_time_loop import RealTimeLoop
from gui.widgets import BarIndicator, IndicatorLight, LivePlot


class MainWindow(QtWidgets.QMainWindow):
    """Modern PyQt window orchestrating simulation and visualization."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gas Furnace Digital Twin")
        self.resize(1200, 720)

        combustion_params = CombustionParams()
        self.disturbances = DisturbanceModel()
        self.furnace = FurnaceModel(
            FurnaceParams(), CombustionModel(combustion_params), self.disturbances
        )
        pid = PIDController(PIDConfig())
        ratio_ctrl = GasAirRatioController(combustion_params, RatioControlConfig())
        self.controller = FurnaceController(pid=pid, ratio_ctrl=ratio_ctrl)

        self.sim_time = 0.0
        self.setpoint_target = self.controller.setpoint_c
        self.last_measured_temp = self.furnace.temperature_c

        self._build_ui()

        self.loop = RealTimeLoop(interval_ms=80)
        self.loop.tick.connect(self._on_tick)
        self.loop.start()

    # UI ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Assemble the overall layout."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        # Plot area
        self.plot = LivePlot(window_seconds=600.0, theme="dark")
        layout.addWidget(self.plot, stretch=3)

        # Control side panel
        side = QtWidgets.QVBoxLayout()
        layout.addLayout(side, stretch=2)

        side.addWidget(self._build_setpoint_panel())
        side.addWidget(self._build_pid_panel())
        side.addWidget(self._build_furnace_panel())
        side.addWidget(self._build_disturbance_panel())
        side.addWidget(self._build_status_panel())
        side.addStretch()

    def _build_setpoint_panel(self) -> QtWidgets.QGroupBox:
        """Create setpoint controls."""
        box = QtWidgets.QGroupBox("Setpoint")
        layout = QtWidgets.QGridLayout(box)
        self.setpoint_spin = QtWidgets.QDoubleSpinBox()
        self.setpoint_spin.setRange(400, 1300)
        self.setpoint_spin.setValue(self.controller.setpoint_c)
        self.setpoint_spin.setSuffix(" °C")
        self.setpoint_spin.setDecimals(1)
        layout.addWidget(QtWidgets.QLabel("Target"), 0, 0)
        layout.addWidget(self.setpoint_spin, 0, 1)

        self.profile_combo = QtWidgets.QComboBox()
        self.profile_combo.addItems(["Step", "Ramp"])
        self.ramp_rate_spin = QtWidgets.QDoubleSpinBox()
        self.ramp_rate_spin.setRange(0.1, 20.0)
        self.ramp_rate_spin.setValue(5.0)
        self.ramp_rate_spin.setSuffix(" °C/s")
        layout.addWidget(QtWidgets.QLabel("Profile"), 1, 0)
        layout.addWidget(self.profile_combo, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Ramp rate"), 2, 0)
        layout.addWidget(self.ramp_rate_spin, 2, 1)

        apply_btn = QtWidgets.QPushButton("Apply Setpoint")
        apply_btn.clicked.connect(self._apply_setpoint)
        layout.addWidget(apply_btn, 3, 0, 1, 2)
        return box

    def _build_pid_panel(self) -> QtWidgets.QGroupBox:
        """Create PID tuning controls."""
        box = QtWidgets.QGroupBox("PID Controller")
        layout = QtWidgets.QGridLayout(box)
        self.kp_spin = QtWidgets.QDoubleSpinBox()
        self.ki_spin = QtWidgets.QDoubleSpinBox()
        self.kd_spin = QtWidgets.QDoubleSpinBox()
        for spin in (self.kp_spin, self.ki_spin, self.kd_spin):
            spin.setRange(0.0, 50.0)
            spin.setDecimals(3)
            spin.setSingleStep(0.1)
        self.kp_spin.setValue(self.controller.pid.config.kp)
        self.ki_spin.setValue(self.controller.pid.config.ki)
        self.kd_spin.setValue(self.controller.pid.config.kd)
        layout.addWidget(QtWidgets.QLabel("Kp"), 0, 0)
        layout.addWidget(self.kp_spin, 0, 1)
        layout.addWidget(QtWidgets.QLabel("Ki"), 1, 0)
        layout.addWidget(self.ki_spin, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Kd"), 2, 0)
        layout.addWidget(self.kd_spin, 2, 1)

        self.deriv_mode = QtWidgets.QComboBox()
        self.deriv_mode.addItems(["On error", "On measurement"])
        self.deriv_mode.setCurrentIndex(0)
        layout.addWidget(QtWidgets.QLabel("Derivative mode"), 3, 0)
        layout.addWidget(self.deriv_mode, 3, 1)

        self.integrator_mode = QtWidgets.QComboBox()
        self.integrator_mode.addItems(["Tustin", "Backward Euler"])
        layout.addWidget(QtWidgets.QLabel("Integrator"), 4, 0)
        layout.addWidget(self.integrator_mode, 4, 1)

        apply = QtWidgets.QPushButton("Apply PID")
        reset = QtWidgets.QPushButton("Reset PID")
        apply.clicked.connect(self._apply_pid)
        reset.clicked.connect(self._reset_pid)
        layout.addWidget(apply, 5, 0)
        layout.addWidget(reset, 5, 1)

        self.pid_active_light = IndicatorLight()
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(QtWidgets.QLabel("Controller active"))
        hl.addWidget(self.pid_active_light)
        hl.addStretch()
        layout.addLayout(hl, 6, 0, 1, 2)

        self.output_bar = BarIndicator(maximum=self.controller.pid.config.u_max)
        layout.addWidget(QtWidgets.QLabel("Gas flow command [kg/s]"), 7, 0, 1, 2)
        layout.addWidget(self.output_bar, 8, 0, 1, 2)
        return box

    def _build_furnace_panel(self) -> QtWidgets.QGroupBox:
        """Create manual combustion controls."""
        box = QtWidgets.QGroupBox("Furnace & Combustion")
        layout = QtWidgets.QGridLayout(box)

        self.manual_gas_check = QtWidgets.QCheckBox("Manual gas")
        self.manual_gas_spin = QtWidgets.QDoubleSpinBox()
        self.manual_gas_spin.setRange(0.0, 1.5)
        self.manual_gas_spin.setDecimals(3)
        self.manual_gas_spin.setValue(0.3)
        self.manual_air_check = QtWidgets.QCheckBox("Manual air")
        self.manual_air_spin = QtWidgets.QDoubleSpinBox()
        self.manual_air_spin.setRange(0.1, 10.0)
        self.manual_air_spin.setDecimals(3)
        self.manual_air_spin.setValue(self.controller.ratio_ctrl.manual_air_flow)
        layout.addWidget(self.manual_gas_check, 0, 0)
        layout.addWidget(self.manual_gas_spin, 0, 1)
        layout.addWidget(self.manual_air_check, 1, 0)
        layout.addWidget(self.manual_air_spin, 1, 1)

        self.eff_label = QtWidgets.QLabel("Combustion efficiency: --")
        layout.addWidget(self.eff_label, 2, 0, 1, 2)
        return box

    def _build_disturbance_panel(self) -> QtWidgets.QGroupBox:
        """Create disturbance toggles."""
        box = QtWidgets.QGroupBox("Disturbances")
        layout = QtWidgets.QVBoxLayout(box)
        self.ambient_check = QtWidgets.QCheckBox("Ambient drift")
        self.ambient_check.setChecked(True)
        self.noise_check = QtWidgets.QCheckBox("Measurement noise")
        self.noise_check.setChecked(True)
        self.load_check = QtWidgets.QCheckBox("Heat load variations")
        self.load_check.setChecked(True)
        self.process_check = QtWidgets.QCheckBox("Process disturbances")
        self.process_check.setChecked(True)
        for w in (
            self.ambient_check,
            self.noise_check,
            self.load_check,
            self.process_check,
        ):
            layout.addWidget(w)
        return box

    def _build_status_panel(self) -> QtWidgets.QGroupBox:
        """Create status readouts."""
        box = QtWidgets.QGroupBox("Status")
        layout = QtWidgets.QGridLayout(box)
        self.temp_label = QtWidgets.QLabel("-- °C")
        self.sp_label = QtWidgets.QLabel("-- °C")
        self.error_label = QtWidgets.QLabel("-- °C")
        self.lambda_label = QtWidgets.QLabel("--")
        self.warning_label = QtWidgets.QLabel("")
        layout.addWidget(QtWidgets.QLabel("Furnace temp"), 0, 0)
        layout.addWidget(self.temp_label, 0, 1)
        layout.addWidget(QtWidgets.QLabel("Setpoint"), 1, 0)
        layout.addWidget(self.sp_label, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Control error"), 2, 0)
        layout.addWidget(self.error_label, 2, 1)
        layout.addWidget(QtWidgets.QLabel("Gas-air lambda"), 3, 0)
        layout.addWidget(self.lambda_label, 3, 1)
        layout.addWidget(QtWidgets.QLabel("Warning"), 4, 0)
        layout.addWidget(self.warning_label, 4, 1)
        return box

    # Callbacks -----------------------------------------------------------
    def _apply_setpoint(self) -> None:
        """Apply setpoint based on selected profile."""
        self.setpoint_target = self.setpoint_spin.value()
        if self.profile_combo.currentText() == "Step":
            self.controller.set_setpoint(self.setpoint_target)

    def _apply_pid(self) -> None:
        """Apply new PID gains and modes."""
        kp, ki, kd = self.kp_spin.value(), self.ki_spin.value(), self.kd_spin.value()
        self.controller.set_pid_gains(kp, ki, kd)
        self.controller.pid.config.derivative_on_measurement = (
            self.deriv_mode.currentIndex() == 1
        )
        self.controller.pid.config.use_tustin = self.integrator_mode.currentIndex() == 0
        self.pid_active_light.set_state(True)

    def _reset_pid(self) -> None:
        """Reset PID internal state."""
        self.controller.pid.reset()
        self.pid_active_light.set_state(False)

    def _apply_disturbance_toggles(self) -> None:
        """Update disturbance enable flags from UI."""
        toggles = DisturbanceToggles(
            ambient_drift=self.ambient_check.isChecked(),
            measurement_noise=self.noise_check.isChecked(),
            heat_load=self.load_check.isChecked(),
            process_noise=self.process_check.isChecked(),
        )
        self.disturbances.toggles = toggles

    def _on_tick(self, dt: float, drift: float) -> None:
        """Simulation + UI refresh."""
        self._apply_disturbance_toggles()
        self._update_setpoint_profile(dt)

        self.controller.manual_gas = self.manual_gas_check.isChecked()
        self.controller.manual_gas_flow = self.manual_gas_spin.value()
        self.controller.ratio_ctrl.manual_override = self.manual_air_check.isChecked()
        self.controller.ratio_ctrl.manual_air_flow = self.manual_air_spin.value()

        control = self.controller.update(self.last_measured_temp, dt)
        result = self.furnace.step(dt, control["gas_flow"], control["air_flow"])
        self.sim_time += dt
        self.last_measured_temp = result["measured_temp_c"]

        self._update_status(result, control, drift)
        self.plot.update_curve(self.sim_time, result["temperature_c"], control["setpoint_c"])

    def _update_setpoint_profile(self, dt: float) -> None:
        """Handle step or ramp setpoint shaping."""
        mode = self.profile_combo.currentText()
        if mode == "Step":
            # Setpoint already applied.
            return
        current = self.controller.setpoint_c
        target = self.setpoint_target
        if abs(target - current) < 1e-2:
            return
        rate = self.ramp_rate_spin.value()
        step = rate * dt
        if target > current:
            current = min(target, current + step)
        else:
            current = max(target, current - step)
        self.controller.set_setpoint(current)

    def _update_status(self, result: dict[str, float], control: dict[str, float], drift: float) -> None:
        """Refresh labels and warnings."""
        temp = result["measured_temp_c"]
        sp = control["setpoint_c"]
        error = sp - temp
        lam = result["lambda"]
        eff = self.furnace.combustion.efficiency(control["gas_flow"], control["air_flow"])

        self.temp_label.setText(f"{temp:0.1f} °C")
        self.sp_label.setText(f"{sp:0.1f} °C")
        self.error_label.setText(f"{error:+0.1f} °C")
        self.lambda_label.setText(f"{lam:0.2f}")
        self.output_bar.set_value(control["gas_flow"])
        self.eff_label.setText(f"Combustion efficiency: {eff*100:0.1f}%")

        warning = ""
        if lam < 0.95:
            warning = "Rich mix"
        elif lam > 1.10:
            warning = "Lean mix"
        elif abs(drift) > 0.05:
            warning = "Timing drift"
        self.warning_label.setText(warning)
