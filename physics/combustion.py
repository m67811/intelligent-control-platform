"""Combustion-related calculations for the furnace simulation."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class CombustionParams:
    """Parameters defining the fuel and air properties."""

    heating_value: float = 50e6  # J/kg of gas
    stoich_air_fuel_ratio: float = 17.2  # kg_air / kg_fuel for natural gas
    base_efficiency: float = 0.85  # nominal efficiency at stoichiometric mix
    efficiency_drop_per_lambda: float = 0.25  # efficiency loss when lambda deviates
    max_efficiency: float = 0.92
    min_efficiency: float = 0.6


class CombustionModel:
    """Models heat release from gas-air combustion."""

    def __init__(self, params: CombustionParams | None = None) -> None:
        self.params = params or CombustionParams()

    def effective_lambda(self, gas_flow: float, air_flow: float) -> float:
        """Return the air-fuel equivalence ratio lambda."""
        if gas_flow <= 1e-6:
            return 1.0
        return max(air_flow / (gas_flow * self.params.stoich_air_fuel_ratio), 1e-3)

    def efficiency(self, gas_flow: float, air_flow: float) -> float:
        """Compute combustion efficiency as a function of lambda deviation."""
        lam = self.effective_lambda(gas_flow, air_flow)
        deviation = abs(lam - 1.0)
        drop = deviation * self.params.efficiency_drop_per_lambda
        eff = self.params.base_efficiency * (1.0 - drop)
        return float(
            min(self.params.max_efficiency, max(self.params.min_efficiency, eff))
        )

    def heat_release(self, gas_flow: float, air_flow: float) -> Tuple[float, float]:
        """Return (thermal_power_watts, lambda)."""
        lam = self.effective_lambda(gas_flow, air_flow)
        eff = self.efficiency(gas_flow, air_flow)
        # Gas flow provided in kg/s, so thermal power is hv * gas_flow * efficiency.
        q_dot = self.params.heating_value * gas_flow * eff
        return q_dot, lam
