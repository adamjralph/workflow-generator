# Regeneration rewrites only generated regions; hand-edits live in a user layer

Generated output is written between **generated-region markers**, and anything a human writes lives
outside them in a **user layer**. Regeneration rewrites only the marked regions, so hand-edits
survive. We rejected clobbering because it makes the tool unusable on real work, and one-shot
generation because it makes iteration impossible. This is the mechanism that satisfies the
"hand-edit without losing edits" requirement; without it, the first edit makes the workflow
un-regenerable.

## Considered Options

- **Clobber on regeneration** — simple, but destroys user work on every run.
- **One-shot generation only** — avoids the conflict by forbidding iteration.
