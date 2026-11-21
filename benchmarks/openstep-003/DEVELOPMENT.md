# Numerical recovery record

The physical inputs, fixed p(s)/Ip targets and 1e-5 residual acceptance threshold
are unchanged from the 002 controlled experiment. Numerical choices and all
unsuccessful or interrupted attempts are retained.

## Recovered coarse baseline

- Reducing Krylov's finite-difference parameter from 1e-5 to 1e-7 initially
  reproduced the coarse plateau. That attempt then lost a critical point and
  ended with an IndexError. Its field, report and log are retained.
- Removing the line search reached the 60-iteration cap with defect about
  0.00934, above the acceptance threshold. Its field, report and log remain.
- Pressure/current continuation starts from the original accepted 129-grid
  operating point and changes both targets in ten equal stages. Stages 0–6
  converged quickly. Stage 7 spent many iterations near a plateau, then crossed
  it and converged after 46 iterations. Stages 8–10 also converged.
- The alpha = 1 endpoint satisfies the exact intended targets, with defect
  4.339039220391924e-8. `recovery_check.py` independently reproduces this residual
  using FreeGS's original uncached boundary operator and full-domain search.
  This establishes a recovered numerical solution, not uniqueness or stability.
- The recovered coarse axis radius is 4.3838208874 m; the accepted 257-grid
  baseline is 4.3896544914 m. The 5.83 mm difference enters the grid comparison.
- A reverse geometry attempt from the accepted old +10 cm control failed at
  +7.5 cm during critical-point refinement. It is retained as an unsuccessful
  numerical attempt, not interpreted as absence of an equilibrium.

## Interrupted alternatives

After the exact baseline was recovered, these redundant diagnostics were
interrupted. The execution tool reported exit code 130 and partial iteration logs are
retained; no accepted final field is claimed for them:

- `results/recovery-129-fd3.log`: larger finite-difference step at the baseline.
- `development/baseline-from-negative-interrupted.log`: baseline restart from
  the accepted -1 cm geometry. The final canonical baseline rerun instead starts
  from the accepted alpha = 1 homotopy endpoint.
- `results/alternate--025mm-257-fd3.log`: larger finite-difference step for the
  -2.5 cm fine-grid case. Its original 1e-7 trial reached the frozen cap and failed acceptance.

## Geometry continuation

Outward and inward branches start independently from accepted operating-point
controls; only accepted fields warm-start another geometry. Inward branch
records use `inward-*` names. Selection files identify the accepted records used
by the screening stage. Intermediate homotopy targets are excluded.

The -2.5 cm outward case fails acceptance on both grids: the coarse trial loses
a critical-point refinement, while the fine trial reaches its iteration cap
above tolerance. Failed fields never enter a heat or confinement comparison.
The summary and complete attempt files list the remaining outcomes.

Runtime warnings in the almost-exact baseline Krylov termination check are
preserved. Independent full-domain residuals, not the optimizer's success flag,
determine numerical acceptance.

The original combined coarse scheduler completed its outward branch and also
repeated the +1 cm inward control before it was stopped. Both accepted +1 cm
records are retained. Its duplicate +2.5 cm inward trial completed with a critical-point error.
Its subsequent duplicate +5 cm trial was interrupted
(`results/shift-+050mm-129.log`); the independently scheduled inward branch
completed to its recorded limit. This scheduling change does not select results
by heat load or alter a physical input.

The combined fine scheduler completed all outward trials. The -5 cm field did
not meet the acceptance threshold. The scheduler's duplicate +1 cm inward
trial was then interrupted (`results/shift-+010mm-257.log`, exit 130); the
separately recorded `inward-010mm-257` field was already accepted. The dedicated
inward continuation supplies the remaining +2.5 and +5 cm attempts.

## Final coverage

All fourteen planned geometry/grid cases completed a bounded solve. Eight have
accepted fields; six remain numerically unresolved. Both ±1 cm movements and
both baselines are accepted on both grids. The -5 cm case is accepted only on
the 129 grid, and +5 cm only on the 257 grid. Both ±2.5 cm cases remain
unaccepted on both grids. The selected accepted fields alone feed the physical
screens. The coarse ±1 cm representative heat reductions reverse sign on the
fine grid; no candidate qualifies for the optional 513-grid refinement.

The original 001/002 package directories remain unchanged. Root navigation now
points to this separate follow-on. Historical manifests retain their original
snapshot meaning, including root-file contents at their original commits.
