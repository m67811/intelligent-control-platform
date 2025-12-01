"""Supervisory control for the furnace simulation."""

from __future__ import annotations

from dataclasses import dataclass

from control.pid import PIDController, PIDConfig
from physics.combustion import CombustionParams


@dataclass
class RatioControlConfig:
    """Parameters for gas-air ratio control."""

    bias: float = 1.02  # Slightly lean to avoid CO
    min_air_flow: float = 0.1
    max_air_flow: float = 10.0


class GasAirRatioController:
    """Maintains air flow to respect stoichiometric ratio, with manual override."""

    def __init__(
        self,
        combustion_params: CombustionParams,
        config: RatioControlConfig | None = None,
    ) -> None:
        self.combustion_params = combustion_params
        self.config = config or RatioControlConfig()
        self.manual_override = False
        self.manual_air_flow = 1.5

    def compute(self, gas_flow: float) -> float:
        """Compute desired air flow."""
        if self.manual_override:
            return self.manual_air_flow
        air_flow = (
            gas_flow * self.combustion_params.stoich_air_fuel_ratio * self.config.bias
        )
        return max(self.config.min_air_flow, min(self.config.max_air_flow, air_flow))


class FurnaceController:
    """Coordinates PID temperature control and gas-air ratio management."""

    def __init__(self, pid: PIDController | None = None, ratio_ctrl: GasAirRatioController | None = None) -> None:
        self.pid = pid or PIDController(PIDConfig())
        self.ratio_ctrl = ratio_ctrl or GasAirRatioController(CombustionParams())
        self.manual_gas = False
        self.manual_gas_flow = 0.3
        self.setpoint_c = 750.0

    def set_setpoint(self, temp_c: float) -> None:
        """Update target temperature."""
        self.setpoint_c = temp_c

    def set_pid_gains(self, kp: float, ki: float, kd: float) -> None:
        """Apply new PID gains."""
        self.pid.set_gains(kp, ki, kd)

    def update(self, measured_temp_c: float, dt: float) -> dict[str, float]:
        """Return gas and air flow commands and controller diagnostics."""
        if self.manual_gas:
            gas_flow = self.manual_gas_flow
        else:
            gas_flow = self.pid.update(self.setpoint_c, measured_temp_c, dt)
        gas_flow = max(self.pid.config.u_min, min(self.pid.config.u_max, gas_flow))
        air_flow = self.ratio_ctrl.compute(gas_flow)

        return {
            "gas_flow": gas_flow,
            "air_flow": air_flow,
            "setpoint_c": self.setpoint_c,
            "controller_output": gas_flow,
        }
