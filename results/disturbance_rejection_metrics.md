# Disturbance rejection

At 70 s the effective heat loss increases (U step) while the setpoint stays at 115 °C. Offset-free MPC updates its disturbance estimate; PID must react only through feedback.

| Metric | MPC | PID |
| --- | --- | --- |
| IAE | 955 | 1.09e+03 |
| ISE | 1.08e+04 | 1.36e+04 |
| Overshoot [%] | 2.93 | 0.0251 |
| Settling time [s] | 62 | 103 |
| Constraint violation steps | 0 | 0 |
| Energy [kWh] | 3.81 | 3.56 |
