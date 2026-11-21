# Development record

The frozen protocol sets models, sweeps and the equilibrium tolerance. It does
not imply every numerical attempt converges.

- Source inspection found `summary` is a separate HDF5 file, not a group in the
  flat-top NetCDF. Downloaded it from the same pinned commit and verified its
  Git blob SHA and SHA-256. Treat IMAS fill values as missing, never as powers.
- Initial output filenames for sweep CSVs omitted grid size. Added grid sizes
  and reran the 257 core calculation so both 129 and 257 records are retained.
  This changes filenames, not the calculation or scoring.
- The 129-grid fixed-pressure/current baseline, initialized by interpolation of
  the 257-grid baseline, reached the 40-iteration cap without converging (defect
  about 0.00135). Its log, report and fields are retained in `development/`.
  A second attempt uses the already-converged 129-grid original baseline as its
  warm start. Same physical constraints and 1e-5 acceptance threshold.
- The first 513-grid runs and first 257-grid modified controlled run were
  interrupted while evaluating repeated boundary integrals. Partial logs are
  retained as `*-uncached-interrupted.log`; they have no accepted final field.
  Added a cached linear von Hagenow boundary operator. Independent comparison
  against the unmodified FreeGS operator on physical and asymmetric sources
  agrees to less than 9e-15 Wb/rad. This changes execution cost, not the boundary
  equation, quadrature, 0.01 m offset or convergence criterion. The 513 solves
  are restarted from their original warm starts. The 257 modified controlled
  retry starts from the converged 129 controlled solution (grid continuation).
- A one-off controlled q diagnostic initially reused the ordinary q CSV name.
  Added a controlled suffix and regenerated the ordinary 129 q profile; original
  magnetic summary JSON was unaffected.
- Both 129-grid baseline constrained warm starts reached 40 iterations without
  convergence; the second attempt remains in `results/` with `converged=false`.
  No failed field is used for a downstream screen. The constrained 257 modified
  solve converged from the constrained 129-grid warm start.
- Profiling a 513-grid restart identified expensive critical-point iteration
  inside resolved numerical coil filaments. Additional cached/profiled attempts
  were interrupted and their logs retained. `critical_scope.py` restricts
  iterative seeds to the expected plasma/X-point region; `critical_check.py`
  compares the complete current source against the original search on both
  earlier grids and both arms. Final 513 diagnostics and the acceptance residual
  restore the original full-domain search. The physical operator and tolerance
  are unchanged. Profiling stack dumps marked "Timeout" are timer snapshots,
  not solver failures or execution deadlines.
