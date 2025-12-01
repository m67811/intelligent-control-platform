"""Dynamic thermal model of a gas-fired melting furnace."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .combustion import CombustionModel, CombustionParams
from .disturbances import DisturbanceModel


@dataclass
class FurnaceParams:
    """Thermal and geometric properties of the furnace."""

    capacity_j_per_k: float = 7.5e5  # Effective heat capacity of molten metal + walls
    surface_area_m2: float = 12.0
    convection_coeff_w_m2k: float = 38.0
    emissivity: float = 0.82
    ambient_temp_k: float = 298.15  # Initial ambient


class FurnaceModel:
    """Represents furnace thermal dynamics using an energy balance."""

    def __init__(
        self,
        params: FurnaceParams | None = None,
        combustion: CombustionModel | None = None,
        disturbances: DisturbanceModel | None = None,
    ) -> None:
        self.params = params or FurnaceParams()
        self.combustion = combustion or CombustionModel(CombustionParams())
        self.disturbances = disturbances or DisturbanceModel()
        self.temperature_k = self.params.ambient_temp_k + 150.0  # start warm
        self.sigma = 5.670374419e-8  # Stefan-Boltzmann

    @property
    def temperature_c(self) -> float:
        """Current molten metal temperature in Celsius."""
        return self.temperature_k - 273.15

    def _heat_losses(self, temp_k: float, ambient_k: float) -> float:
        """Compute convective and radiative heat losses."""
        delta_t = max(0.0, temp_k - ambient_k)
        q_conv = (
            self.params.convection_coeff_w_m2k
            * self.params.surface_area_m2
            * delta_t
        )
        q_rad = (
            self.params.emissivity
            * self.sigma
            * self.params.surface_area_m2
            * (temp_k**4 - ambient_k**4)
        )
        return q_conv + q_rad

    def _derivative(
        self,
        temp_k: float,
        gas_flow: float,
        air_flow: float,
        ambient_k: float,
        heat_load_w: float,
        process_bias_w: float,
    ) -> float:
        """Energy balance derivative dT/dt."""
        q_in, lam = self.combustion.heat_release(gas_flow, air_flow)
        q_losses = self._heat_losses(temp_k, ambient_k)
        return (q_in - q_losses - heat_load_w + process_bias_w) / self.params.capacity_j_per_k

    def step(
        self, dt: float, gas_flow: float, air_flow: float
    ) -> dict[str, float]:
        """Advance the furnace state by dt seconds using RK4 integration."""
        self.disturbances.update()
        ambient_k = self.disturbances.state.ambient_temp
        heat_load = self.disturbances.state.heat_load
        process_bias = self.disturbances.state.process_bias

        def f(temp: float) -> float:
            return self._derivative(
                temp, gas_flow, air_flow, ambient_k, heat_load, process_bias
            )

        k1 = f(self.temperature_k)
        k2 = f(self.temperature_k + 0.5 * dt * k1)
        k3 = f(self.temperature_k + 0.5 * dt * k2)
        k4 = f(self.temperature_k + dt * k3)
        self.temperature_k += (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

        q_in, lam = self.combustion.heat_release(gas_flow, air_flow)
        q_losses = self._heat_losses(self.temperature_k, ambient_k)
        measurement = self.temperature_c + self.disturbances.measurement_noise()

        return {
            "temperature_c": self.temperature_c,
            "measured_temp_c": measurement,
            "ambient_c": ambient_k - 273.15,
            "heat_input_w": q_in,
            "heat_losses_w": q_losses,
            "heat_load_w": heat_load,
            "lambda": lam,
        }
