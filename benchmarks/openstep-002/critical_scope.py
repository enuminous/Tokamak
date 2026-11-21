"""Limit iterative axis/X searches to the expected plasma, not coil filaments.

Final diagnostics/residual use the original full-domain search. This is a
Newton-iteration acceleration, not a change in the accepted physical model.
"""
import numpy as np
from freegs import critical
ORIGINAL=critical.find_critical
BOUNDS=(1.25,6.25,-7.25,7.25)
def scoped(R,Z,psi,discard_xpoints=True):
    ir=np.flatnonzero((R[:,0]>=BOUNDS[0])&(R[:,0]<=BOUNDS[1]))
    iz=np.flatnonzero((Z[0]>=BOUNDS[2])&(Z[0]<=BOUNDS[3]))
    sl=np.ix_(ir,iz)
    return ORIGINAL(R[sl],Z[sl],psi[sl],discard_xpoints=discard_xpoints)
def install():critical.find_critical=scoped
def restore():critical.find_critical=ORIGINAL
