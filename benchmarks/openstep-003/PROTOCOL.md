# OPENSTEP-003 — fixed-operating-point coil continuation

Recorded 21 November 2026 (America/Los_Angeles), before the new solves.
Exploratory numerical continuation; not an independently preregistered or
experimentally validated reactor design. OPENSTEP-001 and 002 remain immutable.

## Fixed physical problem

Reuse the pinned OpenSTEP inputs, FreeGS 0.8.2, fourth-order free-boundary
Grad–Shafranov operator, symmetric half-domain representation, connected cut-cell
current source, F(vacuum) = 11.52 T m and coil currents from 001/002. Hold the
entire pressure function p(s) and total plasma current at the 001 baseline
257-grid values (Ip = 22,774,410.5517846 A). Positive shift moves both p9 packs
toward the midplane. Change positions only, not currents or profile shapes.

## Numerical recovery and sweep

1. Recover the 129 × 257 baseline control. First reduce the Jacobian finite
   difference parameter from 1e-5 to 1e-7. Allow up to 60 Newton iterations.
   If needed, try the same parameter with no line search, then pressure/current
   homotopy from the original 129-grid operating point in ten equal stages.
   A final bounded alternative is reverse geometry continuation from the
   accepted +10 cm control. Retain every attempted field and residual history.
   These are solver changes; never relax the physical acceptance threshold.
2. Sweep shifts -5, -2.5, -1, 0, +1, +2.5, +5 cm at 129 × 257 and 257 × 513.
   Start at zero and continue outward separately in each direction. A failed
   candidate does not become the warm start for the next candidate. Record
   initial-condition file hashes. Restore the full-domain critical-point search
   for independent residual and final diagnostic evaluation.
3. Accept only finite fields with full-domain normalized fixed-point defect
   <= 1e-5, relative total-current and full p(s) errors <= 1e-9, positive F²,
   and up/down symmetry error <= 1e-8 Wb/rad. Failures remain failures.
4. For every accepted candidate, report axis and X-point positions, q95,
   pressure integral, required transport H under the 002 prescribed-source
   assumptions, and rigid no-wall vertical stiffness. Trace the same five
   upstream offsets (1, 2, 5, 10, 20 mm) with 10 and 5 mm integration steps.
   Sweep the same 4 widths × 3 SOL radiation fractions × 2 target-power shares
   as 002, yielding 120 heat samples per geometry. Include wall clearance.
5. Compare each candidate with its same-grid baseline. A diagnostic change is
   numerically resolved only if its absolute fine-grid effect exceeds the sum
   of candidate and baseline coarse-to-fine changes (an observed heuristic,
   not a rigorous bound). Require tracer flux drift <= 1e-5, step-halving
   strike-position difference <= 1 mm and length difference <= 1 cm.
6. A candidate is promising only if representative heat at offset 1 mm,
   lambda_q = 6 mm, SOL radiation = 50%, target share = 25% is reduced beyond
   the refinement heuristic, the maximum sampled load is reduced, and wall
   clearance and required H show no resolved deterioration. Still report the
   complete grid, including tradeoffs. Counts of heat samples are not
   probabilities. No universal q/beta stability thresholds are invented.
7. If any candidate is promising, refine the baseline and the candidate with
   the lowest fine-grid representative heat to 513 × 1025. Publish whether the
   ranking survives. If none qualifies, stop without manufacturing a winner.

## Limits and provenance

Fixed p(s) and Ip do not hold pressure integral, shape, q, or thermal-energy
mapping constant. All mapped source powers/density stay as in 002; no new
confinement or fusion-power prediction is claimed. Full MHD, conducting-wall
feedback, turbulent transport, detachment, component/neutron qualification
remain NOT RUN. Record source/code hashes, commands, logs, failures and raw
fields; publish a new 003 package and link it from the existing lab.
