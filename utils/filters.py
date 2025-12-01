"""Filter utilities used by controllers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LowPassFilter:
    """First-order low-pass filter."""

    cutoff_freq_hz: float = 10.0
    last_value: float = 0.0
    initialized: bool = False

    def reset(self, value: float = 0.0) -> None:
        """Reset filter state."""
        self.last_value = value
        self.initialized = False

    def update(self, value: float, dt: float) -> float:
        """Filter a new sample."""
        if not self.initialized:
            self.last_value = value
            self.initialized = True
            return value
        tau = 1.0 / (2.0 * 3.14159 * self.cutoff_freq_hz)
        alpha = dt / (tau + dt)
        self.last_value = self.last_value + alpha * (value - self.last_value)
        return self.last_value
