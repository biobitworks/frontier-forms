# Common red-team rubric v1 (method lane)

Every lane gets the same evidence snapshot: the candidate freeze manifest and the destination snapshot it names. No lane may read another lane's report before its own first report is sealed (hashed in `CONSENSUS_AND_DISSENT.md`).

Bounded decision options (the only allowed outputs per question):

| Q | Question | Options |
|---|---|---|
| Q1 | Do stored atom bytes match the manifest? | SOURCE_CONSISTENT / SOURCE_INCONSISTENT / INSUFFICIENT_EVIDENCE |
| Q2 | Is there leakage across batch, target, row content or normalization? | LEAKAGE_DETECTED / NO_LEAKAGE_DETECTED_BY_TEST / NOT_TESTED |
| Q3 | Is the freeze compatible with the frozen preregistration? | PROTOCOL_COMPATIBLE / PROTOCOL_CONTRADICTED / UNKNOWN |
| Q4 | Admission recommendation | ADMIT_RECOMMENDED / REJECT_RECOMMENDED / HOLD_RECOMMENDED |

Rules: a deterministic integrity failure overrides any model vote. A valid root does not override demonstrated leakage, invalid licensing or protocol contamination. Model confidence is advisory.
