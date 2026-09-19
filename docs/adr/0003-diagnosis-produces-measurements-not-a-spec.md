# Diagnosis produces measurements, not an inferred workflow spec

Diagnosis measures how an existing workflow behaves — calls per run, context per call, tokens per
run, cache hit rate, per role and per run — and that evidence is the baseline against which
generation is judged. It deliberately does **not** infer a formal spec from logs: an inferred graph
would be an unverified model output masquerading as evidence, and a spec is *authored*, not guessed.
The design that generation consumes comes from the questionnaire, not from diagnosis. We chose this
over auto-inference so the spec boundary stays trustworthy, and so "diagnosis output is the input to
generation" means "the baseline", not "a draft spec".

## Considered Options

- **Measurements plus an auto-inferred graph** — more convenient, but its output is unverifiable and
  would be mistaken for evidence.
