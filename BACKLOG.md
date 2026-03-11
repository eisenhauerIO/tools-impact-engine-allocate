# Backlog

## Add a public solver interface / facade

Right now users must import and instantiate solver classes (`BayesianSolver`,
`MinimaxRegretSolver`) directly. We need a unified entry-point (e.g. a factory
function or facade) that selects and runs the appropriate solver by name, so
callers don't couple to concrete classes.
