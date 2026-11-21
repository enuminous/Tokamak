# Model definitions and limits

## Equilibrium and constrained comparison

Reuse OPENSTEP-001's SI/flux convention, fourth-order free-boundary Grad–Shafranov
operator, cut-cell source and refined O/X-point roots. The symmetric solve is
restricted to up/down-even flux, so convergence alone cannot test vertical
stability. Cache only the invariant Green/quad boundary operator; its direct
equivalence check is committed.

On the 513 grid, critical-point searches also resolve the numerical coil
filaments. Iteration restricts candidate seeds to R=1.25–6.25 m, Z=±7.25 m,
enclosing the expected core and primary X-points and excluding coil packs.
The full source is still computed over the full grid. This restriction is
checked against the full-domain source on the 129 and 257 grids in both arms.
After convergence, restore the original full-domain critical search for final
diagnostics and the independently evaluated acceptance residual. Thus secondary
vacuum critical points cannot silently alter the accepted source.

Let Δψ = ψaxis − ψboundary > 0 and s = (ψaxis − ψ)/Δψ. The original source is
Jφ = mask [R p′(s) + FF′(s)/(μ0 R)]. For the constrained experiment set
p′ = p′original Δψbaseline/Δψ at each iterate. Scale FF′ by c so that the same
cut-cell integral ∑Jφ ΔRΔZ equals the 257-grid baseline Ip. This fixes the entire
p(s), with p(edge)=0, rather than just its on-axis value. Coil currents stay fixed.
This does not enforce a kinetic bootstrap/current-drive solution. Reject fields
whose independent fixed-point defect exceeds 1e-5. Check F² stays positive for
any field used for subsequent magnetic diagnostics.

## Magnetic screens

F²(s) = Fedge² + 2Δψ ∫s¹ FF′(u)du. On a closed contour,
q = (1/2π) ∮ F/[R |∇ψ|] dl. Integrate along extracted closed core contours with
subdivided midpoint quadrature; the analytic circular-flux control checks R and
2π conventions. β = 2μ0 ∫p dV/(V B0²), βN = 100 β a B0/Ip[MA], with geometric
midplane R0,a and B0=11.52/R0. These diagnostics do not determine a stability
spectrum or replace wall, ideal, resistive and kinetic MHD calculations.

For a rigid translation δ of fixed Jφ, compute
Fz(δ) = −2π∫ R Jφ(R,Z) BR,coils(R,Z+δ) dR dZ. The entire plasma is translated,
so the integrated self-force is zero; only the external coil field is included.
Compute centered stiffness [Fz(h)−Fz(−h)]/(2h). Positive stiffness is destabilizing
under this restricted perturbation. A separate analytic-coil evaluation checks
the interpolated field. No growth time is inferred: self-consistent inductive,
wall and plasma dynamics are missing.

## Confinement and energy

Use the IPB98(y,2) formula in UKAEA PROCESS:

τ98 = 0.0562 Ip[MA]^0.93 B[T]^0.15 nline[10¹⁹ m⁻³]^0.41 P[MW]^−0.69
R[m]^1.97 κIPB^0.78 (a/R)^0.58 M[amu]^0.19,
with κIPB = V/(2π²Ra²), M=2.5. A fixed D-T fuel mass is an assumption for this
scaling; the source also contains He/Xe/Ar.

Two conventions are explicitly evaluated: transport P = Pheat−Prad and total
loss P=Pheat, with the same P used in τ=W/P and the scaling. Do not compare H
numbers across these conventions without conversion. The transient model uses
the former: dW/dt = Pheat−Prad−W/(H τ98), with powers and τ98 constant within
each case. Adaptive RK integration is checked against the exact exponential.
The 30-second runs do not solve fusion feedback, density evolution, current
drive or turbulent transport. Initial thermal energy is mapped from JETTO and
scaled by the pressure integral ratio between arms.

## Field lines and heat

In poloidal arc length l, integrate dR/dl=BR/Bp, dZ/dl=BZ/Bp and
dLparallel/dl=|B|/Bp using RK4 at 10 and 5 mm steps. Here BR=−ψZ/R,
BZ=ψR/R and Bφ=11.52/R outside the core. Stop at the first segment intersection
with the pinned wall/dome outline. This is an axisymmetric magnetic connection,
not particle or neutral transport. Each interpolated field is checked for flux
conservation; comparison across equilibrium grids is separate.

For upstream radial offset x and width λ, assume one-target power fraction f and
SOL-radiated fraction frad. Conservation of power in a thin flux tube gives

qtarget(x) = f Psep (1−frad) exp(−x/λ)/(2π Rup λ) × |Bnormal,target|/Bp,up.

This includes projected incidence and axisymmetric area expansion. It excludes
cross-field spreading, detached plasma, recycling, radiation geometry and ELMs.
Only five radial offsets are sampled, so the quoted maximum is a sampled maximum.
The wall normal changes at corners; small geometric shifts can change the load.
The 10 MW/m² threshold is an external design criterion, not our model validation.

## Engineering, thermal and power accounting

At each numerical coil filament evaluate the other coils and plasma field,
excluding its entire own pack. Sum dFz=−2π R Iweight BR and generalized
dFr=2π R Iweight BZ. The latter is hoop loading, not a net Cartesian vector.
Self-force and actual support load sharing are omitted. Pack area comes from
the source filament dimensions, and current is equivalent ampere-turn current.
Forces divided by assumed stresses are required-area sensitivities only.

The thermal equation is cv ∂T/∂t = k ∂²T/∂x² on a homogeneous slab. A cell-centered
finite-volume/backward-Euler discretization applies front heat flux q and back
Dirichlet temperature 450 K. Discrete stored energy plus outgoing energy equals
injected energy. The steady analytic surface value is 450+qL/k. Temperature-
dependent properties, radiation, cooling resistance, phase changes and erosion
are absent. Values outside a real material's range remain extrapolations.

Net electric = ηthermal (Pfusion+Paux+Pohmic) − (Paux+Pohmic)/ηwallplug − Pother.
This deliberately transparent budget assumes complete thermal capture and unity
blanket energy multiplication. Fusion power is the source's prescribed neutron
plus charged-particle power, not an output of the equilibrium calculation.
No neutron spectrum/transport, damage, tritium breeding or availability is solved.
