Architect Approval Contract

The Architect is the sole human root authority for Station Calyx.

Any action that mutates system state MUST be accompanied by:

A proposal artifact

An approval receipt referencing the proposal hash

A valid cryptographic signature produced by the Architect’s registered key

No software agent, including CBO, may:

Generate Architect signatures

Derive passphrases

Substitute automated inference for human approval

Absence of a valid signature SHALL be treated as explicit denial.