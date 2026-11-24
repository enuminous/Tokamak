# OPENSTEP-009 · Heat footprint to transient target temperature

Question: how does a temporary loss of heat transfer at the coolant boundary change the surface temperature for the four archived p9 geometries? A calculation on a hypothetical slab can test the interface from magnetic footprint to heat removal. Physical heat flux, coolant failure frequency and allowable temperatures require facility data.

Use all four shifts and all four corner radii in OPENSTEP-005's ordered summaries at 257 × 513. Take the optimized maximum over the declared launch window, retaining its units and geometry identity. Compare the sharp steady references with the matching OPENSTEP-006 rows. The +5 cm shift denotes the mirrored p9 pair in the historical convention. It does not denote a rigid movement of the full PF system.

Assume a homogeneous 5 mm slab, k = 120 W/(m K), volumetric heat capacity = 2.5 MJ/(m³ K), initial slab and bulk coolant = 450 K. Apply the recorded peak as a constant incident flux from t = 0 to 2 s; hold that footprint fixed. Use h = 50 kW/(m² K) for 1 s. Over the second second retain h or reduce it to 10 kW/(m² K). At t = 2 s remove the imposed heat. Restore nominal h and follow cooldown to 5 s. These are test fixtures, including the 1800 K screen carried from 006. Resolve time within each interval on a 0.01 s observation grid and record both sides of discontinuities. Report the highest sampled loaded-face temperature and the first sampled screen exceedance. No intermediate time interpolation for a crossing. No material-failure verdict follows.

Use cell-centered finite volumes and half-cell face resistances. Independently integrate the outlet flux and compare with the change in stored energy over each interval. Compare 16, 32 and 64 cells. Gates set before running this calculation:

- Require 16 unique geometry inputs, all 32 geometry/fault pairs and both sharp-wall directions. Reject duplicate/missing keys, nonfinite inputs and nonpositive material data.
- Analytic limits: zero flux stays at coolant temperature to 1e-7 K; imposed steady flux gives the linear slab solution to 1e-6 K. For each original sharp geometry steady temperature agrees with the matching 006 row within 1e-6 K.
- Relative energy discrepancy at most 1e-8 of max(1 J/m², input energy, energy removed, absolute storage change) per interval. The 32-to-64 change in maximum sampled temperature must be within 2 K for every case. The sampled peak under reduced cooling must not fall below the paired nominal peak (1e-6 K tolerance).
- Carry through failed checks. A missing or invalid field is ungraded, never zero-filled. Report every screen crossing and time, both signs of coil movement and all radii. Stop refinement on a pass at 64; on failure retain the failure and try 128 as a diagnostic only.

Exclusions include lateral conduction, pulsed ELM/disruption energy, stress, radiation transport, active feedback, material evolution, coolant boiling, CAD, and changing flux profiles. Reusing a FreeGS field or a TokaMaker trajectory provides numerical cross-checks. Physical qualification needs independent measurements and owner-defined margins.
