"""Conservative 1-D diffusion in an explicitly assumed homogeneous slab."""
from pathlib import Path
import json,csv,itertools,hashlib
import numpy as np
from scipy.linalg import solve_banded
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'

def simulate(k,L,q,n=80,dt=.01,end=20.):
    cv=2.5e6;Tback=450.;dx=L/n;cap=cv*dx;g=k/dx
    # Cell-centered finite volumes. q enters front face; last center is dx/2
    # from the Dirichlet coolant face. Backward Euler is unconditionally stable.
    A=np.zeros((3,n));A[1]=cap/dt+2*g;A[1,0]=cap/dt+g;A[1,-1]=cap/dt+3*g
    A[0,1:]=-g;A[2,:-1]=-g
    T=np.full(n,Tback);inenergy=0.;outenergy=0.;trace=[];balance=0.
    for it in range(round(end/dt)):
        rhs=cap/dt*T;rhs[0]+=q;rhs[-1]+=2*g*Tback
        T=solve_banded((1,1),A,rhs,check_finite=False)
        outflux=2*g*(T[-1]-Tback);inenergy+=q*dt;outenergy+=outflux*dt
        balance=max(balance,abs(cap*np.sum(T-Tback)-(inenergy-outenergy)))
        if it%max(1,round(.1/dt))==0 or it==round(end/dt)-1:
            trace.append(dict(time_s=(it+1)*dt,surface_K=float(T[0]+q*dx/(2*k)),back_flux_W_m2=float(outflux)))
    surface=float(T[0]+q*dx/(2*k));steady=Tback+q*L/k
    row=dict(conductivity_W_mK=k,thickness_m=L,heat_flux_MW_m2=q/1e6,cells=n,dt_s=dt,
        surface_at_20s_K=surface,analytic_steady_surface_K=steady,energy_balance_relative=balance/inenergy,
        fraction_of_steady_temperature_rise=(surface-Tback)/(steady-Tback))
    return row,trace

def main():
    rows=[]
    for k,L,q in itertools.product([80.,120.,180.],[.005,.01,.02],[1e6,5e6,1e7,2e7]):
        row,trace=simulate(k,L,q);rows.append(row)
    refinement=[]
    for n,dt in [(40,.02),(80,.01),(160,.005)]:
        row,trace=simulate(120,.01,1e7,n,dt);refinement.append(row)
        with (OUT/f'thermal-central-{n}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=trace[0]);w.writeheader();w.writerows(trace)
    with (OUT/'thermal-sweep.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    report=dict(cases=len(rows),refinement=refinement,max_energy_balance_relative=max(x['energy_balance_relative'] for x in rows),
        max_surface_K=max(x['surface_at_20s_K'] for x in rows),min_surface_K=min(x['surface_at_20s_K'] for x in rows),
        assumptions=['Homogeneous constant k and heat capacity','Perfectly temperature-clamped back face','Prescribed uniform surface flux; no radiation, coolant resistance, phase change or erosion'],
        physical_status='UNRESOLVED: thermal response under assumed parameters, not component qualification',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        amendment_sha256=hashlib.sha256((ROOT/'AMENDMENTS.md').read_bytes()).hexdigest())
    (OUT/'thermal.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
