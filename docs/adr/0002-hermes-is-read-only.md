# Hermes is read-only; generated artifacts live in a user-named store

The tool must never edit Hermes source, configuration, authentication, or live board/profile state,
and "no writes to Hermes" is defined to mean exactly those things. Everything the tool produces —
the spec, the emitted workflow, run logs, and approval records — is written to the tool's own
**artifact store** or to a project directory the user names. Reading Hermes (profiles, models,
skills, usage databases) is always allowed. We chose a precise boundary because an imprecise one
would leave "is writing a generated workflow to disk allowed?" genuinely undecidable, and a boundary
that is not written down is one that erodes.

## Considered Options

- **Diagnose-only, no writes at all** — too strict: the tool cannot function without persisting its
  own specs, logs, and approvals.
- **Imprecise "don't modify Hermes"** — the status quo; leaves the artifact question unanswered.
