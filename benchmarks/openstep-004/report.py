"""Summarize completed OPENSTEP-004 jobs without changing earlier snapshots."""
from pathlib import Path
from datetime import datetime, timezone
import csv
from collections import Counter
import hashlib
import json
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
OUT = ROOT/'results'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stages = {name: json.loads((OUT/f'{name}.json').read_text())
              for name in ['preflight', 'controls', 'equilibria', 'tracing']}
    assert len(stages['equilibria']['rows']) == 8, 'Incomplete equilibrium job'
    assert stages['tracing']['trace_count'] == 88, 'Incomplete original-offset traces'
    assert len(stages['tracing']['comparisons']) == 40, 'Missing tracer comparisons'
    checks = [dict(stage=stage, **c) for stage, data in stages.items() for c in data['checks']]
    for stage, data in stages.items():
        ok = data['code_sha256'] == digest(ROOT/'validate.py') and data['protocol_sha256'] == digest(ROOT/'PROTOCOL.md')
        checks.append(dict(stage='provenance', name=stage+':unchanged_code_and_protocol',
                           status='PASS' if ok else 'FAIL', value=ok, limit=True))
    rows = stages['equilibria']['rows']
    comparisons = stages['tracing']['comparisons']
    dense = list(csv.DictReader((OUT/'dense-footprints.csv').open()))
    tags = [r['tag'] for r in rows if r['grid']==257]
    assert len(dense) == 148 and set(r['tag'] for r in dense) == set(tags), 'Incomplete dense grid'
    fine = []
    for tag in tags:
        records = [r for r in dense if r['tag']==tag]
        def maximum(flag):
            selected = [r for r in records if r[flag]=='True' and r['hit']=='True']
            return max(selected, key=lambda r: float(r['representative_heat_MW_m2']))
        a, c = maximum('in_17'), maximum('in_33')
        combined = max([r for r in records if r['hit']=='True'],
                       key=lambda r:float(r['representative_heat_MW_m2']))
        delta = abs(float(c['representative_heat_MW_m2'])/float(a['representative_heat_MW_m2'])-1)
        check = dict(stage='sampling', name=tag+':17_33_sampled_maximum',
                     status='PASS' if delta<=.01 else 'FAIL', value=delta, limit=.01)
        checks.append(check)
        shift = next(r['shift_m'] for r in rows if r['tag']==tag)
        at1 = next(r for r in comparisons if r['tag']==tag and r['offset_m']==.001)
        fine.append(dict(tag=tag, shift_m=shift,
                         heat_1mm_MW_m2=at1['adaptive_heat_MW_m2'],
                         maximum_17_MW_m2=float(a['representative_heat_MW_m2']),
                         maximum_33_MW_m2=float(c['representative_heat_MW_m2']),
                         maximum_offset_m=float(c['offset_m']),
                         maximum_at_interval_endpoint=float(c['offset_m']) in [.00025,.02],
                         maximum_37_MW_m2=float(combined['representative_heat_MW_m2']),
                         maximum_37_offset_m=float(combined['offset_m']),
                         maximum_37_at_interval_endpoint=float(combined['offset_m']) in [.00025,.02],
                         sampled_max_relative_difference=delta,
                         wall_components=sorted(set(int(r['component']) for r in records if r['component'])),
                         wall_segments=sorted(set(int(r['segment']) for r in records if r['segment'])),
                         sample_count=len(records)))
    grouped = []
    for stage in ['preflight', 'controls', 'equilibria', 'tracing', 'sampling', 'provenance']:
        part = [c for c in checks if c['stage']==stage]
        grouped.append(dict(stage=stage, passed=sum(c['status']=='PASS' for c in part),
                            failed=sum(c['status']=='FAIL' for c in part)))
    failures = [c for c in checks if c['status']=='FAIL']
    failure_families = dict(Counter(c['name'].split(':')[-1] for c in failures))
    refine = json.loads((OUT/'representative-refinement.json').read_text())
    assert len(refine['rows']) == 8, 'Incomplete bounded refinement'
    refinement_checks = list(refine['checks'])
    refined_comparison = []
    original_traces = list(csv.DictReader((OUT/'adaptive-traces.csv').open()))
    for row in refine['rows']:
        before = next(r for r in original_traces if r['tag']==row['tag'] and float(r['offset_m'])==.001 and r['tight']=='True' and r['direction']=='1')
        pos = float(np.hypot(row['R_target_m']-float(before['R_target_m']), row['Z_target_m']-float(before['Z_target_m'])))
        length = abs(row['connection_length_m']-float(before['connection_length_m']))
        heat = abs(row['representative_heat_MW_m2']/float(before['representative_heat_MW_m2'])-1)
        value = dict(position_m=pos, length_m=length, heat_relative=heat)
        refinement_checks.append(dict(name=row['tag']+':tight_third_agreement',
                                      status='PASS' if pos<=1e-5 and length<=1e-4 and heat<=.001 else 'FAIL',
                                      value=value, limit=dict(position_m=1e-5, length_m=1e-4, heat_relative=.001)))
        refined_comparison.append(dict(tag=row['tag'], **value, flux_drift=row['normalized_flux_drift']))
    ok = (refine['driver_sha256']==digest(ROOT/'refine_traces.py')
          and refine['amendment_sha256']==digest(ROOT/'AMENDMENTS.md')
          and refine['code_sha256']==digest(ROOT/'validate.py')
          and refine['protocol_sha256']==digest(ROOT/'PROTOCOL.md'))
    refinement_checks.append(dict(name='refinement:code_and_amendment_hashes', status='PASS' if ok else 'FAIL', value=ok, limit=True))
    refinement = dict(scope='Post hoc representative-point precision diagnosis; original verdict retained',
                      cases=8, passed=sum(c['status']=='PASS' for c in refinement_checks),
                      failed=sum(c['status']=='FAIL' for c in refinement_checks),
                      comparisons=refined_comparison, checks=refinement_checks)
    (OUT/'refinement-assessment.json').write_text(json.dumps(refinement, indent=2)+'\n')
    target_rows = [{k:r[k] for k in ['tag','component','segment','R_target_m','Z_target_m',
                                   'Bnormal_target_T','Bpol_upstream_T','area_expansion',
                                   'representative_heat_MW_m2']}
                   for r in refine['rows'] if r['grid']==257]
    summary = dict(experiment='OPENSTEP-004', parent_commit=stages['preflight']['parent_commit'],
                   completed_utc=datetime.now(timezone.utc).isoformat(),
                   execution_status='COMPLETED', numerical_status='PASS' if not failures else 'FAIL',
                   physics_status='UNRESOLVED', passed=sum(c['status']=='PASS' for c in checks),
                   failed=len(failures), groups=grouped, failures=failures,
                   failure_families=failure_families, representative_refinement=refinement,
                   fine_representative_targets=target_rows,
                   equilibrium_cases=8, original_offset_comparisons=40,
                   adaptive_trace_records=88, dense_sample_records=len(dense),
                   additional_dense_integrations=128,
                   max_uncached_defect=max(r['uncached_defect'] for r in rows),
                   max_direct_force_relative_difference=max(r['force_relative_difference'] for r in rows),
                   max_tracer_position_difference_m=max(r['position_m'] for r in comparisons),
                   max_tracer_length_difference_m=max(r['length_m'] for r in comparisons),
                   max_tracer_heat_relative_difference=max(r['heat_relative'] for r in comparisons),
                   fine_grid=fine, unchanged_design_decision='No validated improvement or full reactor qualification')
    (OUT/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    (OUT/'verification.json').write_text(json.dumps(dict(checks=checks, groups=grouped, passed=summary['passed'], failed=summary['failed']), indent=2)+'\n')

    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':11})
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True, layout='constrained')
    colors = ['#167d8d', '#9b5a16', '#74529a', '#c13b3b']
    for row, color in zip(sorted(fine,key=lambda r:r['shift_m']), colors):
        records = sorted([r for r in dense if r['tag']==row['tag'] and r['hit']=='True'], key=lambda r:float(r['offset_m']))
        x = np.array([float(r['offset_m']) for r in records])*1000
        label=f"{row['shift_m']*100:+g} cm coil move"
        axes[0].plot(x, [float(r['representative_heat_MW_m2']) for r in records], '.-', label=label, color=color)
        axes[1].plot(x, [float(r['connection_length_m']) for r in records], '.-', color=color)
    axes[0].axhline(10, ls='--', color='#777', lw=1, label='10 MW/m² conditional screen')
    axes[0].set_ylabel('Conditional wall heat (MW/m²)')
    axes[1].set_ylabel('Connection length (m)')
    axes[1].set_xlabel('Launch offset outside midplane separatrix (mm)')
    axes[0].legend(fontsize=9, ncol=2)
    for ax in axes:
        ax.set_xscale('log')
        ax.grid(alpha=.2)
    fig.suptitle('OPENSTEP-004 · denser tracing of the four accepted fine-grid fields\nFixed equilibrium fields; attached heat model; continuous peak unresolved', fontsize=13)
    fig.savefig(OUT/'dense-footprints.svg')
    fig.savefig(OUT/'dense-footprints.png', dpi=160)
    plt.close(fig)
    raw = np.genfromtxt(ROOT.parent/'openstep-002/source/SPR45_2D_Wall.csv', delimiter=',', skip_header=2)
    wall = raw[:,:2]
    wall = wall[np.isfinite(wall).all(axis=1)]/1000
    fig, ax = plt.subplots(figsize=(8,5), layout='constrained')
    ax.plot(wall[:,0], wall[:,1], color='#444', lw=2, label='Supplied polygonal wall')
    for row,color in zip(target_rows,['#9b5a16','#167d8d','#74529a','#c13b3b']):
        shift = next(r['shift_m'] for r in rows if r['tag']==row['tag'])*100
        ax.scatter(row['R_target_m'], row['Z_target_m'], s=70, color=color,
                   label=f"{shift:+g} cm · {row['representative_heat_MW_m2']:.2f} MW/m²", zorder=3)
    ax.set(xlim=(5.76,5.88), ylim=(-8.56,-8.47), xlabel='R (m)', ylabel='Z (m)',
           title='The +5 cm case strikes the adjacent wall segment\n1 mm launch offset, 257 × 513 equilibrium; conditional attached model')
    ax.set_aspect('equal', adjustable='box')
    ax.legend(fontsize=9, loc='upper left', bbox_to_anchor=(1.02,1))
    ax.grid(alpha=.2)
    fig.savefig(OUT/'wall-corner.svg')
    fig.savefig(OUT/'wall-corner.png', dpi=160)
    plt.close(fig)

    lines = ['# OPENSTEP-004 — the next numerical validation checks', '',
             'Matthew Chenoweth Wright / Monolithic LLC · 21 November 2026', '',
             f"**Execution: completed. Numerical assertions: {summary['passed']} PASS, {summary['failed']} FAIL. Physical qualification: UNRESOLVED.**", '',
             'These assertions include file-integrity checks and repeated per-trace acceptance conditions; they are not independent physical experiments. The substantive comparisons are eight uncached equilibrium replays, eight direct-coil force calculations and forty comparisons of the old and new tracing methods.', '',
             'The historical OPENSTEP-003 conclusion is preserved: no tested coil movement has demonstrated an improvement that survives the specified equilibrium-grid comparison. This suite does not make a new geometry winner or run full MHD.', '',
             '## Results by check family', '', '| Check family | PASS | FAIL |', '|---|---:|---:|']
    lines += [f"| {g['stage']} | {g['passed']} | {g['failed']} |" for g in grouped]
    lines += ['', '## Equilibrium and force replay', '',
              '| Grid | Move (cm) | Uncached normalized defect | Direct stiffness (MN/m) | Difference from prior force |',
              '|---|---:|---:|---:|---:|']
    lines += [f"| {r['grid']} × {2*r['grid']-1} | {r['shift_m']*100:+g} | {r['uncached_defect']:.3g} | {r['stiffness_N_per_m']/1e6:.5f} | {r['force_relative_difference']*100:.5f}% |" for r in rows]
    lines += ['', 'Positive stiffness means destabilizing in the rigid, fixed-coil, no-wall model. No conducting vessel, controller, plasma deformation or MHD eigenmode is included. The original 1e−5 residual limit was retained. The deliberately perturbed equilibrium must be rejected for its negative control to pass.', '',
              '## Different tracing route', '',
              'The new tracer uses adaptive DOP853 in toroidal angle and continuous signed-distance wall events. The previous tracer uses fixed-step RK4 in poloidal arc length and chord/wall intersections. Both share the saved equilibrium, cubic flux interpolant and wall geometry; this is implementation diversity, not an independent physics model or independent reviewer.', '',
              f"Across forty original-offset comparisons, the largest differences were **{summary['max_tracer_position_difference_m']*1e6:.3f} µm** in strike position, **{summary['max_tracer_length_difference_m']*1000:.3f} mm** in connection length and **{summary['max_tracer_heat_relative_difference']*100:.5f}%** in representative heat.", '',
              'The suite also checks tighter adaptive tolerances, reverse-direction tracing, analytic uniform-field trajectories and rejection of a deliberately inconsistent flux/field pair. Raw positions, lengths, target segments and solver evaluation counts are retained.', '',
              '### Why the +5 cm heat projection is much larger', '',
              '![Representative traces land on adjacent wall segments](results/wall-corner.png)', '',
              'The third-tolerance fine-grid replay places the baseline and both 1 cm cases on wall segment 12, while the +5 cm case hits adjacent segment 13 (zero-based indices in the supplied main-wall polygon). The different surface normal raises the normal field and reduces the flux-tube area expansion. Thus the approximately 56 MW/m² projection is reproduced by the alternative tracer; it is tied to the imposed wall geometry and heat model. This does not establish the heat on a manufactured, rounded target or a detached plasma.', '',
              '| Fine-grid field | Segment | R target (m) | Z target (m) | Normal field (T) | Area expansion |',
              '|---|---:|---:|---:|---:|---:|']
    lines += [f"| {r['tag']} | {r['segment']} | {r['R_target_m']:.6f} | {r['Z_target_m']:.6f} | {r['Bnormal_target_T']:.6f} | {r['area_expansion']:.5f} |" for r in target_rows]
    lines += ['',
              '## Denser fine-grid footprints', '',
              '![Denser footprint and connection-length samples](results/dense-footprints.png)', '',
              '| Move (cm) | Heat at 1 mm (MW/m²) | 17-point max | 33-point max | All 37 max | All 37 max offset (mm) | At interval endpoint? |',
              '|---|---:|---:|---:|---:|---:|---|']
    lines += [f"| {r['shift_m']*100:+g} | {r['heat_1mm_MW_m2']:.5f} | {r['maximum_17_MW_m2']:.5f} | {r['maximum_33_MW_m2']:.5f} | {r['maximum_37_MW_m2']:.5f} | {r['maximum_37_offset_m']*1000:.4f} | {'Yes' if r['maximum_37_at_interval_endpoint'] else 'No'} |" for r in sorted(fine,key=lambda r:r['shift_m'])]
    lines += ['', 'The nested grids cover only 0.25–20 mm. Original offsets are additionally retained. Each fine field has 37 distinct sampled offsets; 32 new integrations per field supplement the original five. An endpoint maximum or a narrow unsampled feature prevents treating the sampled maximum as the physical peak, even when 17/33 values agree. Launch offsets smaller than the equilibrium spacing do not add equilibrium resolution.', '',
              'These are the same conditional assumptions as 003: 6 mm upstream width, 50% SOL radiation, 25% one-target power, prescribed source power and attached flux-tube projection. They do not model detachment, neutrals or heat transport across flux surfaces.', '',
              'The baseline maximum on the nested geometric grids changes by 3.02% between 17 and 33 points, failing the frozen 1% sampling-consistency check. Including the original five offsets gives its largest recorded sample at 10 mm (12.3507 MW/m²). The +1 cm geometry has an additional high sample near 6.6874 mm (21.5351 MW/m²), where the wall segment changes. These dense values are diagnostics from the standard adaptive settings; their stricter flux failures remain recorded, and they are not certified continuous maxima.', '',
              '## Failed checks', '']
    if failures:
        lines += ['| Failure family | Failed assertions |', '|---|---:|']
        lines += [f'| {name} | {count} |' for name,count in sorted(failure_families.items())]
        lines += ['', 'Every individual failure and its value/limit is retained in [verification.json](results/verification.json). The original numerical suite remains FAIL; later refinement does not overwrite those results.']
    else:
        lines += ['None in the executed numerical suite.']
    lines += ['', '## Bounded third-tolerance diagnosis', '',
              f"After the first failures, all eight fields were retraced at the fixed 1 mm representative offset with rtol 1e-12 and a 0.025 rad maximum step. This separate diagnostic records **{refinement['passed']} PASS, {refinement['failed']} FAIL**. See [AMENDMENTS.md](AMENDMENTS.md) and the [full refinement assessment](results/refinement-assessment.json).", '',
              '| Field | Normalized flux drift | Tight-to-third strike change (µm) | Length change (mm) | Heat change (%) |',
              '|---|---:|---:|---:|---:|']
    lines += [f"| {r['tag']} | {r['flux_drift']:.3g} | {r['position_m']*1e6:.4f} | {r['length_m']*1000:.4f} | {r['heat_relative']*100:.6f} |" for r in refined_comparison]
    lines += ['', 'The initial checks and dense samples are retained unchanged. A successful representative-point diagnosis would not certify every dense sample, remove equilibrium-grid dependence, or establish a physical peak.']
    lines += ['', '## What is still unresolved', '',
              '- The six unaccepted grid/geometry cases from 003 remain unresolved; this suite does not solve them.',
              '- Equilibrium-grid dependence and the continuous heat-load maximum remain unresolved. The +5 cm case still lacks an accepted coarse counterpart.',
              '- Full 3-D MHD and conducting-wall/feedback stability: NOT RUN.',
              '- Predictive turbulent transport and self-consistent burn: NOT RUN.',
              '- SOL detachment and neutral recycling: NOT RUN.',
              '- Structural, superconducting, cooling and neutron qualification: NOT RUN.', '',
              '## Reproduce', '',
              'Run from the repository root with Python 3.12. The 001–003 files and their front-page inputs remain unchanged in this publication, so the 003 inventory can be checked directly. Source numerical dependencies are pinned in the inherited requirements.', '',
              '```sh', 'python -m pip install -r benchmarks/openstep-004/requirements.txt',
              'OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-004/validate.py preflight',
              'OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-004/validate.py controls',
              'OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-004/validate.py equilibria',
              'OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-004/validate.py tracing',
              'OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-004/refine_traces.py',
              'OPENBLAS_NUM_THREADS=1 python benchmarks/openstep-004/report.py', '```', '',
              'See [PROTOCOL.md](PROTOCOL.md), [summary.json](results/summary.json), [verification.json](results/verification.json) and [artifact-manifest.json](artifact-manifest.json). Each stage records the code/protocol hashes. FAIL assertions are recorded even when a calculation completes normally; inspect the numerical status rather than only the process exit code.', '',
              '## Sources and independence', '',
              '- [Historical controlled scan](../openstep-003/README.md), parent `2438abacf652478ec7865b3ce1fce5d17ad8ab1c`.',
              '- [SciPy 1.17.0 solve_ivp](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.integrate.solve_ivp.html): DOP853 and event handling.',
              '- [FreeGS 0.8.2 diagnostics](https://freegs.readthedocs.io/en/stable/diagnostics.html): toroidal-angle field-line tracing conventions.',
              '- UKAEA OpenSTEP, Brown et al., [DOI 10.14468/07jt-s540](https://doi.org/10.14468/07jt-s540), pinned source `6f66ae09c60b361d600b178416ef3f22b8d0aa6a`, CC BY 4.0. No UKAEA endorsement implied.',
              '- Original FreeGS boundary and coil routines remain shared LGPL-3.0-or-later dependencies. The profile/connectivity implementation, equilibrium and wall are shared inputs; agreement cannot establish their physical correctness.', '']
    (ROOT/'README.md').write_text('\n'.join(lines))
    files = []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.name=='artifact-manifest.json':
            continue
        data = path.read_bytes()
        files.append(dict(path=str(path.relative_to(REPO)), bytes=len(data), sha256=digest(path),
                          git_blob_sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()))
    (ROOT/'artifact-manifest.json').write_text(json.dumps(dict(experiment='OPENSTEP-004', parent_commit=summary['parent_commit'], files=files), indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__=='__main__':
    main()
