# Setpoint tracking

Temperature setpoint steps from 80 °C to 120 °C at 30 s. Compares how quickly each controller reaches the new target.

| Metric | MPC | PID |
| --- | --- | --- |
| IAE | 1.82e+03 | 2.48e+03 |
| ISE | 4.3e+04 | 5.41e+04 |
| Overshoot [%] | 2.85 | 0 |
| Settling time [s] | 101 | 179 |
| Constraint violation steps | 0 | 0 |
| Energy [kWh] | 5.79 | 4.88 |
