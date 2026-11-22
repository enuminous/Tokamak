"""Assemble only completed evidence; preserve earlier experiment verdicts."""
from collections import Counter
import csv
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import ROOT, OUT, REPO, PARENT, Wall, stamp, sha, save, check


def main():
    stages={name:json.loads((OUT/(name+'.json')).read_text()) for name in
            ['preflight','controls','contours','derivative-cache','footprints','wall-feedback']}
    assert stages['contours']['completed'] and stages['footprints']['completed']
    assert len(stages['contours']['rows'])==88
    assert len(stages['footprints']['summaries'])==16
    checks=[dict(stage=name,**c) for name,d in stages.items() for c in d['checks']]
    provenance=[]
    for name,data in stages.items():
        check(provenance,name+':protocol',data['protocol_sha256']==sha(ROOT/'PROTOCOL.md'))
        for file,digest in data['code_sha256'].items():
            check(provenance,name+':'+file,sha(ROOT/file)==digest)
    checks += [dict(stage='provenance',**c) for c in provenance]
    failures=[c for c in checks if c['status']=='FAIL']
    groups=[dict(stage=name,passed=sum(c['stage']==name and c['status']=='PASS' for c in checks),
                 failed=sum(c['stage']==name and c['status']=='FAIL' for c in checks)) for name in [*stages,'provenance']]
    rows=stages['contours']['rows']
    comparisons=stages['contours']['comparisons']
    refinement=[r for r in comparisons if r['comparison']=='contour_refinement']
    dop=[r for r in comparisons if r['comparison']=='saved_third_DOP853']
    footprints=stages['footprints']['summaries']
    raw=list(csv.DictReader((OUT/'footprints.csv').open()))
    branches=list(csv.DictReader((OUT/'first-hit-checks.csv').open()))
    previous=json.loads((ROOT.parent/'openstep-004/results/summary.json').read_text())
    peaks=[]
    for row in footprints:
        best=row['optimized_maximum']
        old=next(x for x in previous['fine_grid'] if x['tag']==row['tag'])
        peaks.append(dict(tag=row['tag'],shift_m=row['shift_m'],radius_m=row['radius_m'],
                          peak_heat_MW_m2=best['representative_heat_MW_m2'],offset_m=best['offset_m'],
                          segment=best['segment'],old_37_sample_max_MW_m2=old['maximum_37_MW_m2'],
                          old_comparison_applicable=row['radius_m']==0,
                          at_window_endpoint=min(abs(best['offset_m']-.00025),abs(best['offset_m']-.02))<1e-10,
                          at_sharp_corner=row['radius_m']==0 and best['segment']=='13' and abs(best['t'])<1e-10))
    summary=dict(experiment='OPENSTEP-005',parent_commit=PARENT,completed_utc=datetime.now(timezone.utc).isoformat(),
                 execution_status='COMPLETED',numerical_status='PASS' if not failures else 'FAIL',
                 device_wall_stability='NOT RUN / UNRESOLVED',physics_validation='UNRESOLVED',
                 passed=sum(c['status']=='PASS' for c in checks),failed=len(failures),groups=groups,
                 contour_trace_records=len(rows),footprint_trace_records=len(branches),
                 direct_footprint_samples=len(raw),footprint_scenarios=len(footprints),
                 max_normalized_flux_error=max(r['normalized_flux_drift'] for r in rows),
                 max_contour_refinement_length_m=max(r['length_m'] for r in refinement),
                 max_contour_refinement_position_m=max(r['position_m'] for r in refinement),
                 max_contour_refinement_heat_relative=max(r['heat_relative'] for r in refinement),
                 max_third_DOP853_length_difference_m=max(r['length_m'] for r in dop),
                 max_third_DOP853_position_difference_m=max(r['position_m'] for r in dop),
                 heat_peaks=peaks,failures=failures,
                 inherited_004_outcomes=dict(initial_passed=previous['passed'],initial_failed=previous['failed'],
                     refinement_passed=previous['representative_refinement']['passed'],refinement_failed=previous['representative_refinement']['failed']),
                 synthetic_wall_feedback=stages['wall-feedback'])
    save('summary.json',summary)
    save('verification.json',dict(checks=checks,groups=groups,passed=summary['passed'],failed=summary['failed']))

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    colors={0.:'#303e52',.001:'#397eb1',.005:'#d98038',.01:'#5c9b60'}
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained',sharex=True)
    tags=list(dict.fromkeys(r['tag'] for r in peaks))
    for ax,tag in zip(axes.flat,tags):
        shift=next(r['shift_m'] for r in peaks if r['tag']==tag)
        for radius in colors:
            for segment in ['12','arc-13','13']:
                selected=sorted([r for r in raw if r['tag']==tag and float(r['radius_m'])==radius and r['segment']==segment],key=lambda r:float(r['offset_m']))
                if selected:
                    ax.plot([float(r['offset_m'])*1000 for r in selected],[float(r['representative_heat_MW_m2']) for r in selected],color=colors[radius],lw=1.8)
        for radius,color in colors.items():
            ax.plot([],[],color=color,label='Sharp' if radius==0 else f'{radius*1000:g} mm fillet')
        ax.axhline(10,color='#999',lw=.8,ls='--')
        ax.set_title(f'{shift*100:+g} cm coil move');ax.set_xscale('log');ax.grid(alpha=.18)
        ax.set_xlabel('Upstream offset (mm)');ax.set_ylabel('Conditional heat (MW/m²)')
    axes[0,0].legend(fontsize=8)
    fig.suptitle('OPENSTEP-005 · corner-resolved heat and assumed rounding\nFixed equilibria; 0.25–20 mm window; imposed attached heat model',fontsize=13)
    fig.savefig(OUT/'footprint-rounding.svg');fig.savefig(OUT/'footprint-rounding.png',dpi=150);plt.close(fig)

    fig,ax=plt.subplots(figsize=(7,5),layout='constrained')
    for radius,color in colors.items():
        w=Wall(radius=radius)
        for primitive in w.primitives:
            if primitive['component']==0 and primitive['segment'] in ['12','13','arc-13']:
                xy=w.point(primitive,np.linspace(0,1,100))
                ax.plot(xy[:,0],xy[:,1],color=color,lw=2)
        ax.plot([],[],color=color,label='Sharp supplied corner' if radius==0 else f'Assumed {radius*1000:g} mm radius')
    ax.set(xlim=(5.841,5.858),ylim=(-8.528,-8.509),xlabel='R (m)',ylabel='Z (m)',title='Exact circular fillets at lower wall vertex 13')
    ax.set_aspect('equal');ax.legend(fontsize=8);ax.grid(alpha=.18)
    fig.savefig(OUT/'corner-geometry.svg');fig.savefig(OUT/'corner-geometry.png',dpi=150);plt.close(fig)

    time_rows=list(csv.DictReader((OUT/'synthetic-time-traces.csv').open()))
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for case,label in [('synthetic_stable_feedback','Stabilizing feedback'),('synthetic_reversed_feedback','Reversed sign'),('synthetic_saturated','Voltage saturated')]:
        selected=[r for r in time_rows if r['case']==case]
        axes[0].plot([float(r['time_s']) for r in selected],[float(r['z_m'])*1000 for r in selected],label=label)
    axes[0].set(xlim=(0,2),xlabel='Time (s)',ylabel='Displacement (mm)',title='Synthetic stress cases');axes[0].set_yscale('symlog',linthresh=1);axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
    gains=list(csv.DictReader((OUT/'synthetic-gain-map.csv').open()))
    x=np.array([float(r['Kp_V_m']) for r in gains]);y=np.array([float(r['Kd_V_s_m']) for r in gains]);z=np.array([float(r['max_real_eigenvalue_s_inverse']) for r in gains])
    sc=axes[1].scatter(x,y,c=z,cmap='coolwarm',vmin=-.5,vmax=.5,s=20)
    axes[1].set(xlabel='Kp (V/m)',ylabel='Kd (V s/m)',title='Synthetic gain grid; blue means decay')
    fig.colorbar(sc,ax=axes[1],label='Largest eigenvalue real part (1/s)')
    fig.suptitle('Implementation controls only — no tokamak stability claim',fontsize=13)
    fig.savefig(OUT/'synthetic-feedback.svg');fig.savefig(OUT/'synthetic-feedback.png',dpi=150);plt.close(fig)

    table='\n'.join(f"| {r['stage']} | {r['passed']} | {r['failed']} |" for r in groups)
    peak_table=[]
    for tag in tags:
        rr=[r for r in peaks if r['tag']==tag]
        sharp=next(r for r in rr if r['radius_m']==0)
        values=[next(r['peak_heat_MW_m2'] for r in rr if r['radius_m']==radius) for radius in colors]
        peak_table.append(f"| {sharp['shift_m']*100:+g} cm | {sharp['old_37_sample_max_MW_m2']:.4f} | "+' | '.join(f'{v:.4f}' for v in values)+' |')
    corner_table=[]
    for tag in tags:
        rr=[r for r in raw if r['tag']==tag and float(r['radius_m'])==0 and r['endpoint']=='True']
        limits=[r for r in rr if (r['segment']=='12' and abs(float(r['t'])-1)<1e-10) or (r['segment']=='13' and abs(float(r['t']))<1e-10)]
        if len(limits)==2:
            a=next(r for r in limits if r['segment']=='12');b=next(r for r in limits if r['segment']=='13')
            shift=next(r['shift_m'] for r in peaks if r['tag']==tag)
            corner_table.append(f"| {shift*100:+g} cm | {float(a['offset_m'])*1000:.6f} | {float(a['representative_heat_MW_m2']):.4f} | {float(b['representative_heat_MW_m2']):.4f} |")
    baseline=next(r for r in peaks if r['shift_m']==0 and r['radius_m']==0)
    wall=stages['wall-feedback']
    blockers='\n'.join('- '+x for x in wall['device_readiness']['blockers'])
    text=f'''# OPENSTEP-005: contour validation, wall corners and synthetic feedback

**Execution complete. Numerical checks: {summary['passed']} PASS, {summary['failed']} FAIL.**
These are assertions, not independent experiments. Device wall stability and
physical design validation remain **UNRESOLVED**.

Parent: [`{PARENT}`](https://github.com/enuminous/Tokamak/commit/{PARENT}).
The frozen [protocol](PROTOCOL.md), [inputs](inputs.json),
[verification ledger](results/verification.json) and [development record](DEVELOPMENT.md)
separate this calculation from historical results. OPENSTEP-004's
{previous['passed']} PASS/{previous['failed']} FAIL initial assertions and
{previous['representative_refinement']['passed']} PASS/{previous['representative_refinement']['failed']} FAIL
bounded refinement remain unchanged.

## What changed

The new tracer follows the implicit contour `psi(R,Z) = psi_launch` and integrates
connection length separately. All eight accepted equilibria are reused without
retuning. The heat study resolves the sharp-wall transition and evaluates three
explicitly assumed corner radii. A separate synthetic implementation exercises
wall-current dynamics and feedback; it does not compute STEP eigenmodes.

| Stage | PASS | FAIL |
|---|---:|---:|
{table}

## Contour and length results

- {len(rows)} physical-field trace records: 40 offsets at each of two settings,
  plus eight reverse 1 mm traces. Nine analytic traces include one inconsistent
  field used as a negative control.
- Maximum normalized flux error: **{summary['max_normalized_flux_error']:.3g}**.
- Maximum 20/10 mm chart-step and 8/16-node quadrature refinement changes:
  **{summary['max_contour_refinement_position_m']:.3g} m** strike,
  **{summary['max_contour_refinement_length_m']:.3g} m** connection length,
  **{summary['max_contour_refinement_heat_relative']:.3g}** relative heat.
- Across all eight 1 mm comparisons, maximum difference from OPENSTEP-004's
  third-tolerance DOP853 route is **{summary['max_third_DOP853_length_difference_m']:.3g} m**
  in length, within the frozen 0.1 mm limit.

Both routes share the same flux arrays, bicubic interpolation and imposed
toroidal field. Their agreement verifies this numerical calculation; it is not
independent validation of the equilibrium or plasma physics. Flux error alone
is not sufficient evidence because projection enforces the flux constraint.
Analytic length controls, quadrature refinement, mirror tests and the alternate
DOP853 comparison provide the additional checks.

Raw records: [traces](results/contour-traces.csv),
[comparisons](results/contour-comparison.csv),
[paths](results/contour-paths.npz) (columns R, Z, accumulated length, in metres).

## Heat footprint and rounded-corner sensitivity

All values below are **conditional MW/m²** over the upstream offset window
**0.25–20 mm**, with the same imposed 6 mm exponential width, 50% SOL radiation
and 25% one-target power fraction. Source power comes from the separately
identified JETTO flat-top source, as in OPENSTEP-002/003/004; it is not a newly
self-consistent power/transport solution for each equilibrium.

| Coil move | Old 37-point sharp sample | Resolved sharp limit | 1 mm fillet | 5 mm fillet | 10 mm fillet |
|---|---:|---:|---:|---:|---:|
{chr(10).join(peak_table)}

The baseline sharp-wall maximum is **{baseline['peak_heat_MW_m2']:.4f} MW/m²** at
**{baseline['offset_m']*1000:.6f} mm**, a one-sided limit on face 13. At the exact
polygon vertex the normal is undefined; a single heat value there would be
misleading. The two limits are:

| Coil move | Corner launch offset (mm) | Face 12 limit (MW/m²) | Face 13 limit (MW/m²) |
|---|---:|---:|---:|
{chr(10).join(corner_table)}

The +5 cm case does not cross that sharp corner inside the selected window.
Endpoint maxima remain endpoint-limited; nothing here bounds the heat closer
to the separatrix than 0.25 mm. Nested 65/129/257-point sampling on each target
interval and bounded local searches agree at the frozen 1% criterion where
their assertions pass. This is a converged numerical search, not an interval
proof of a global maximum.

There are {len(raw)} direct flux-map samples across 16 scenarios and
{len(branches)} additional first-hit/near-peak trace records. Mapping is checked
against full contours at three interior locations per branch and near each
scenario's maximum. The search is limited to the observed lower target faces
12/13 and their fillet; it is not an exhaustive proof excluding every possible
topological branch transition. Exact circular normals avoid replacing one
sharp corner with many polygon corners.

![Heat-footprint sensitivity](results/footprint-rounding.svg)

The radii are **assumptions**, not measured CAD dimensions. The same radius is
applied at the mirrored upper corner. All equilibrium fields are held fixed;
this does not model a new free-boundary equilibrium, erosion, detachment,
cooling, material survival or manufacturing tolerances.

![Assumed local geometry](results/corner-geometry.svg)

Raw data: [footprints](results/footprints.csv),
[first-hit checks](results/first-hit-checks.csv),
[peak searches](results/peak-searches.csv), [summary](results/footprints.json).
The earlier design-selection rule remains unchanged. A new conditional heat
metric does not by itself promote a geometry or trigger the historical optional
513-grid design test.

## Wall current and feedback: implemented, synthetic only

`wall_feedback.py` implements reciprocal mechanical/inductive coupling with
resistive losses and proportional/velocity voltage feedback. Checks cover the
analytic no-wall growth rate, ideal-wall oscillation, resistive-wall cubic,
passive energy balance, time integration versus a matrix exponential, feedback
sign, voltage saturation and invalid inputs. All fixture constants are recorded
in [wall-feedback.json](results/wall-feedback.json).

The synthetic gain grid has {wall['gain_grid_cases']} cases, of which
{wall['stable_gain_cases']} have strictly decaying linear modes. This is an
implementation exercise, not a tokamak controller setting. The example omits
sensor noise, sampled control, latency, current limits, evolving equilibrium
and distributed plasma/conductor dynamics. Its displacement/current/time scales
are not predictions for STEP.

![Synthetic feedback controls](results/synthetic-feedback.svg)

The [input contract](INPUT-CONTRACT.md) and [input record](device-inputs.json) deliberately leave unavailable device
inputs empty. Its validator checks completeness and rejects malformed/missing
values; accepted metadata or hashes alone do not establish calibration. The
pinned [source inspection](source-inspection.json) finds a wall outline and
fixed active-coil geometry, without a passive-conductor/circuit/controller
package. Actual-device wall eigenmodes and feedback are **NOT RUN**.

Next required inputs are a conducting volume mesh (or shell plus thickness),
temperature-dependent resistivity, electrical connections, dynamic coil
circuits, a validated plasma response, sensor/actuator limits and controller
timing. The earlier rigid no-wall force stiffness does not supply those data.
The official [TokaMaker vertical-stability example](https://openfusiontoolkit.github.io/OpenFUSIONToolkit/docs/v26.9/doc_tMaker_DIIID_ex2.html)
documents a higher-fidelity route once an appropriate equilibrium and conductor
model are available; no such solver result is claimed here.

## Reproduce

From the repository root, in a Python environment containing the pinned dependencies:

```sh
python -m pip install -r benchmarks/openstep-005/requirements.txt
OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-005/run.py
```

The actual run used Python and package versions in `inputs.json`, with
`PYTHONPATH=/workspace/scratch/4b552039c657/equilibrium-deps`.
Individual commands were `preflight.py`, `contour.py controls`,
`contour.py physical`, `derivative_cache.py`, `footprints.py`, `wall_feedback.py`, then `report.py`.
Independent stages ran concurrently; stage logs are retained under `logs/`.
No physical equilibrium was newly solved in this package.

The [artifact manifest](artifact-manifest.json) records exact byte counts,
SHA-256 hashes and Git blob hashes, excluding itself and Python caches.
Source data remain under their original OpenSTEP CC-BY-4.0 attribution; see
[OPENSTEP-001](../openstep-001/README.md) and
[OPENSTEP-002](../openstep-002/README.md) for provenance and model limitations.
'''
    (ROOT/'README.md').write_text(text)
    files=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.name=='artifact-manifest.json':
            continue
        data=path.read_bytes()
        files.append(dict(path=str(path.relative_to(REPO)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                          git_blob_sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()))
    (ROOT/'artifact-manifest.json').write_text(json.dumps(dict(experiment='OPENSTEP-005',parent_commit=PARENT,files=files),indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['passed','failed','numerical_status','device_wall_stability']},indent=2))


if __name__=='__main__':
    main()
