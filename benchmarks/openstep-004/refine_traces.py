"""Post hoc third-tolerance replay at the fixed representative 1 mm offset."""
from pathlib import Path
import json
import time
import numpy as np
import validate as v


def main():
    result = v.stamp('representative_refinement')
    result['driver_sha256'] = v.sha(__file__)
    result['amendment_sha256'] = v.sha(v.ROOT/'AMENDMENTS.md')
    result['settings'] = dict(rtol=1e-12, atol=[1e-13,1e-13,1e-11], max_step_rad=.025)
    original_ivp = v.solve_ivp
    def refined_ivp(*args, **kwargs):
        kwargs.update(rtol=1e-12, atol=[1e-13,1e-13,1e-11], max_step=.025)
        return original_ivp(*args, **kwargs)
    # Inject only integration parameters; do not modify validate.py or the field.
    v.solve_ivp = refined_ivp
    wall = v.Wall(v.s.walls())
    power = json.loads((v.ROOT.parent/'openstep-002/results/kinetic-inputs.json').read_text())['P_transport_W']
    rows, checks, paths = [], [], {}
    for path, prior in v.inventory():
        start = time.time()
        f = v.Field(path)
        row, points = v.trace(f, wall, .001, tight=True)
        row['representative_heat_MW_m2'] = v.heat(row, f, power)
        row['tolerance_level'] = 'third'
        v.check_trace(checks, f.arm+':third', row)
        rows.append(row)
        paths[f.arm] = points
        result.update(rows=rows, checks=checks)
        v.save('representative-refinement.json', result)
        np.savez_compressed(v.OUT/'representative-refinement-paths.npz', **paths)
        print(f'Third tolerance {f.arm}: flux drift {row["normalized_flux_drift"]:.3g}; {time.time()-start:.1f}s', flush=True)


if __name__=='__main__':
    main()
