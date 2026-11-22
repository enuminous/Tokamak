# Implementation corrections and additional diagnostics

2026-11-22, after coarse/fine modes and first open-loop evolution, before corrected time and feedback runs:

1. Concurrent executor processes reused a PID while sharing /tmp; OFT's PID-only temporary directory collided. The eta2 and original open-dt10 attempts failed before physics. Each run now uses its own randomly named working directory and OFT local_dir temporary mode. Original failure outputs and both code versions are retained.
2. The first isolated open-loop trajectory recorded an almost zero initial axis displacement because set_psi defaults to update_bounds=False. This is a stale initial diagnostic, not a zero physical seed. Explicitly update bounds when seeding, before initial sampling. Keep the original output. Initial flux amplitude, gain grid and acceptance limits are unchanged.
3. Add a zero-seed trajectory and a negative-seed open-loop trajectory at the fine time step. These diagnose equilibrium drift and seed-sign sensitivity if linear/time agreement fails. They do not replace the frozen primary growth-rate comparison, and no tolerance is relaxed.

The initial isolated open-loop fit was 802.146/s versus the 945.978/s eigenvalue: it fails the 10% first-e-folding comparison. The corrected result and all diagnostic outcomes will be reported separately.

After corrected dt=0.1/gamma and dt=0.05/gamma results (802.146/s and 784.789/s), before the following diagnostic: also compute the linear spectrum with include_bounds=True to test whether the documented fixed-bounds approximation explains the discrepancy. This is a separate model-setting diagnostic, not a replacement for the failed primary comparison.

The initial reduced-burn tolerance comparison used only final energy, which was fixed by the termination boundary. Replace that insufficient numerical check with the maximum dense-trajectory difference at 101 common times and the termination-time difference (limits 1e-6 in temperature scale and 1e-5 s). This does not change the model, primary results or physical interpretation.

The include_bounds=True diagnostic gives 807.703/s, much closer to the measured time-domain rates. Before further runs, add two time-domain comparisons seeded with that eigenmode at dt=0.05/gamma and 0.025/gamma, using the original 10% rate and 5% timestep criteria as diagnostic checks. Preserve the original two fixed-bounds comparison failures. These are explanatory reruns, not preregistered primary results.
