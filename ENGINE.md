# Recirculating Muon Engine

This simulator explores an engine architecture motivated by A. Beth Jones’s TriSphere return loop. It tracks externally produced muons as a depleting catalyst population. It provides no hardware design, radiation analysis, or experimental validation.

## Catalyst and energy ledgers

An active muon survives a cycle of duration t with probability s = exp(−t/τ), using the free-muon mean lifetime τ ≈ 2.197 μs. It produces one fusion in this model if it survives. Afterward, it sticks with probability p. A fraction r of unstuck muons returns. The continuation probability is q = s(1−p)r and expected fusions per injected muon are s/(1−q). Probabilities of eventual decay, sticking, and return loss sum to one.

Each modeled D–T event adds approximately 3.5 MeV to charged products and 14.1 MeV to neutrons. The chosen charged recovery fraction supplies the useful energy ledger. Neutron energy is recorded and excluded from torch credit. Bootstrap cost is charged per delivered muon. The model assumes steady supply after startup. A negative internally funded margin gates the jet to zero. External bootstrap, when selected, is displayed as a separate power demand and allows recovered energy to be spent on the jet.

Ideal thrust is √(2 ṁ Pjet) for a nonrelativistic, fully directed jet. The mass flow is a separate propellant input and no model converts fusion products directly into thrust. The energy ledger excludes auxiliary loads and capture infrastructure. The quark chamber has no reaction model and contributes zero energy.

Default settings give about 56.11 fusions per delivered muon, 117.84 MeV recovered against 9,000 MeV assumed bootstrap cost, and zero internally funded thrust. These are illustrative results under chosen parameters.

## Sources

- [Particle Data Group](https://pdg.lbl.gov/)
- [ITER Engineering Basis Handbook, Volume 1 Chapter 4](https://www.iter.org/sites/default/files/media/2026-01/vol.1_ch.04_role_and_distinctive_feature_dv4qgd_v2_0.pdf)
- [CERN, Heavy ions and quark–gluon plasma](https://home.web.cern.ch/science/physics/heavy-ions-and-quark-gluon-plasma/)
- [A. Beth Jones, TriSphere](https://tri-sphere-text.abethjones.workers.dev/)
