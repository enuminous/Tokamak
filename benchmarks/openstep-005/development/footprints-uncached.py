"""Flux-map heat maxima, one-sided polygon limits and assumed circular fillets."""
import argparse
import json
import time
import numpy as np
from scipy.optimize import brentq, minimize_scalar
from common import ROOT, OUT, FrozenField, Wall, inventory, stamp, save, csvsave, check, heat
from contour import trace, assess, compare, assess_difference

WINDOW = (.00025, .02)
RADII = (0., .001, .005, .01)


def offset_at(field, point):
    rsep = field.d['midplane_radii_m'][1]
    level = float(field.sp.ev(*point))
    def residual(x):
        return float(field.sp.ev(rsep+x, 0.)-level)
    for x in WINDOW:
        if abs(residual(x)) < 1e-11:
            return x
    return float(brentq(residual, *WINDOW, xtol=2e-14))


def intervals(field, wall):
    """Bounded search on the two observed lower target faces and their fillet.

    All branch identifications are checked by full first-hit traces below;
    the map alone cannot establish magnetic connectivity.
    """
    rsep = field.d['midplane_radii_m'][1]
    levels = [float(field.sp.ev(rsep+x, 0.)) for x in WINDOW]
    result = []
    for primitive in wall.primitives:
        if primitive['component'] != 0 or primitive['segment'] not in ['12', '13', 'arc-13']:
            continue
        tgrid = np.linspace(0, 1, 257)
        points = wall.point(primitive, tgrid)
        flux = field.sp.ev(points[:, 0], points[:, 1])
        # Each selected target has a monotone flux map in the tested fields.
        # Refuse ambiguous maps rather than silently selecting an arbitrary root.
        if not (np.all(np.diff(flux) < 0) or np.all(np.diff(flux) > 0)):
            raise ValueError('Nonmonotone target map requires a new explicit branch split')
        cuts = [0., 1.]
        for level in levels:
            if (flux[0]-level)*(flux[-1]-level) < 0:
                cuts.append(float(brentq(lambda t: float(field.sp.ev(*wall.point(primitive, t))-level), 0, 1, xtol=2e-14)))
        cuts.sort()
        for lo, hi in zip(cuts[:-1], cuts[1:]):
            level = float(field.sp.ev(*wall.point(primitive, (lo+hi)/2)))
            if min(levels) <= level <= max(levels):
                result.append((primitive, lo, hi))
    return result


def evaluate(field, wall, primitive, t):
    xy = wall.point(primitive, t)
    offset = offset_at(field, xy)
    return dict(tag=field.arm, shift_m=field.shift, radius_m=wall.radius,
                segment=primitive['segment'], t=float(t), offset_m=offset,
                R_target_m=float(xy[0]), Z_target_m=float(xy[1]),
                **heat(field, offset, xy, wall.normal(primitive, t)))


def geometry_checks():
    checks, arcs = [], []
    original = Wall()
    for radius in RADII[1:]:
        wall = Wall(radius=radius)
        for a in wall.fillets:
            label = f'{radius}:{a["segment"]}'
            for t, tangent in [(0., a['d0']), (1., a['d1'])]:
                xy, normal = wall.point(a, t), wall.normal(a, t)
                check(checks, label+f':radius:{t}', abs(np.linalg.norm(xy-a['center'])-radius) < 1e-12)
                check(checks, label+f':tangent:{t}', abs(normal@tangent) < 1e-11)
                check(checks, label+f':boundary:{t}', abs(wall.signed_distance(xy)) < 1e-11)
            curve = wall.point(a, np.linspace(0, 1, 65))
            check(checks, label+':cuts_inside_original', min(original.signed_distance(x) for x in curve) >= -1e-12)
            arcs.append({k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in a.items()})
        lower = wall.point(wall.fillets[0], np.linspace(0, 1, 65))
        upper = wall.point(wall.fillets[1], np.linspace(1, 0, 65))*[1, -1]
        check(checks, str(radius)+':mirror', float(np.max(abs(lower-upper))) < 1e-12)
        # A midpoint of the removed corner must be outside the rounded chamber.
        a = wall.fillets[0]
        vertex = wall.shapes[0][13]
        cut_point = .5*(vertex+wall.point(a, .5))
        check(checks, str(radius)+':cut_region_excluded', wall.signed_distance(cut_point) < 0)
        check(checks, str(radius)+':unmodified_midplane', wall.signed_distance(np.array([4.,0.])) > 0)
    save('geometry-controls.json', dict(**stamp('geometry_controls'), checks=checks, arcs=arcs))
    return checks


def main():
    result = stamp('footprint_corner_and_rounding')
    checks, rows, summaries, branch_rows, search_rows = geometry_checks(), [], [], [], []
    for path, _ in inventory():
        if len(np.load(path)['r']) != 257:
            continue
        field = FrozenField(path)
        for radius in RADII:
            wall = Wall(radius=radius)
            branches = intervals(field, wall)
            print('Starting footprint', field.arm, radius, 'branches', len(branches), flush=True)
            maxima = {65: [], 129: [], 257: []}
            optimized = []
            coverage = []
            for primitive, lo, hi in branches:
                label = f'{field.arm}:{radius}:{primitive["segment"]}'
                e0, e1 = evaluate(field, wall, primitive, lo), evaluate(field, wall, primitive, hi)
                coverage.append(sorted([e0['offset_m'], e1['offset_m']]))
                dense = []
                for i, t in enumerate(np.linspace(lo, hi, 257)):
                    row = evaluate(field, wall, primitive, t)
                    row.update(in_65=(i%4==0), in_129=(i%2==0), endpoint=(i in [0,256]))
                    rows.append(row)
                    dense.append(row)
                for n, stride in [(65, 4), (129, 2), (257, 1)]:
                    maxima[n].append(max(dense[::stride], key=lambda r:r['representative_heat_MW_m2']))
                candidates = [dense[0], dense[-1]]
                values = np.array([x['representative_heat_MW_m2'] for x in dense])
                local = np.flatnonzero((values[1:-1] >= values[:-2]) & (values[1:-1] >= values[2:]))+1
                # Also test the complete interval; all sampled local peaks get
                # their own small bracket so unimodality is not presumed globally.
                bounds = [(lo, hi)] + [(dense[i-1]['t'], dense[i+1]['t']) for i in local]
                for a, b in bounds:
                    opt = minimize_scalar(lambda t: -evaluate(field, wall, primitive, t)['representative_heat_MW_m2'],
                                          bounds=(a,b), method='bounded', options={'xatol':1e-12})
                    check(checks, label+':optimizer', bool(opt.success))
                    row = evaluate(field, wall, primitive, opt.x)
                    candidates.append(row)
                    search_rows.append(dict(tag=field.arm, radius_m=radius, segment=primitive['segment'],
                                            lo=a, hi=b, success=bool(opt.success), iterations=int(opt.nfev),
                                            optimum_t=float(opt.x), heat_MW_m2=row['representative_heat_MW_m2']))
                optimized.append(max(candidates, key=lambda r:r['representative_heat_MW_m2']))
                # First-hit connectivity is checked independently of the wall map.
                for fraction in [.05, .5, .95]:
                    t = lo+(hi-lo)*fraction
                    mapped = evaluate(field, wall, primitive, t)
                    traced, _ = trace(field, wall, mapped['offset_m'], tight=False)
                    branch_rows.append(traced)
                    assess(checks, label+f':branch:{fraction}', traced)
                    position = float(np.hypot(traced['R_target_m']-mapped['R_target_m'], traced['Z_target_m']-mapped['Z_target_m']))
                    check(checks, label+f':first_hit_segment:{fraction}', traced['component']==0 and traced['segment']==primitive['segment'])
                    check(checks, label+f':first_hit_position:{fraction}', position <= 1e-5, position, 1e-5)
                    relative = abs(traced['representative_heat_MW_m2']/mapped['representative_heat_MW_m2']-1) if traced['hit'] else None
                    check(checks, label+f':first_hit_heat:{fraction}', relative is not None and relative <= .001, relative, .001)
            coverage.sort()
            check(checks, f'{field.arm}:{radius}:window_start', abs(coverage[0][0]-WINDOW[0]) < 1e-10)
            check(checks, f'{field.arm}:{radius}:window_end', abs(coverage[-1][1]-WINDOW[1]) < 1e-10)
            gaps = [abs(a[1]-b[0]) for a,b in zip(coverage[:-1],coverage[1:])]
            check(checks, f'{field.arm}:{radius}:window_contiguous', not gaps or max(gaps) < 1e-10, max(gaps, default=0), 1e-10)
            best = {n:max(candidates, key=lambda r:r['representative_heat_MW_m2']) for n,candidates in maxima.items()}
            optbest = max(optimized, key=lambda r:r['representative_heat_MW_m2'])
            for a,b in [(65,129),(129,257)]:
                delta = abs(best[b]['representative_heat_MW_m2']/best[a]['representative_heat_MW_m2']-1)
                check(checks, f'{field.arm}:{radius}:peak_{a}_{b}', delta < .01, delta, .01)
            delta = abs(optbest['representative_heat_MW_m2']/best[257]['representative_heat_MW_m2']-1)
            check(checks, f'{field.arm}:{radius}:peak_257_optimized', delta < .01, delta, .01)
            # Full contour refinement at the maximum (nudged into its face when
            # the mathematical maximum is a one-sided corner limit).
            p, lo, hi = next((p,lo,hi) for p,lo,hi in branches if p['segment']==optbest['segment'])
            t = float(np.clip(optbest['t'], lo+1e-5*(hi-lo), hi-1e-5*(hi-lo)))
            near_peak = evaluate(field, wall, p, t)
            pair = [trace(field, wall, near_peak['offset_m'], tight=tight)[0] for tight in [False,True]]
            for traced in pair:
                branch_rows.append(traced)
                assess(checks, f'{field.arm}:{radius}:near_peak:{traced["tight"]}', traced)
            assess_difference(checks, f'{field.arm}:{radius}:near_peak_refinement', compare(*pair))
            distance = float(np.hypot(pair[1]['R_target_m']-near_peak['R_target_m'],pair[1]['Z_target_m']-near_peak['Z_target_m']))
            check(checks, f'{field.arm}:{radius}:peak_branch', pair[1]['segment']==optbest['segment'] and distance <= 1e-5, distance, 1e-5)
            summaries.append(dict(tag=field.arm, shift_m=field.shift, radius_m=radius,
                                  branches=[dict(segment=p['segment'],t_min=lo,t_max=hi) for p,lo,hi in branches],
                                  sampled_maxima={str(n):b['representative_heat_MW_m2'] for n,b in best.items()},
                                  optimized_maximum=optbest, window_m=list(WINDOW),
                                  near_peak_offset_m=near_peak['offset_m']))
            save('footprints.json', dict(**result, completed=False, checks=checks, summaries=summaries))
            print('Finished footprint', field.arm, radius, 'peak', optbest['representative_heat_MW_m2'],
                  'failures', sum(c['status']=='FAIL' for c in checks), flush=True)
    save('footprints.json', dict(**result, completed=True, checks=checks, summaries=summaries))
    csvsave('footprints.csv', rows)
    csvsave('first-hit-checks.csv', branch_rows)
    csvsave('peak-searches.csv', search_rows)
    print(json.dumps({s:sum(c['status']==s for c in checks) for s in ['PASS','FAIL']}), flush=True)


if __name__ == '__main__':
    main()
