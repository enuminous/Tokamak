# Physics and correspondence

## Poloidal cross-section

Use dimensionless coordinates x (radial offset from the magnetic axis) and z (height). Use the flux function

    ψ(x,z) = x²/2 + z²/2 + z³/3.

The in-plane field direction is proportional to (−∂ψ/∂z, ∂ψ/∂x) = (−z(1+z), x). Its dot product with ∇ψ vanishes, so the field is tangent to the plotted contours. The point (0,0) is a minimum. The point (0,−1) is a saddle because the two diagonal Hessian entries there are +1 and −1. Its flux value is 1/6. At that value the two upper branches bound the confined region and the two lower branches reach the idealized target at z = −1.55.

Revolving the closed contours around the device symmetry axis gives nested tori. The plot shows the poloidal cross-section. The tokamak also has a toroidal field component, which remains present at a poloidal X-point. Twelve interior contours are sampled for display and their spacing is arbitrary. The idealized target truncates the visible open curves. This polynomial is an illustrative flux, with no fitted device equilibrium or claim of Grad–Shafranov force balance.

## Particle inventory

For one unit initially in the core, let ℓ be the fraction leaving and r be the fraction of that outflow that returns in one step. Retained = 1−ℓ, returned = ℓr, removed = ℓ(1−r), and next inventory = 1−ℓ(1−r). These quantities are particle fractions. A real divertor can return neutral fuel that later ionizes and can also remove particles and exhaust heat. The fractions in the lab are inputs. The model omits energy accounting, flight time, sources, species changes, and transport across the separatrix.

## Layer-by-layer map

The physical correspondences apply to selected functions in the blueprint. An open entry means the tokamak model offers no specific mapping for that layer.

| Layer | Blueprint motif | Tokamak correspondence |
| --- | --- | --- |
| 0 | Central reflective point | Loose geometric reference to the magnetic axis, which forms a ring in three dimensions. |
| 1 | Duality | Open. |
| 2 | Vesica piscis | Open. |
| 3 | 3:1:3 hourglass | Visual correspondence to the saddle crossing. The ratio and double-hourglass structure are open. |
| 4 | Collapsed tetrahedron | Open. |
| 5 | Octahedron or conical diamond | Open. |
| 6 | Filter | Separatrix between closed and open flux. Cross-field transport moves particles across it. |
| 7 | Product or dodecahedral layer | Partial functional correspondence to the confined inventory. The polyhedron is open. |
| 8 | Cube | Open. |
| 9 | Merkaba | Open. |
| 10 | Through-center hourglass | Local X geometry at the edge of confinement. The tokamak X-point lies away from the magnetic axis. |
| 11 | Toroidal return | Toroidal confinement and a separate neutral recycling path at the divertor. |
| 12 | Asymptotic shell | Material vessel and divertor targets supply a physical boundary with exchange. |

The blueprint's Time, Space, and Phase tori have no assigned tokamak equivalents. The geometric comparison does not establish universal rotation or a closed cosmology.

## Sources

- [Beth’s Universal 13-Layer Tri-Sphere Blueprint](https://docs.google.com/document/d/1I5enZeXyvjFy0pVPHwT70JTCAn0XXgt0/edit)
- [ITER Technical Basis, §1.3.6, Divertor and Power Exhaust](https://www-pub.iaea.org/MTCD/Publications/PDF/ITER-EDA-DS-24.pdf)
- [Real-time feedback control of the impurity emission front in tokamak divertor plasmas, Fig. 1](https://www.nature.com/articles/s41467-021-21268-3)

## Jones's equations and the model

Source: [A. Beth Jones, The 13-Layer Tri-Sphere: Equations for a Closed Loop](https://tri-sphere-text.abethjones.workers.dev/), checked November 19, 2026 Pacific time. Jones describes TriSphere as an interpretive framework.

| Equation | Jones’s construction | Role in this lab |
| --- | --- | --- |
| 1 | Layers at ρ = 0 through 12 | Integer shell selector. The illustrative radial oscillator uses continuous normalized displacement. |
| 2 | Shells S³ in C² | Domain of the Hopf example. The zero-radius shell is a point. |
| 3 | Hopf map | Implemented in real coordinates. The image norm is ρ². For ρ > 0 the map is invariant under a common phase on both complex inputs. |
| 4 | Radial velocity zero at 12 | A source condition. The oscillator has a parameter-dependent turning point and no wall at 12. |
| 5 | Return map from shell to central reflective point | A source construction. The toy solver uses a center return event. |
| 6 | Layer reflection M(n) = 12 − n | Source symmetry, without an assigned reactor counterpart. |
| 7 | Intent filters Product and Compost | Analogue to routing only. The numerical fractions are user inputs and carry no physical intent coupling. |
| 8 | Periodic breath | Tested through a fixed point of the toy return map. Periodicity of the full framework remains open. |
| 9 | 144 = 12 × 12 | Source geometric count, without an assigned reactor counterpart. |
| 10 | Driven damped radial motion | Exact solution for a chosen harmonic potential between center kicks. |

Jones’s candidate equation is ρ″ = −V′(ρ) − γρ′ + D(ρ,k). For E = (ρ′)²/2 + V(ρ), the energy change rate is −γ(ρ′)² + ρ′D(ρ,k). A repeated nontrivial excursion with positive damping requires replenishment. For fixed k and smooth single-valued D(ρ,k), an out-and-back path has zero net drive work. Periodicity and exact turning at ρ = 12 therefore need further conditions.

The lab chooses V = ρ²/2 in normalized units and supplies an explicit event-driven alternative. For 0 < γ < 2, let ω = √(1−γ²/4), T = π/ω, and q = exp(−γT). At launch energy E, ρ(t) = √(2E) exp(−γt/2) sin(ωt)/ω for one excursion. At the center the toy reflector reverses velocity and adds work K. Then E_next = qE + K and the fixed point is K/(1−q). Zero kick gives decay. A positive kick gives a positive attracting fixed point for this chosen closure. This demonstrates a sufficient model mechanism and leaves Jones’s physical source of drive open.

## Reactor schematic boundaries

The 3D geometry shows a generic vacuum vessel, plasma surfaces, toroidal-field coils, poloidal-field coils, and divertor targets. The cutaway is a display operation. The projected wireframe uses circular profiles. The 2D analytic plot supplies the separatrix topology independently. The time axis animates points on prescribed helices, with pitch and speed selected for viewing. Neither drawing is a magnetic equilibrium or a device-specific engineering schematic. No trajectories through the exhaust, material loads, transport coefficients, power output, or operating limits are calculated.

The fuel and energy panels each use the same independent one-step balance with independently adjustable fractions. A returned fuel fraction does not imply the same returned energy fraction. The radial drive adds work supplied by an idealized external actuator. The flux model, both inventories, Hopf map, and radial oscillator are separate demonstrations.
