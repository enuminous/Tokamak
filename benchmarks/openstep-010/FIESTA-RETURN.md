# Independent return format

Start with inputs/baseline.json and inputs/inward-5cm.json. Solve each equilibrium separately at 257 × 513 and 129 × 257. Include a solver revision, convergence record, pressure-versus-s samples, total current, F at the boundary, flux and current conventions, coil input comparison, boundary treatment, and an input-matching review. Keep original field files and acquisition metadata. A source baseline or a trace of the local fields cannot supply the displaced equilibrium.

Export one NumPy .npz per case and grid, using 1-D increasing arrays r and z in metres, R-major 2-D total poloidal flux psi in Wb/rad, and scalar axis_R_m, psi_axis, psi_sep from that solution. Convert signs so BR = −∂Zψ/R and BZ = ∂Rψ/R. The trace uses the solver’s separatrix flux to find its outboard intersection. A constant flux gauge cancels if applied to all three flux values.

Copy inputs/fiesta-return-template.json into a separate return directory. Replace the null entries with real run records, filenames and hashes. Set the independent review field to accepted only upon a documented successful review. Missing metadata, an unavailable refinement, or different settings keep the case unresolved. The register is human-attested; the comparison script checks file identities and mesh and traces the supplied fields. It cannot authenticate a solver or reviewer from a label.

Use a copy of the extracted bundle. Execute the following at its root:

    python benchmarks/openstep-010/compare.py --fiesta-manifest /path/to/return.json --output /path/to/comparison.json

The script writes the paired CSV at benchmarks/openstep-010/results/pair-comparison.csv and writes the JSON where specified. The spot heat comparison is enabled only for an accepted independent magnetic crossing.
