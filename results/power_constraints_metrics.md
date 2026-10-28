# Power limits and rate constraints

Tight power cap (150 kW) and 8 kW/s move limit while requesting 165 °C. MPC anticipates the ceiling; PID often saturates and overshoots when limits bind.

| Metric | MPC | PID |
| --- | --- | --- |
| IAE | 9.48e+03 | 9.15e+03 |
| ISE | 5.34e+05 | 5.02e+05 |
| Overshoot [%] | 0 | 0 |
| Settling time [s] | 199 | 199 |
| Constraint violation steps | 0 | 6 |
| Energy [kWh] | 7.75 | 7.99 |
