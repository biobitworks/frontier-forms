# Module arms: incremental additions and LOMO (run v1)

Each arm is frozen B0 plus a set of modules (`src/frontier_forms/forms/arms.py`). Graph edges join arms that differ in one module, so each edge attributes its change to a single leaf. `FCG_ARMS_V1.json` holds the nodes (arm output roots), the edges (paired exact McNemar and template-stratified bootstrap, overall and on the test split) and the graph root.

Endpoint: success on every required field of a form, paired by case digest. Test split: 54 forms from 18 patients.

| Arm | All forms | Test forms | Field accuracy |
|---|---|---|---|
| B0 | 0.463 | 0.333 | 0.856 |
| B0+L1 evidence abstain | 0.477 | 0.333 | 0.917 |
| B0+L2 unit validation | 0.463 | 0.333 | 0.865 |
| B0+L3 clinical filter | 0.495 | 0.333 | 0.902 |
| B0+L1+L3 | 0.720 | 0.556 | 0.950 |
| Full (L1+L2+L3) | 0.720 | 0.556 | 0.959 |

Under the predeclared golden-path rule, no single module qualifies. On the test split, adding any one module to B0 leaves form success unchanged. LOMO shows L1 and L3 are each necessary in the full candidate (test delta +0.222, exact McNemar p=0.00049, bootstrap CI [0.13, 0.33]).

Post hoc note: L1 and L3 interact, because most failing forms have both an allergy and a conditions error. The path B0 → +L1 → +L1+L3 is where the gain appears. L2 improves only the pounds field, which is not required, so it cannot move this endpoint.

Leakage note: these modules were written after B0 errors were viewed on all splits. Treat this as discovery only, until it is replicated on a new cohort or template set.
