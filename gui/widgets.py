"""Reusable PyQt widgets for the furnace GUI."""

from __future__ import annotations

from collections import deque
from typing import Deque, Tuple

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtGui, QtWidgets


class LivePlot(FigureCanvasQTAgg):
    """Matplotlib canvas with rolling window for temperature data."""

    def __init__(self, window_seconds: float = 300.0, theme: str = "dark") -> None:
        self.fig = Figure(figsize=(6, 4), tight_layout=True)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.window_seconds = window_seconds
        self.theme = theme
        self._style()
        self.time_data: Deque[float] = deque()
        self.temp_data: Deque[float] = deque()
        self.setpoint_data: Deque[float] = deque()
        (self.temp_line,) = self.ax.plot([], [], color="#00e0ff", linewidth=2, label="Furnace")
        (self.sp_line,) = self.ax.plot([], [], color="#ffb347", linewidth=2, linestyle="--", label="Setpoint")
        self.ax.legend(loc="upper right")
        self.ax.set_xlabel("Time [s]")
        self.ax.set_ylabel("Temperature [°C]")
        self.ax.grid(True, alpha=0.3)

    def _style(self) -> None:
        """Apply simple theme styling."""
        if self.theme == "dark":
            self.fig.patch.set_facecolor("#1d1f21")
            self.ax.set_facecolor("#222629")
            self.ax.tick_params(colors="#d8d8d8")
            for spine in self.ax.spines.values():
                spine.set_color("#777")
            self.ax.yaxis.label.set_color("#d8d8d8")
            self.ax.xaxis.label.set_color("#d8d8d8")

    def update_curve(self, t: float, temp: float, setpoint: float) -> None:
        """Append new data and redraw."""
        self.time_data.append(t)
        self.temp_data.append(temp)
        self.setpoint_data.append(setpoint)
        # Remove old data to keep window bounded.
        while self.time_data and (self.time_data[-1] - self.time_data[0] > self.window_seconds):
            self.time_data.popleft()
            self.temp_data.popleft()
            self.setpoint_data.popleft()
        self.temp_line.set_data(self.time_data, self.temp_data)
        self.sp_line.set_data(self.time_data, self.setpoint_data)
        if self.time_data:
            self.ax.set_xlim(max(0.0, self.time_data[-1] - self.window_seconds), self.time_data[-1] + 1.0)
            y_min = min(min(self.temp_data, default=0), min(self.setpoint_data, default=0))
            y_max = max(max(self.temp_data, default=1), max(self.setpoint_data, default=1))
            pad = max(10.0, 0.1 * (y_max - y_min + 1e-3))
            self.ax.set_ylim(y_min - pad, y_max + pad)
        self.draw_idle()


class IndicatorLight(QtWidgets.QWidget):
    """Simple circular indicator light."""

    def __init__(self, color_on: str = "#5cb85c", color_off: str = "#444") -> None:
        super().__init__()
        self.color_on = color_on
        self.color_off = color_off
        self.on = False
        self.setFixedSize(18, 18)

    def set_state(self, on: bool) -> None:
        """Update indicator state."""
        self.on = on
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        """Draw the indicator."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        color = QtGui.QColor(self.color_on if self.on else self.color_off)
        painter.setBrush(QtGui.QBrush(color))
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        radius = min(self.width(), self.height()) // 2 - 2
        painter.drawEllipse(self.rect().center(), radius, radius)


class BarIndicator(QtWidgets.QProgressBar):
    """Horizontal bar used for control output visualization."""

    def __init__(self, maximum: float = 1.5) -> None:
        super().__init__()
        self.setMinimum(0)
        self.setMaximum(int(maximum * 100))
        self.setTextVisible(True)
        self.setFormat("%v")

    def set_value(self, value: float) -> None:
        """Update bar."""
        self.setValue(int(value * 100))
