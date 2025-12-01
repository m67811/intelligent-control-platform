"""PID controller implementation with configurable features."""

from __future__ import annotations

from dataclasses import dataclass

from utils.filters import LowPassFilter


@dataclass
class PIDConfig:
    """Configuration for PID controller."""

    kp: float = 5.0
    ki: float = 0.8
    kd: float = 0.0
    u_min: float = 0.0
    u_max: float = 1.5  # kg/s gas flow upper bound
    integrator_limit: float = 2.0
    derivative_filter_hz: float = 4.0
    use_tustin: bool = True
    derivative_on_measurement: bool = False


class PIDController:
    """PID with anti-windup, derivative filtering, and configurable discretization."""

    def __init__(self, config: PIDConfig | None = None) -> None:
        self.config = config or PIDConfig()
        self.integrator = 0.0
        self.prev_error = 0.0
        self.prev_measurement = 0.0
        self.filter = LowPassFilter(self.config.derivative_filter_hz)
        self.output = 0.0

    def reset(self) -> None:
        """Reset controller state."""
        self.integrator = 0.0
        self.prev_error = 0.0
        self.prev_measurement = 0.0
        self.filter.reset(0.0)
        self.output = 0.0

    def update(self, setpoint: float, measurement: float, dt: float) -> float:
        """Compute PID output."""
        if dt <= 0.0:
            return self.output
        error = setpoint - measurement
        # Proportional
        p = self.config.kp * error

        # Integral with selectable discretization.
        if self.config.use_tustin:
            self.integrator += 0.5 * self.config.ki * dt * (error + self.prev_error)
        else:
            self.integrator += self.config.ki * dt * error
        # Clamp integrator.
        self.integrator = max(
            -self.config.integrator_limit, min(self.config.integrator_limit, self.integrator)
        )

        # Derivative
        if self.config.derivative_on_measurement:
            derivative_raw = -(measurement - self.prev_measurement) / dt
        else:
            derivative_raw = (error - self.prev_error) / dt
        d_filtered = self.filter.update(derivative_raw, dt)
        d = self.config.kd * d_filtered

        u = p + self.integrator + d
        # Saturate and anti-windup: stop integrating when saturating in same direction.
        if u > self.config.u_max:
            u = self.config.u_max
            if error > 0:
                # Undo last integration step to avoid windup.
                self.integrator -= self.config.ki * dt * error
        elif u < self.config.u_min:
            u = self.config.u_min
            if error < 0:
                self.integrator -= self.config.ki * dt * error

        self.prev_error = error
        self.prev_measurement = measurement
        self.output = u
        return u

    def set_gains(self, kp: float, ki: float, kd: float) -> None:
        """Update controller gains at runtime."""
        self.config.kp = kp
        self.config.ki = ki
        self.config.kd = kd
        self.reset()
