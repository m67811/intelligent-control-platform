"""Disturbance models for the furnace simulation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class DisturbanceToggles:
    """Enables or disables each disturbance component."""

    ambient_drift: bool = True
    measurement_noise: bool = True
    heat_load: bool = True
    process_noise: bool = True


@dataclass
class DisturbanceState:
    """Mutable disturbance state."""

    ambient_temp: float = 298.15  # K
    heat_load: float = 15_000.0  # W of heat draw from molten metal
    noise_bias: float = 0.0
    process_bias: float = 0.0


@dataclass
class DisturbanceParams:
    """Parameterization of disturbance dynamics."""

    ambient_drift_std: float = 0.05  # K per step random walk
    ambient_reversion: float = 0.001  # pulls drift back to nominal
    measurement_noise_std: float = 0.75  # K standard deviation
    heat_load_std: float = 1200.0  # W
    process_noise_std: float = 400.0  # W additive to heat balance
    nominal_ambient: float = 298.15  # K (25 C)


class DisturbanceModel:
    """Generates disturbances for the furnace model."""

    def __init__(
        self,
        toggles: DisturbanceToggles | None = None,
        params: DisturbanceParams | None = None,
    ) -> None:
        self.toggles = toggles or DisturbanceToggles()
        self.params = params or DisturbanceParams()
        self.state = DisturbanceState(ambient_temp=self.params.nominal_ambient)

    def update(self) -> None:
        """Evolve slow disturbances (ambient drift and load changes)."""
        if self.toggles.ambient_drift:
            drift = random.gauss(0.0, self.params.ambient_drift_std)
            # Ornstein-Uhlenbeck style pull toward nominal ambient.
            pull = (
                self.params.ambient_reversion
                * (self.params.nominal_ambient - self.state.ambient_temp)
            )
            self.state.ambient_temp += drift + pull
        if self.toggles.heat_load:
            delta = random.gauss(0.0, self.params.heat_load_std)
            self.state.heat_load = max(0.0, 15_000.0 + delta)
        if self.toggles.process_noise:
            self.state.process_bias = random.gauss(0.0, self.params.process_noise_std)

    def measurement_noise(self) -> float:
        """Return measurement noise for temperature sensors."""
        if not self.toggles.measurement_noise:
            return 0.0
        return random.gauss(0.0, self.params.measurement_noise_std)
