# X-point continuation under asymmetric forcing

November 20, 2026

## Result

In this reduced current-carrying Grad–Shafranov model, the X-point moves continuously under asymmetric forcing, then merges with the magnetic axis at a finite forcing threshold. This is loss of the tracked equilibrium topology. Plasma stability and the proposed TriSphere vessel are outside this test.

## Model

In dimensionless cylindrical coordinates, take

$$
\psi(R,z;\delta)=4(R^2-4)^2+R^2[z^2/2+z^3/3+(1+\delta)z]-R^4z/4.
$$

Direct differentiation gives $\Delta^\ast\psi=(\partial_{RR}-R^{-1}\partial_R+\partial_{zz})\psi=33R^2$. The change in forcing is proportional to $R^2z$, a homogeneous solution, so the source term is fixed. The baseline is already single-null and up–down asymmetric. The forcing is prescribed by an analytic flux term and does not represent independently modeled coils or a self-consistent plasma–vacuum free boundary.

## Continuation

Locate the magnetic axis as a local minimum and the X-point as a saddle. Start the sweep at $\delta=-0.2$, seed the two roots near $(2,0)$ and $(2,-1)$, then use the previous roots as initial guesses in steps of 0.001. The last resolved pair on that grid is at 0.236. Solving the two gradient equations together with the zero-Hessian-determinant condition locates the merger at $\delta=0.2361242835$, $R=1.9863011172$, $z=-0.4850417723$.

| Forcing | Axis z | X-point z | Saddle minus axis flux |
|---:|---:|---:|---:|
| −0.200 | 0.17536 | −1.13689 | 1.474290 |
| 0 | 0 | −0.96546 | 0.588865 |
| +0.100 | −0.11721 | −0.85021 | 0.258097 |
| +0.200 | −0.29590 | −0.67348 | 0.035331 |
| +0.236124 | −0.48504 | −0.48504 | 0 at merger |

## Replay

Run the following with Python, NumPy, and SciPy.

~~~python
import numpy as np
from scipy.optimize import root

def evaluate(point, forcing):
    r, z = point
    v = z*z/2 + z**3/3 + (1 + forcing)*z
    w = z + z*z + 1 + forcing
    flux = 4*(r*r - 4)**2 + r*r*v - r**4*z/4
    gradient = np.array([
        16*r*(r*r - 4) + 2*r*v - r**3*z,
        r*r*(w - r*r/4),
    ])
    cross = 2*r*w - r**3
    hessian = np.array([
        [16*(3*r*r - 4) + 2*v - 3*r*r*z, cross],
        [cross, r*r*(1 + 2*z)],
    ])
    return flux, gradient, np.linalg.eigvalsh(hessian)

axis, saddle = [2, 0], [2, -1]
for increment in range(-200, 351):
    forcing = increment / 1000
    roots = [
        root(lambda p: evaluate(p, forcing)[1], guess, tol=1e-10)
        for guess in (axis, saddle)
    ]
    axis, saddle = (result.x for result in roots)
    fa, ga, ea = evaluate(axis, forcing)
    fx, gx, ex = evaluate(saddle, forcing)
    if max(np.linalg.norm(ga), np.linalg.norm(gx)) > 1e-8 or not (
        ea[0] > 0 and ex[0] < 0 < ex[1]
    ):
        print("First failed continuation step:", forcing)
        break
    if increment in {-200, 0, 100, 200, 236}:
        print(forcing, axis, saddle, fx - fa)

def merger(state):
    flux, gradient, eigenvalues = evaluate(state[:2], state[2])
    return [*gradient, np.prod(eigenvalues)]

fold = root(merger, [1.987, -0.49, 0.237], tol=1e-12)
assert np.max(np.abs(merger(fold.x))) < 1e-8
print("Merger (R, z, forcing):", fold.x)
~~~

The magnetic flux Hessian classifies poloidal critical points. A plasma stability test would need a separate perturbation calculation along a self-consistent equilibrium branch. No stability window or preferred TriSphere layer follows from this result.
