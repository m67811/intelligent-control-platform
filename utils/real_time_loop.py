"""Real-time loop utility backed by QTimer."""

from __future__ import annotations

import time
from typing import Callable

from PyQt5 import QtCore


class RealTimeLoop(QtCore.QObject):
    """Runs a periodic callback with drift estimation."""

    tick = QtCore.pyqtSignal(float, float)

    def __init__(self, interval_ms: int = 100) -> None:
        super().__init__()
        self.timer = QtCore.QTimer(self)
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self._on_tick)
        self.last_time = time.perf_counter()
        self.dt_target = interval_ms / 1000.0

    def start(self) -> None:
        """Start the timer loop."""
        self.last_time = time.perf_counter()
        self.timer.start(int(self.dt_target * 1000))

    def stop(self) -> None:
        """Stop the loop."""
        self.timer.stop()

    def set_interval_ms(self, interval_ms: int) -> None:
        """Update loop period."""
        self.dt_target = interval_ms / 1000.0
        if self.timer.isActive():
            self.timer.start(interval_ms)

    def _on_tick(self) -> None:
        """Handle timer tick, emitting elapsed dt and drift."""
        now = time.perf_counter()
        dt = now - self.last_time
        drift = dt - self.dt_target
        self.last_time = now
        self.tick.emit(dt, drift)
