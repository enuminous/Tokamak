# Numerical amendments

21 November 2026, before the added restart: the direct reduced-difference
baseline solve lost a critical point; the no-line-search attempt failed the
residual threshold; pressure/current continuation stalled near alpha = 0.7;
and the reverse path from +10 cm failed at +7.5 cm during critical-point
refinement. The independently attempted -1 cm candidate converged on the
129 grid. Add a baseline restart from that accepted -1 cm field, followed by
the frozen geometry grid. This is an additional warm-start route, not a change
in pressure/current targets, source discretization, physical equations or
acceptance limits. The original attempts remain in results/. Intermediate
homotopy states have different targets and are not design candidates.

Before two additional numerical diagnostics: the 129-grid baseline restart from
-1 cm and the 257-grid -2.5 cm continuation both descend slowly or stall. Add
one rdiff = 1e-3 trial for each, keeping the original residual acceptance and
all physical inputs fixed. This tests a larger Jacobian sampling scale across
the cut-cell source's discrete connectivity changes. It does not establish
that connectivity is the cause. Retain both the original and alternate trials;
an accepted alternate can supply a subsequent continuation seed.

The original ten-stage pressure/current continuation reached alpha = 1 with
full-domain defect 4.339039220391924e-8, recovering the exact coarse baseline.
The additional coarse baseline and large-difference diagnostic trials were
interrupted after recovery; their logs remain available. The coarse geometry
sweep is restarted from this accepted endpoint. The redundant larger-difference
-2.5 cm fine trial was also interrupted; the original fine sweep continues.
