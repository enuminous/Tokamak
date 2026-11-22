# OPENSTEP-006 — native reference benchmark and reactor requirements

Frozen before new physical calculations on 2026-11-22. This is a bounded computational assessment, not a construction design or an experimental validation. OPENSTEP-001–005 and their negative results remain unchanged.

## Native axisymmetric plasma/wall benchmark

Use OpenFUSIONToolkit 26.9, upstream reference 73d8eb09bce0a4f4c56b88f13fcf36f951c53e91, published DIII-D vessel polygons/resistivities, coils and EFIT g192185.02440. Reproduce the documented inverse, forward and edge-current-ramped equilibria. The ramp changes the physics of the final equilibrium and must be reported. Numerical vertical-position constraints used in equilibrium construction are not feedback hardware.

Generate the published mesh at original resolution and half all mesh length scales for a refinement check. Solve with second-order elements. Compute four passive-wall decay modes and ten plasma/wall eigenmodes near +5000/s, using the documented include_bounds=False setting. Positive real growth is unstable. Compare the leading real unstable mode with the upstream notebook value 945.98/s, allowing 10% (different meshing/environment). Require coarse/fine leading growth and slowest wall time within 10% to call this two-grid agreement; it is not continuum convergence. Double every vessel resistivity in a separate coarse case: wall times must halve within 0.1%; test whether the leading plasma growth doubles within 2% rather than assume it.

Seed the leading unstable mode at 0.0005 of the flux span. Evolve for two linear e-folding times using dt=0.1/gamma and dt=0.05/gamma in separate processes. Fit log absolute mode projection over the first e-folding interval; compare against eigenvalue within 10%, and compare fitted rates between time steps within 5%. Record any retries, changed timesteps and failure. Never treat a solver error as physical stability.

Explore ideal F9A/F9B antisymmetric current feedback using gains [-100000,-20000,0,20000,100000] A/m, correction clamp +/-500 A and slew limit 1e6 A/s, at dt=0.05/gamma for two e-folding times. Ideal measurement and prescribed coil currents are assumptions. Repeat the best final-displacement nonzero gain with 0.5 and 1.0 ms measurement delays. Selection is exploratory and disclosed. A control case screens as suppressing this perturbation only if final displacement <= initial and peak <= twice initial. No voltage, inductance, actual controller, noise or general MHD stability claim follows.

## STEP scenario feasibility

Use the frozen OpenSTEP EB-CC JETTO profiles already archived in OPENSTEP-002. Keep these distinct from the Fiesta equilibrium and the DIII-D benchmark. Calculate D-T thermal fusion from actual D/T densities and temperatures using Bosch-Hale, without fitting fusion power to the source result. Check source power closure and compare predicted alpha power with the published deposited alpha power (10% comparison screen, not an assertion of equivalence).

For a declared zero-dimensional energy model, scale all temperatures by x and hold density/profile shapes fixed. W=x W0; alpha power follows the reactivity integral; radiation is P_rad0*x^a, a=[0,0.5,1]; transport is x W0/(f*tau0), tau0=W0/P_transport0, f=[0.7,1,1.3,1.6]. Aux fractions [0,0.5,1] and alpha deposition fractions [0.8,1] form 72 cases. Find all sign-changing energy-balance roots in x=[0.5,2.5] on a fixed 401-point grid, classify derivative signs, and integrate +/-5% perturbations for the central f=1, aux=1, a=0.5, deposition=1 case. Model boundaries terminate integration. Report calibration of tau0 and radiation explicitly; this does not independently validate confinement or impurity radiation.

Extend the OPENSTEP-005 four fine-grid sharp-wall peak loads with a convective slab requirement sweep: k=[80,120,180] W/m/K, thickness=[0.002,0.005,0.010] m, h=[10000,50000,100000] W/m2/K, coolant=450 K; surface screen 1800 K (assumed, not a material qualification). Report conduction and coolant temperature jumps. Radiation needed to reach a 10 MW/m2 heat screen is a requirement derived from the 50%-radiated source scenario, not demonstrated detachment.

Use the source fusion/neutron power for transparent plant balance. Sweep thermal conversion efficiency [0.3,0.4,0.5], auxiliary wall-plug efficiency [0.3,0.5,0.7], recoverable fusion heat fraction [0.8,1], fixed electric loads [50,150,300] MW, availability [0.3,0.6,0.9]. Include deposited auxiliary and ohmic heat once; charge their electrical supply once, with assumed ohmic supply efficiency 0.9. No blanket multiplication. Report instantaneous and annual-average net power, with fixed loads also during downtime and auxiliary heating only during operation. Negative cases remain in output.

Fuel requirements: convert D-T-equivalent source fusion power to tritium burn at 17.6 MeV/reaction and 3.016049 u/triton. Calculate burn per full-power day/year and circulate at burn fractions [0.01,0.03,0.1]. Inventory lower bounds equal throughput times processing delays [1,4,24] hours. Sweep TBR=[0.9,1,1.05,1.1,1.2], breeding recovery=[0.9,0.95,0.99], exhaust loss per pass=[0,0.0001,0.001], burn fraction as above. Check net production sign using explicit mass balance. No neutron transport, breeding prediction, retention or start-up inventory certification.

## Evidence rules

Archive inputs, hashes, code, full numerical output, failures and commands. Use PASS/FAIL for specified numerical tests; use CONDITIONAL for sensitivity outcomes; use UNRESOLVED for absent STEP conductor/circuit/MHD/transport/material/neutronics inputs. Do not combine hypothetical favorable settings into a proven reactor. Any necessary protocol change receives a dated amendment before its dependent run.
