"""Render the narrative from the actual assessed result bundle."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
def main():
    s=json.loads((OUT/'summary.json').read_text());k=json.loads((OUT/'kinetic-inputs.json').read_text());v=json.loads((OUT/'verification.json').read_text())
    base,mod=s['confinement']['central'];n=s['selected_grid'];prev=s['previous_grid']
    h=s['representative_heat_loads'];heat=lambda arm,rad:float(next(x['projected_heat_MW_m2'] for x in h if x['arm']==arm and float(x['SOL_radiation_fraction'])==rad))
    control={x['arm']:x for x in s['controlled'] if x['grid']==257}
    control_text='The fine-grid constrained comparison did not converge in both arms and remains unresolved.'
    if all(control.get(a,{}).get('converged') for a in ['baseline','p9-inward']):
        shift=100*(control['p9-inward']['metrics']['axis_R_m']-control['baseline']['metrics']['axis_R_m'])
        control_text=f'At fixed p(s) and total Ip, the 257-grid axis change is {shift:+.3f} cm. This is a separate operating constraint, not the fixed-p′ experiment. Check the medium-grid statuses below before treating it as a refinement-verified effect.'
    table='\n'.join(f"| {r['arm']} | {r['grid']} × {2*r['grid']-1} | {'CONVERGED' if r['converged'] else 'UNRESOLVED'} | {r['defect']:.3g} |" for r in s['numerical'] if r['defect'] is not None)
    ctable='\n'.join(f"| {r['arm']} | {r['grid']} × {2*r['grid']-1} | {'CONVERGED' if r['converged'] else 'UNRESOLVED'} | {r['defect']:.3g} |" for r in s['controlled'] if r['defect'] is not None)
    etable='\n'.join(f"| {name} | {r['baseline']:.7g} | {r['modified']:.7g} | {r['delta']:+.5g} | {r['observed_grid_variation']:.3g} | {'RESOLVED' if r['resolved'] else 'UNRESOLVED'} |" for name,r in s['effects'].items())
    mtable='\n'.join(f"| {r['arm']} | {r['q_min_sampled']:.4f} | {r['q95']:.4f} | {100*r['beta_toroidal']:.3f}% | {r['beta_normalized']:.4f} |" for r in s['magnetic'])
    eng=s['engineering'];largest=max(c['resultant_generalized_N'] for e in eng for c in e['coils'])/1e6
    gaps='\n'.join(f"| {r['test']} | NOT RUN / UNRESOLVED | {r['reason']} |" for r in s['not_run'])
    text=f'''# OPENSTEP-002 — extended simulation screens

20 November 2026 · Matthew Chenoweth Wright / Monolithic LLC

**The translated-coil configuration is not demonstrated to be a better tokamak
design.** The executed screens reveal destabilizing no-wall vertical response,
conditional heat-load exceedances and strong dependence on the operating
constraints. They do not establish physical feasibility. The source STEP design
is itself a published design simulation; these are not measurements or a critique
of the complete STEP engineering programme.

[Open the interactive results](https://enuminous.github.io/Tokamak/screening.html)
· [Machine-readable summary](results/summary.json)
· [Frozen protocol](PROTOCOL.md)
· [Methods](METHODS.md)
· [Development/failures](DEVELOPMENT.md)

## Results

The selected equilibrium grid is **{n} × {2*n-1}**, compared with {prev} × {2*prev-1}.
The reproduced baseline's gauge-aligned core-flux RMSE against the pinned Fiesta
reference is **{100*s['reference_baseline_core_flux_nrmse']:.4f}%** of its axis-to-boundary flux span.
The original experiment keeps the seven coil circuit currents and the derivative
profiles p′(s), FF′(s) fixed while moving both p9 packs 10 cm toward the midplane.
The controlled experiment instead fixes baseline pressure p(s) and total plasma
current. These are different physical constraints.

| Category | Executed calculation | Finding and limit |
|---|---|---|
| Numerical | Refined free-boundary equilibrium and independent residual | See per-run convergence and observed grid differences below. |
| Stability | q/beta profiles; ±1, ±5, ±10 mm rigid vertical translations | Both arms have positive dFz/dz, about {s['vertical'][0]['translations'][0]['dFz_dz_N_per_m']/1e6:.2f} MN/m. This tests a rigid fixed-current/no-wall model, not MHD eigenmodes. |
| Confinement | {s['confinement']['cases']} prescribed-source 30 s energy ODE cases | Required radiation-subtracted H changes {base['H_required_transport']:.3f} → {mod['H_required_transport']:.3f} at the mapped energy targets. H is assumed, not observed. |
| Exhaust | {s['exhaust']['trace_count']} field-line traces; {s['exhaust']['load_samples']} heat samples | {s['exhaust']['above_criterion']} chosen samples exceed the 10 MW/m² steady target criterion. No detachment or neutral recycling model. |
| Engineering | Pack geometry, external magnetic loads, required support-area sensitivity | Largest generalized load {largest:.1f} MN. Self-force, actual winding/support design and allowable stress are missing. |
| Thermal | {s['thermal']['cases']} one-dimensional diffusion cases plus refinement | Central assumed slab reaches {s['thermal']['refinement'][1]['surface_at_20s_K']:.1f} K at 20 s. This is not a material/cooling qualification. |
| Electric budget | {s['electric']['cases']} efficiency/parasitic combinations | {s['electric']['minimum_net_MW']:.1f} to {s['electric']['maximum_net_MW']:.1f} MW conditional net electricity. Fusion power is prescribed. |

Sweep counts and positive/negative counts are properties of the selected grid of
assumptions, **not probabilities** or performance forecasts.

### Equilibrium and operating-point control

| Arm | Grid | Outcome | Independent normalized defect |
|---|---|---|---|
{table}

| Quantity (SI units) | Baseline | p9 inward | Change | Sum of last grid changes | Effect screen |
|---|---|---|---|---|---|
{etable}

Observed grid variation is a heuristic numerical screen, not an error bound or
confidence interval. No Richardson order is inferred from discontinuous core
masking. Historical OPENSTEP-001 results are preserved unchanged.

{control_text}

| Fixed-p(s)/Ip arm | Grid | Outcome | Independent normalized defect |
|---|---|---|---|
{ctable}

All converged constrained runs meet the target Ip and on-axis pressure to the
recorded floating-point tolerances. A failed solve is not evidence that the
physical equilibrium cannot exist. Failed/interrupted attempts remain in
`development/`; accepted fields and final residuals are in `results/`.

### Magnetic diagnostics

| Arm | Minimum sampled q | q95 | Toroidal beta | Normalized beta |
|---|---|---|---|---|
{mtable}

The sample runs from s = 0.01 to 0.99; it is not a proof of a global q minimum.
No universal beta threshold is used to declare stability. The two vertical-force
gradients are close; a small difference must be compared with grid variation.
The change is {s['vertical_stiffness_change']['delta_N_per_m']/1e3:+.2f} kN/m,
against {s['vertical_stiffness_change']['observed_grid_variation_N_per_m']/1e3:.2f}
kN/m summed last-grid variation ({'RESOLVED' if s['vertical_stiffness_change']['resolved'] else 'UNRESOLVED'} by the stated screen).
The force calculation includes no wall eddy currents, controller or plasma
current/shape response, and supplies **no physical instability growth rate**.

![Magnetic screens](results/magnetic-screens.svg)

### Power balance and confinement conventions

The pinned JETTO source gives {k['W_thermal_J']/1e6:.3f} MJ thermal energy,
{k['line_density_m3']/1e20:.4f} × 10²⁰ m⁻³ line-average electron density,
{k['P_aux_W']/1e6:.3f} MW auxiliary, {k['P_alpha_W']/1e6:.3f} MW alpha,
{k['P_ohmic_W']/1e6:.3f} MW ohmic, and {k['P_radiation_W']/1e6:.3f} MW core
radiation. Their sum gives {k['P_transport_W']/1e6:.3f} MW transported power;
the source-power balance closes exactly at the recorded precision. Integrating
its thermal profile differs from its summary energy by
{100*k['thermal_integral_relative_difference']:.3f}%, which is retained.

The baseline uses the JETTO thermal energy as a mapped target. The modified target
scales with the equilibrium pressure integral, retaining the same thermal
fraction, density, composition and prescribed powers. This is an assumption;
kinetic transport was not recomputed in the changed geometry.

With radiation-subtracted power, required H is
{base['H_required_transport']:.3f} → {mod['H_required_transport']:.3f}.
With total heating treated as the loss power in both τ = W/P and the scaling,
the corresponding values are {base['H_required_total_loss']:.3f} →
{mod['H_required_total_loss']:.3f}. These conventions must not be mixed. The
source's stored H98 = {k['summary_H98']:.3f} uses its own summary/geometry.
The apparent higher stored energy from fixed p′ does not demonstrate better
confinement.

![Energy trajectories](results/confinement.svg)

### Exhaust and materials

For a 6 mm upstream exponential width, a 1 mm upstream offset and 25% of the
separatrix power allocated to one target, the sampled attached target flux is
{heat('baseline',0):.2f} → {heat('p9-inward',0):.2f} MW/m² without SOL radiation.
With 90% SOL radiation it is {heat('baseline',.9):.2f} →
{heat('p9-inward',.9):.2f} MW/m². These are samples, not guaranteed peaks.
The target segment and incidence angle can change under refinement; inspect
the per-grid trace CSVs. Upstream offsets can be smaller than the equilibrium
mesh spacing: interpolation is not additional physical resolution.

![Exhaust footprints](results/exhaust.svg)

The supplied wall/domes are unchanged when the coils move. Approximate
s = 0.999 surface-to-wall distances are {eng[0]['near_LCFS_to_wall_m']*100:.2f} cm
and {eng[1]['near_LCFS_to_wall_m']*100:.2f} cm. The pack-intersection check uses
rectangular filament-pack bounds and finds
{sum(len(x['coil_pack_intersections']) for x in eng)} positive-area pack overlaps;
this says nothing about absent supports, casings or access paths.

The coil force calculation excludes self-force. The radial value is integrated
outward/hoop loading around the ring, not a net Cartesian force. Dividing its
generalized resultant by 100, 300 or 600 MPa gives illustrative required areas,
not structural stresses from FEA. Likewise equivalent ampere-turn density is not
superconductor current density without winding turns and fill factor.

The slab fixes its back face at 450 K, volumetric heat capacity at 2.5 MJ/(m³ K),
and sweeps k = 80/120/180 W/(m K), L = 5/10/20 mm, q = 1/5/10/20 MW/m².
Constant-property temperatures can reach {s['thermal']['max_surface_K']:.0f} K;
such outputs flag the assumptions' limits, not a surviving component. No
melting, coolant resistance, erosion, fatigue or neutron damage is modelled.

![Engineering screens](results/engineering.svg)

## Explicitly unrun higher-fidelity tests

| Test | Status | Missing model/input |
|---|---|---|
{gaps}

TokaMaker native initialization succeeded, but **no TokaMaker eigenmode result**
is presented. A wall outline alone does not define the conducting structures.
The reported neutron wall load is a uniform geometric average only. The net
electric sweep assumes complete heat recovery and unity blanket multiplication;
neither establishes tritium self-sufficiency or a power-producing plant.

## Replay

Python 3.12.14 was used. Run from this directory after installing the pinned
requirements into your chosen virtual environment:

```bash
python -m pip install -r requirements.txt
python fetch_sources.py
python boundary_check.py
python critical_check.py
python refine.py --n 513 --shift 0
python refine.py --n 513 --shift .1
python controlled.py --n 129 --shift .1
python controlled.py --n 257 --shift 0
python controlled.py --n 257 --shift .1 --warm-grid 129 --warm-controlled
python controlled.py --n 129 --shift 0 --warm-grid 129
python screens.py --n 129 --part all
python screens.py --n 257 --part all
python screens.py --n 513 --part all
python thermal.py
python diagnostic_checks.py
python verify.py
python assess.py
python write_report.py
```

Set `OPENBLAS_NUM_THREADS=1` for the recorded thread setting. Prerequisite 001
fields are committed; see its own replay for generating them. `Field` refuses
nonconverged inputs. If a refined solve fails, do not run screens on that field;
the report falls back to the finest mutually converged screened pair.
The cached boundary operator has an independent algebraic-equivalence test
against unmodified FreeGS, and keeps the original numerical boundary convention.
Iterative critical-point searches omit coil-pack regions; the accepted final
diagnostics and residual use the original full-domain search. The restricted
search has a separate source-equivalence test on both earlier grids and arms.

Verification currently records **{v['passed']} PASS, {v['failed']} FAIL** for
implementation/conservation/numerical checks. These are separate from physical
feasibility. [Detailed checks](results/verification.json) and the artifact hash
manifest allow a reviewer to distinguish source data, computed fields, selected
assumptions and unsupported claims.

## Sources and licensing

- Brown et al., [OpenSTEP](https://github.com/ukaea/OpenSTEP/tree/6f66ae09c60b361d600b178416ef3f22b8d0aa6a), [DOI 10.14468/07jt-s540](https://doi.org/10.14468/07jt-s540), CC BY 4.0. The pin represents STEP SPP-001/CML5/SPR45, not a claim about the latest STEP design. See [source manifest](source/manifest.json), and the license/citation in `../openstep-001/source/`.
- UKAEA PROCESS, [confinement definitions and IPB98(y,2)](https://ukaea.github.io/PROCESS/physics-models/plasma_confinement/) and [IPB elongation definition](https://ukaea.github.io/PROCESS/source/reference/process/models/physics/plasma_geometry/). Our implementation evaluates the published formula; this is not a PROCESS plant-model run.
- Henderson et al., [Nuclear Fusion 65 (2025) 016033](https://doi.org/10.1088/1741-4326/ad93e7), for the 10 MW/m² steady target criterion and heat-width sensitivity range. Our geometric attached-footprint model is not their detached SOL model or its equation (22).
- Tholerus et al., [flat-top operational space](https://arxiv.org/abs/2403.09460), contextual source for the distinct integrated JETTO operating point.
- [Open FUSION Toolkit vertical-stability example](https://openfusiontoolkit.github.io/OpenFUSIONToolkit/docs/v26.9/doc_tMaker_DIIID_ex2.html), for required wall/circuit modelling; not executed as a STEP validation.
- FreeGS 0.8.2: LGPL-3.0-or-later. `cached_boundary.py` is adapted from its boundary implementation; [license](LICENSE-FreeGS.txt). Other dependencies retain their own licenses. Data-derived figures are adaptations, with no UKAEA endorsement implied.
'''
    (ROOT/'README.md').write_text(text)
if __name__=='__main__':main()
