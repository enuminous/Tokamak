"""Immutable inputs and exact line/circular-fillet wall geometry."""
from pathlib import Path
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
from scipy.interpolate import RectBivariateSpline
from shapely.geometry import Point, Polygon, LineString

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
OUT = ROOT / 'results'
PARENT = '4939a9314d2db8482a4a0f7421ca4bb1d125917d'
F = 11.52
OFFSETS = [.001, .002, .005, .01, .02]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp(stage):
    return dict(stage=stage, parent_commit=PARENT,
                started_utc=datetime.now(timezone.utc).isoformat(),
                protocol_sha256=sha(ROOT / 'PROTOCOL.md'),
                code_sha256={p.name: sha(p) for p in ROOT.glob('*.py')})


def save(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def csvsave(name, rows):
    if not rows:
        return
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check(checks, name, ok, value=None, limit=None):
    checks.append(dict(name=name, status='PASS' if bool(ok) else 'FAIL',
                       value=value, limit=limit))


def inventory():
    items = []
    for n in [129, 257]:
        data = json.loads((ROOT.parent / f'openstep-003/results/screens-{n}.json').read_text())
        for row, pin in zip(data['rows'], data['input_fingerprint']['fields']):
            path = ROOT.parent / pin['path']
            assert sha(path) == pin['sha256']
            assert sha(path.with_suffix('.json')) == pin['report_sha256']
            assert path.stem == row['tag']
            items.append((path, row))
    assert len(items) == 8
    return items


class FrozenField:
    """Load previously accepted diagnostics; no repeated critical/source solve."""
    def __init__(self, path):
        data = np.load(path)
        self.r, self.z, self.psi = data['r'], data['z'], data['psi']
        self.report = json.loads(path.with_suffix('.json').read_text())
        assert self.report['converged']
        self.d = self.report['final']
        self.span = self.d['psi_axis'] - self.d['psi_boundary']
        self.arm, self.n = path.stem, len(self.r)
        self.sp = RectBivariateSpline(self.r, self.z, self.psi)
        self.shift = self.report['p9_translation_m']

    def grad(self, xy):
        xy = np.asarray(xy)
        return np.stack([self.sp.ev(xy[..., 0], xy[..., 1], dx=1),
                         self.sp.ev(xy[..., 0], xy[..., 1], dy=1)], axis=-1)

    def bpol(self, r, z):
        return -self.sp.ev(r, z, dy=1)/r, self.sp.ev(r, z, dx=1)/r


def shapes():
    data = np.genfromtxt(ROOT.parent / 'openstep-002/source/SPR45_2D_Wall.csv',
                         delimiter=',', skip_header=2)
    result = []
    for i in range(3):
        w = data[:, 2*i:2*i+2]
        w = w[np.isfinite(w).all(axis=1)] / 1000
        if not np.allclose(w[0], w[-1], atol=1e-12, rtol=0):
            w = np.vstack([w, w[0]])
        result.append(w)
    return result


class Wall:
    def __init__(self, curves=None, radius=0.):
        self.shapes = shapes() if curves is None else [np.asarray(x, float) for x in curves]
        self.radius = radius
        self.polys = [Polygon(w) for w in self.shapes]
        self.lines = [LineString(w) for w in self.shapes]
        assert all(p.is_valid for p in self.polys)
        self.fillets = []
        self.primitives = []
        starts, ends = {}, {}
        if radius:
            for idx in [13, 357]:
                w = self.shapes[0]
                vertex = w[idx]
                d0, d1 = vertex-w[idx-1], w[idx+1]-vertex
                d0, d1 = d0/np.linalg.norm(d0), d1/np.linalg.norm(d1)
                angle = float(np.arctan2(np.linalg.det(np.array([d0, d1])), d0@d1))
                assert 0 < angle < np.pi, 'Requested fillet must be a convex CCW corner'
                tangent = radius*np.tan(angle/2)
                assert tangent < min(np.linalg.norm(vertex-w[idx-1]), np.linalg.norm(w[idx+1]-vertex))
                a, b = vertex-d0*tangent, vertex+d1*tangent
                center = a + radius*np.array([-d0[1], d0[0]])
                start_angle = float(np.arctan2(*(a-center)[::-1]))
                arc = dict(kind='arc', component=0, segment=f'arc-{idx}',
                           center=center, radius=radius, angle0=start_angle,
                           angle=angle, a=a, b=b, d0=d0, d1=d1, vertex=idx)
                self.fillets.append(arc)
                ends[idx-1], starts[idx] = a, b
        for c, w in enumerate(self.shapes):
            for idx, (a, b) in enumerate(zip(w[:-1], w[1:])):
                if c == 0:
                    a, b = starts.get(idx, a), ends.get(idx, b)
                if np.linalg.norm(b-a) < 1e-12:
                    continue
                self.primitives.append(dict(kind='line', component=c, segment=str(idx), a=a, b=b))
        self.primitives += self.fillets

    def signed_distance(self, xy):
        p = Point(float(xy[0]), float(xy[1]))
        values = [self.lines[0].distance(p) * (1 if self.polys[0].covers(p) else -1)]
        values += [line.distance(p) * (-1 if poly.contains(p) else 1)
                   for line, poly in zip(self.lines[1:], self.polys[1:])]
        for arc in self.fillets:
            # Inside the two tangency half-planes, the disk cuts off the corner.
            if (np.dot(xy-arc['a'], arc['d0']) >= 0 and
                    np.dot(xy-arc['b'], arc['d1']) <= 0):
                values.append(arc['radius']-np.linalg.norm(xy-arc['center']))
        return float(min(values))

    @staticmethod
    def point(primitive, t):
        t = np.asarray(t)
        if primitive['kind'] == 'line':
            return primitive['a'] + t[..., None]*(primitive['b']-primitive['a'])
        a = primitive['angle0'] + primitive['angle']*t
        return primitive['center'] + primitive['radius']*np.stack([np.cos(a), np.sin(a)], axis=-1)

    @staticmethod
    def normal(primitive, t):
        if primitive['kind'] == 'line':
            delta = primitive['b']-primitive['a']
            return np.array([-delta[1], delta[0]])/np.linalg.norm(delta)
        # Sign is immaterial to |B.n|; use inward normal consistently.
        return (primitive['center']-Wall.point(primitive, t))/primitive['radius']

    def target(self, xy):
        best = None
        for primitive in self.primitives:
            if primitive['kind'] == 'line':
                delta = primitive['b']-primitive['a']
                t = np.clip(np.dot(xy-primitive['a'], delta)/(delta@delta), 0, 1)
            else:
                angle = np.arctan2(*(xy-primitive['center'])[::-1])
                relative = (angle-primitive['angle0']) % (2*np.pi)
                if relative > primitive['angle']:
                    t = float(np.linalg.norm(xy-primitive['b']) < np.linalg.norm(xy-primitive['a']))
                else:
                    t = relative/primitive['angle']
            distance = float(np.linalg.norm(xy-self.point(primitive, t)))
            if best is None or distance < best[0]:
                best = distance, primitive, float(t)
        distance, primitive, t = best
        return primitive['component'], primitive['segment'], self.normal(primitive, t), distance


def power():
    return json.loads((ROOT.parent / 'openstep-002/results/kinetic-inputs.json').read_text())['P_transport_W']


def heat(field, offset, xy, normal):
    rup = field.d['midplane_radii_m'][1]+offset
    bpu = float(np.hypot(*field.bpol(rup, 0.)))
    bn = abs(float(np.dot(field.bpol(*xy), normal)))
    return dict(Bnormal_target_T=bn, Bpol_upstream_T=bpu,
                area_expansion=bpu/bn if bn else None,
                representative_heat_MW_m2=float(.25*power()*.5*np.exp(-offset/.006)*bn/
                                               (2*np.pi*rup*.006*bpu)/1e6))
