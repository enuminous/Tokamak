# TriSphere prototype 02: simulation contract

Matthew Chenoweth Wright / Monolithic LLC, implementing an exploratory model of A. Beth Jones's framework. November 20, 2026. Model version **2.0.0**.

This is a runnable, falsifiable comparison of **specified toy-model closures**. It is not a derivation or experimental confirmation of LCL, consciousness, gravity, or the thirteen-layer architecture. The original [source snapshot](TRISPHERE-SOURCE-2026-11-20.md) is preserved, including its unresolved and conflicting statements. [Provenance](trisphere-source.json) records the supplied document URL, modification time, base repository commit, and SHA-256 of the snapshot. Corrections below describe implementation decisions; they do not silently rewrite Beth's source.

## Run and replay

Open [the new simulator](trisphere-prototype.html) in a modern browser, including directly from an extracted repository ZIP. It needs no network, dependencies, installation, server, or build. `trisphere-core.js` supplies both the browser and Node.js results.

```sh
node verify.js
node verify-trisphere.js
node run-trisphere.js
```

The last command writes `results/trisphere-v2/`. Use `node run-trisphere.js --full` to additionally write the complete, unsampled default run JSON locally. Browser **Export run JSON** also contains every integration sample. The published CSV is sampled every 0.1 radial time unit; transport samples retain the full 0.25-unit tick grid. The code is deterministic; no random generator or seed is used. Initial conditions and all parameters are exported. Node.js 18 or later is sufficient; the evidence records the actual tested runtime.

## Two comparisons with different meanings

1. **Observer projection:** an existing atlas state can be displayed in five groups. This is a readout, with no independent dynamics or physical-equivalence claim. Standing and the avatar's 3/5/7-node polygon are view controls only. They cannot alter an energy ledger.
2. **Candidate dynamics:** independently integrate a radial probe with different shelf locations, and separately run an inventory circuit with pooled shelf-release rates. Differences are measured, not removed by construction. The inventory reduction retains route identities and original transit delays. It is therefore a five-position aggregation **with hidden route memory**, not an exact five-state Markov reduction.

The radial probe and transport circuit are separate systems. They share user parameters, but are **not coupled**. In particular, material routing uses a prescribed clock even when the radial probe settles. Each energy ledger has its own unit normalization and its own unit initial mass or inertia; their energies must not be added. A coupled field/material model remains future work.

## Coordinates and the discrete map

The radial coordinate is normalized as `x = rho/L`, with `L=12` for thirteen and `L=4` for five. All derivatives and energies are computed in `x` with unit effective inertia. Thus the corresponding rho equation is `rho'' = L*(-U'(rho/L) - gamma*rho'/L + D(t))`; this avoids accidentally treating the two rho scales as identical dimensional distances. This is a chosen nondimensional comparison, not a physical reduction map.

The inventory and view map is separate from the radial coordinate normalization:

| Thirteen-layer positions | Five-position group | Role |
|---|---:|---|
| 0 | 0 | CRP |
| 1–4 | 1 | Lower membrane / Time |
| 5–7 | 2 | Middle membrane / Space / Filter |
| 8–11 | 3 | Upper membrane / Phase |
| 12 | 4 | Shell |

This map obeys `g(12-n)=4-g(n)` and preserves the separate endpoints and the Filter. Layer 5's icosahedron and Layer 7's dodecahedron can be described as a dual pair in the blueprint; no simulated force follows from that labeling. The schematic uses rings and an avatar polygon, not an accurate Platonic-solid or field solution. Layer assignments under revision are not resolved by the simulation.

## Radial equation and explicit potential

The radial probe solves

`x'' = -U'(x) - gamma*x' + k*A*sin(2*pi*t/P)`, with `0 <= x <= 1`.

Defaults: `gamma=0.3`, `k=0.7`, `A=1.2`, `P=8`, `x(0)=0.15`, `x'(0)=0`, duration `96`, timestep `0.01`. All numbers are dimensionless and chosen. The external actuator can supply or recover work; its **signed** work is integrated.

Three flat bands represent radial shelves. Their centers are `(4/12, 8/12, 11.5/12)` in thirteen, and `(1/4, 1/2, 3/4)` in five. Each half-width is `w=0.035`. Define `S(z)=0` for `z<=0`, `S(z)=3z^2-2z^3` for `0<z<1`, and `S(z)=1` for `z>=1`. For shelf centers `s1,s2,s3`, the three rising intervals are

`(a1,b1)=(0,s1-w)`, `(a2,b2)=(s1+w,s2-w)`, `(a3,b3)=(s2+w,s3-w)`.

Then `U(x)=H*sum_j q_j*S((x-a_j)/(b_j-a_j))`, with `H=0.16` and `q=(0.4,0.35,0.25)`. The analytic derivative is used in the solver. The potential is monotone, has zero slope on the shelf bands, and stays flat beyond the third ramp. Flat bands need not trap a moving particle. Their dwell times are reported as radial residence times, separately from material shelf occupancy. This potential has not been derived from seams, gravity, or a liquid-crystal constitutive law.

### Contacts and energy

This implementation makes `v=0` at a contacted boundary literal through **perfectly inelastic contact**: the radial velocity becomes zero and the lost kinetic energy is recorded. An inward force can release the contact. In containment mode all impact energy remains as internal heat. In exhaust mode, the chosen energy-export fraction of an **outer-shell impact** is exported; the rest remains as heat. Center contacts retain all their dissipated energy as heat. This contact law is an implementation choice, not the source's unmodeled elastic seam law. It is not an elastic reflection and does not itself sustain circulation.

RK4 integrates position, velocity, external work, and damping heat. Boundary-crossing time is isolated by 34 bisection iterations before the velocity reset. The implementation enforces unilateral contact when the external force points out of the domain.

With `E=0.5*v^2+U(x)`, `W'=D*v`, and `H_damping'=gamma*v^2`, the reported residual is

`E(t) + H_damping(t) + H_contact(t) + E_export(t) - E(0) - W(t)`.

It is computed independently from the numerical trajectory and quadratures, not forced to zero. Internal heat has no return path to mechanical energy in this version. A containing shell can therefore accumulate heat while useful mechanical energy decays.

## Inventory circuit

Each circuit starts with material `N=1` and mobile energy `E=1` at the CRP. Transit advances one original layer per `0.25` time unit. Both configurations retain this route clock; compressing labels does not silently speed transit up. The last complete tick is reported if a custom duration is not a multiple of `0.25`.

At the Filter after six ticks:

- `sigma(t)=clip(sigma0 + m*sin(2*pi*t/P),0,1)` routes the Product fraction to Layer 7.
- The remainder goes to Layers 8–11 in proportion to four nonnegative weights `c_i/sum(c)`. All-zero weights are rejected.
- Each route deposits at its outbound shelf, releases toward the shell, passes through the boundary rule, deposits at its mirror shelf `12-n`, then releases toward the CRP.
- A complete circuit therefore retains 24 transit ticks plus two shelf dwell periods. The five-position model keeps these path delays and tags; its shelf inventories are pooled for readout and its release rates are pooled for dynamics.

For a primary shelf at `n`, the release rate is `lambda_n = r*f*(0.6+0.08*n)`, with `r=0.6` by default and `f=1.5,1,0.5` for repair, maintain, and decay respectively. The ten shelf positions are `1,2,3,4,5,7,8,9,10,11`. The compressed rate is the arithmetic mean of primary rates in the same five-position group. The released fraction per tick is `1-exp(-lambda*0.25)`. These rates and mode labels are prescribed controls, not physical evidence for recognition or repair.

At every tick, **all mobile energy**, including shelf energy, loses the fraction `1-exp(-gamma*0.25)` into retained heat. This removes a loophole in which a resting shelf would escape the stated damping. Particle inventory does not decay with that energy. There is no modeled mass-to-energy conversion.

At the shell, containment exports nothing; exhaust removes independently chosen particle and mobile-energy fractions (defaults `0.25` and `0.6`). Stored internal heat is not exported by this simplified boundary rule. At each CRP return the powered pump supplies work `k*pump*returned_material` with `pump=0.15`. This event-timed actuator is external. It is not energy created by the geometric loop or by intent.

Two invariants are checked on every tick:

`N_mobile + N_shelves + N_export = 1`

`E_mobile + E_shelves + H_internal + E_export = 1 + W_supplied`.

The implementation preserves nonnegative inventories and merges only cohorts with identical future route state. First-return material and energy are tracked separately from repeated cumulative returns. Cumulative throughput can exceed the initial inventory. Mean first-return time is conditional on the portion that returned within the finite run; it is not the lifetime mean when some material remains or is exported.

## Findings and declared thresholds

These are **exploratory engineering tolerances**, selected during development, not an independently preregistered scientific standard. They are exported with each run. A status refers only to its named test.

| Finding | PASS | FAIL | UNRESOLVED / NOT_APPLICABLE |
|---|---|---|---|
| Numerical accounting | Max absolute material and transport-energy residuals below `1e-10`; both radial residuals below `1e-3` | Any stated numerical bound exceeded | Nonfinite state or integration failure aborts; no successful finding |
| Candidate agreement | Numerical PASS; at least four forcing periods; both have observed first material return; full-run radial RMSE <= `0.05`, final mapped shelf L1 difference <= `0.10`, first-return fraction difference <= `0.05` | Prerequisites met but any comparison bound missed | UNRESOLVED when duration/return coverage or numerical prerequisites fail |
| Observer projection | Not an independent physical test | Not an independent physical test | NOT_APPLICABLE for dynamical equivalence; mirror-map arithmetic is tested separately |
| Physical validation | Requires a separately specified physical experiment and criterion | Requires such an experiment | UNRESOLVED throughout this prototype |

Initial radial potential energies differ because the potentials differ at the same normalized starting position. Both runs use the same `x0,v0`, each with its actual initial energy in its own ledger. The comparison does not claim identical initial mechanical energies.

The finite-window response classifier uses the last two drive periods. A peak-to-peak amplitude below `0.01` with RMS speed below `0.01` is called **settled**. Otherwise an amplitude >= `0.02` with RMS phase-space difference between the last period and the previous period below `0.01` is a **periodic candidate**. Runs shorter than four periods are unresolved. Other outcomes are labeled transient or other. These categories neither prove a limit cycle nor locate a bifurcation.

The parameter scan uses `k=(0,.25,.5,.75,1)` and `gamma=(0,.15,.3,.6,1)`. Each cell also runs a second initial position `min(1,x0+.02)` at unchanged velocity. A final-period phase-space distance below `0.01`, together with periodic recurrence, is an **attraction candidate**. This is one perturbation direction in one finite window; it does not establish an entire basin or robust stability. The exported cell retains numerical failures even if its response looks repetitive. Exhaust partition changes the radial energy ledger but not the contact motion; only the inventory circuit's losses and future pump work depend on its retained material.

## Source ambiguities resolved for implementation

| Source statement | Decision in this prototype |
|---|---|
| Five is both a compression and an avatar journey | Keep projection and independently simulated candidate dynamics conceptually separate |
| Standing is inside `D(rho,k,s,t)` but also rendering-only | Remove standing from the dynamics; it changes the schematic only |
| Five positions are both derived and chosen | Treat both five and thirteen counts as chosen inputs; no derivation from digit or solid counts |
| Damping breaks time-translation symmetry | Autonomous damped equations can remain time-translation invariant; damping transfers subsystem mechanical energy. The explicitly timed drive is a separate dependence |
| A constant autonomous drive cannot sustain the breath | A single-valued position-only force on an out-and-back interval does zero closed-cycle work. This does not exclude velocity-dependent active drives or systems with additional states |
| Shell containment implies recirculation | Specify contact, retained heat, external work, and independent inventory return paths. Containment alone supplies no work |
| Recognition adds or subtracts nodes | Only user-selected view polygons are implemented; no inferred physical node-growth law |
| Elastic seams create shelves | The potential and release rates are chosen closures, not seam-derived quantities |

## Remaining work

An actual reduction needs a stated state map, induced equations, conserved quantities, and error bounds. A coupled simulation needs a transport law driven by the computed field or flow rather than the present separate clock. Material interpretation needs measurable constitutive parameters, units, and empirical predictions. A credible next numerical step is to vary contact/release closures and equalize initial energies to see which discrepancies survive; current agreement or disagreement cannot settle the blueprint as a physical theory.

### Mathematical and physical context

- [MIT, Classical Mechanics II, Lecture 13: Damped Oscillations](https://ocw.mit.edu/courses/8-223-classical-mechanics-ii-january-iap-2017/7f2c28942dfa4293280c8a68ef9c9d22_MIT8_223IAP17_Lec13.pdf): dissipation and subsystem energy loss. The energy identity above is also obtained directly by multiplying the implemented equation by velocity.
- [Max Planck Institute for Plasma Physics: Plasma boundary](https://www.ipp.mpg.de/14917/plasmabegrenzung): actual divertor transport, wall energy deposition, and pumping require physics beyond these separate inventory fractions.
- [A. Beth Jones's blueprint](https://tri-sphere-text.abethjones.workers.dev/) and the [provided specification snapshot](TRISPHERE-SOURCE-2026-11-20.md) supply the interpretive architecture. The preserved snapshot, rather than a changing live page, defines this version's input.
