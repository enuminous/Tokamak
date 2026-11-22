# Development record

- The first analytic-control invocation stopped at a Python syntax error before
  executing any calculation. A missing closing parenthesis was corrected. The
  subsequent 49 analytic-control assertions passed. No physical result or
  acceptance criterion was used to tune that correction.
- Frozen-field loading reuses the hash-verified accepted equilibrium report and
  flux array. This avoids repeating a critical-point/current-source solve in
  every trace. OPENSTEP-004 already contains uncached equilibrium replays; this
  package tests tracing and the imposed heat model on those same fields.
- The upstream pinned source tree and wall-creation notebook were inspected.
  They provide a first-wall outline and fixed active-coil geometry, not the
  missing calibrated conductor/circuit/controller package. The bounded source
  evidence is in `source-inspection.json`; inputs may exist outside that source.
- Synthetic wall/feedback constants are implementation fixtures, selected to
  exercise known no-wall, ideal-wall, resistive-wall, feedback-sign and saturation
  behavior. They are not estimates of tokamak conductor properties or gains.
- Stage records hash all Python files present at stage start. Additional drivers
  were developed while independent stages ran; each recorded file must still
  match its hash. The final manifest covers the complete package.
- Profiling a fine-grid trace found 5.2 of 6.8 seconds inside repeated FITPACK
  derivative evaluation. The initial rounding sweep was interrupted after five
  complete scenarios (all assertions passing); its checkpoint, source and log
  are retained in `development/`. `CachedField` constructs the two derivative
  splines once, without changing the flux spline, tolerances or geometry.
  `derivative_cache.py` checks every original grid node plus 4096 seeded points
  per field and reruns all eight tight 1 mm contours against uncached results.
  The rounding sweep is then restarted from the beginning with that validated
  evaluation cache. The main 88-trace stage retains the original uncached route.
