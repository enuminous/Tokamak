"""Independent coil-field crosscheck and constrained-profile checks."""
import json
import numpy as np
import screens as s

def main():
    f=s.Field('baseline',129);mask=np.abs(f.j)>0
    r,z,j=f.R[mask],f.Z[mask],f.j[mask];machine=s.b.machine(f.ref);h=.005
    force=lambda zz:float(np.sum(-2*np.pi*r*j*machine.Br(r,zz))*f.da)
    direct=(force(z+h)-force(z-h))/(2*h)
    interpolated=s.vertical(f)['translations'][1]['dFz_dz_N_per_m']
    s.save('force-independent-check.json',dict(grid=129,analytic_coil_force_gradient=direct,
        interpolated_coil_force_gradient=interpolated,relative_difference=abs(interpolated/direct-1)))
    output=[]
    for arm,n in [('baseline',257),('p9-inward',129),('p9-inward',257)]:
        report=s.OUT/f'{arm}-{n}-controlled.json'
        if not report.exists() or not json.loads(report.read_text()).get('converged'):continue
        f=s.Field(arm,n,True);row=s.magnetic(f)
        target=json.loads((s.b.ROOT/'results/baseline-257-symmetric.json').read_text())['final']
        span=target['psi_axis']-target['psi_boundary'];ref=f.ref['pp'].antiderivative();pp=f.pp.antiderivative();ss=np.linspace(0,1,101)
        expected=span*(ref(1)-ref(ss));actual=f.span*(pp(1)-pp(ss))
        row['pressure_profile_relative_error']=float(np.max(abs(actual-expected))/target['pressure_axis_Pa']);output.append(row)
    s.save('controlled-magnetic.json',output)
    print('Independent force and controlled-profile checks recorded')
if __name__=='__main__':main()
