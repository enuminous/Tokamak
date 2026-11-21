"""Cached von Hagenow boundary integral, algebraically matching FreeGS 0.8.2.

Adapted from freegs.boundary.freeBoundaryHagenow by Ben Dudson, University of York
(2016). LGPL-3.0-or-later; see LICENSE-FreeGS.txt. Only invariant Green-function
and Romberg quadrature weights are cached. The equation and 0.01 m boundary
offset are unchanged. Independent equivalence check is in boundary_check.py.
"""
import numpy as np
from scipy.integrate import romb
from freegs.gradshafranov import Greens

class CachedHagenow:
    def __init__(self,eq):
        R,Z=eq.R,eq.Z;nr,nz=R.shape
        dr,dz=eq.dR,eq.dZ
        # Preserve original down/up/left/right traversal and duplicate corners.
        self.ij=np.array([(i,0) for i in range(nr)]+[(i,nz-1) for i in range(nr)]+[(0,j) for j in range(nz)]+[(nr-1,j) for j in range(nz)])
        eps=np.array([(0.,-.01)]*nr+[(0.,.01)]*nr+[(-.01,0.)]*nz+[(.01,0.)]*nz)
        target=np.c_[R[self.ij[:,0],self.ij[:,1]],Z[self.ij[:,0],self.ij[:,1]]]+eps
        sources=np.vstack([np.c_[R[0],Z[0]],np.c_[R[-1],Z[-1]],np.c_[R[:,0],Z[:,0]],np.c_[R[:,-1],Z[:,-1]]])
        wr=romb(np.eye(nr),axis=1);wz=romb(np.eye(nz),axis=1)
        weights=np.r_[wz*dz/R[0],wz*dz/R[-1],wr*dr/R[:,0],wr*dr/R[:,-1]]
        self.matrix=np.empty((len(target),len(sources)))
        for i in range(0,len(target),64):
            t=target[i:i+64]
            self.matrix[i:i+64]=Greens(sources[None,:,0],sources[None,:,1],t[:,None,0],t[:,None,1])*weights
    def __call__(self,eq,Jtor,psi):
        rhs=eq.R*Jtor;rhs[0,:]=rhs[-1,:]=0.;rhs[:,0]=rhs[:,-1]=0.
        u=eq.callSolver(psi,rhs)
        c=np.array([25/12,-4,3,-4/3,.25])
        left=np.einsum('i,ij->j',c,u[:5])/eq.dR
        right=np.einsum('i,ij->j',c,u[-1:-6:-1])/eq.dR
        down=u[:,:5]@c/eq.dZ;up=u[:,-1:-6:-1]@c/eq.dZ
        d=np.hypot(eq.dR,eq.dZ);i=np.arange(5)
        left[0]=down[0]=np.dot(c,u[i,i])/d
        left[-1]=up[0]=np.dot(c,u[i,-1-i])/d
        right[0]=down[-1]=np.dot(c,u[-1-i,i])/d
        right[-1]=up[-1]=np.dot(c,u[-1-i,-1-i])/d
        values=self.matrix@np.r_[left,right,down,up]
        for (i,j),v in zip(self.ij,values):psi[i,j]=v
