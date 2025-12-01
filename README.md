# Gas Furnace Digital Twin

Real-time digital twin of a gas-fired melting furnace with physics-based thermal model, combustion dynamics, PID control, and PyQt5 GUI.

## Run

```bash
python main.py
```

Dependencies: `PyQt5`, `matplotlib`. Install with `pip install -r requirements.txt` or `pip install PyQt5 matplotlib`.

## Physics Model

- Energy balance on molten metal + wall capacitance:  
  `dT/dt = (Q_comb - Q_loss - Q_load + Q_process) / C_total`
- Combustion: natural-gas lower heating value, stoichiometric ratio enforced by gas/air flows, efficiency drops with lambda deviation.
- Losses: convection `h*A*(T-T_amb)` and radiation `eps*sigma*A*(T^4 - T_amb^4)`.
- Disturbances: ambient drift (Ornstein–Uhlenbeck), stochastic heat load, additive process noise, measurement noise (Gaussian).
- Integration: RK4 each 80 ms for numerical stability.

## Control

- PID with tunable `Kp, Ki, Kd`, derivative on error/measurement, Tustin or backward-Euler integration, low-pass filtered derivative, integrator clamp and anti-windup.
- Air flow auto-computed to maintain stoichiometric ratio with bias; manual overrides for gas and air are available.

## Real-Time Loop

- `QTimer`-based loop targeting 80 ms; measures drift each cycle and displays warnings when timing deviates.
- Updates: PID -> gas/air flows -> physics integration -> GUI refresh.

## GUI Preview (textual)

```
+---------------------------------------------------------------+
|  Temperature Plot (setpoint dashed, furnace solid)            |
|                                                               |
|                                                               |
+-----------------------+-----------------+---------------------+
| Setpoint | PID | Furnace/Combustion | Disturbances | Status  |
|  target  | Kp  | manual gas/air     | toggles      | temp    |
|  profile | Ki  | efficiency         |               warnings |
| ramp/step| Kd  |                     |                      |
+---------------------------------------------------------------+
```
