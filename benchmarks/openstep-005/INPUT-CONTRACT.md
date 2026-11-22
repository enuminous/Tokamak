# Inputs required for actual-device wall modes and feedback

Current status: **NOT RUN / UNRESOLVED**. `device-inputs.json` records the
available equilibrium and wall-outline references and leaves missing inputs
empty. `wall_feedback.validate_inputs` is a completeness gate, not a calibration
or assurance certificate. A metadata field saying `reviewed` is not independent
evidence that review occurred.

Every section requires `source_ref`, a 64-character lowercase `sha256`, `units`,
`model`, and `calibration_status`. For a proposed device run, the evidence class
must be `calibrated_device_inputs` and each calibration status must be `reviewed`.
Retain the actual source records and review evidence alongside those metadata.

| Section | Required physical content and additional fields |
|---|---|
| `equilibrium` | Pinned equilibrium, current/pressure profiles, mesh and convergence evidence; flux and coordinate conventions |
| `conductor_geometry` | Closed conducting volumes or shell mesh with material regions; model is `axisymmetric_volume_mesh` or `thin_shell_mesh_with_thickness`; the latter requires positive `thickness_m` |
| `material_resistivity` | Positive `resistivity_ohm_m` and `temperature_K`, with material/temperature dependence and uncertainty; use a spatial material model where a single value is insufficient |
| `electrical_connections` | Continuous/segmented structures, breaks, contacts, mutual coupling and external return paths |
| `active_coils` | Winding geometry, turns and dynamic electrical circuit, including resistance and inductance; fixed ampere-turns alone are insufficient |
| `plasma_response` | Verified distributed or reduced response and its assumptions; rigid force stiffness alone does not define inertia or a mode spectrum |
| `sensors` | Position/flux response, noise, positive `sample_rate_Hz`, nonnegative `latency_s` |
| `actuators` | Circuit/power-supply response and positive `voltage_limit_V`, `current_limit_A`, `bandwidth_Hz` |
| `controller` | Explicit feedback law, signs, units, sample/hold behavior, nonnegative `latency_s`, limits and failure handling |

Validate a completed proposal with:

```python
import json
from wall_feedback import validate_inputs
result = validate_inputs(json.load(open("device-inputs.json")))
print(result)
```

This does not launch TokaMaker or certify a device. The native TokaMaker model
must be built and checked independently against the supplied equilibrium and
conducting mesh before interpreting eigenmodes. Mesh convergence, passive-wall
limits, time integration, actuator limits and sampled/latent feedback require
explicit acceptance tests for that model. The present synthetic four-state
fixture is only a test of its own reduced equations.

Relevant primary documentation:

- [TokaMaker vertical-stability example](https://openfusiontoolkit.github.io/OpenFUSIONToolkit/docs/v26.9/doc_tMaker_DIIID_ex2.html)
- [Pinned OpenSTEP wall construction](https://github.com/ukaea/OpenSTEP/blob/6f66ae09c60b361d600b178416ef3f22b8d0aa6a/scripts/wall.ipynb)
