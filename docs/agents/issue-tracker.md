# Issue tracker: Local Markdown

Issues and specifications for this repo live as Markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The specification is `.scratch/<feature-slug>/spec.md`.
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`; do not create a single combined tickets file.
- Triage state is recorded as a `Status:` line near the top of each issue file. Use the roles defined in `triage-labels.md`.
- Comments and conversation history are appended under a `## Comments` heading.
- Preserve links from the tracker file to its authoritative source records and EvidenceRecords.
- Do not store secrets or unnecessary sensitive client information in tracker files.

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/`, creating the feature directory if necessary.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally provide the path or issue number directly.

## Wayfinding operations

- **Map:** `.scratch/<effort>/map.md`, containing Notes, Decisions-so-far, and Fog.
- **Child ticket:** `.scratch/<effort>/issues/NN-<slug>.md`, with a `Type:` line (`research`, `prototype`, `grilling`, or `task`) and a `Status:` line.
- **Blocking:** record `Blocked by: NN, NN` near the top. A ticket is unblocked when every listed ticket is resolved.
- **Frontier:** scan the effort's `issues/` directory for open, unblocked, and unclaimed tickets; the first numbered ticket wins.
- **Claim:** set `Status: claimed` and save before starting work.
- **Resolve:** append the result under `## Answer`, set `Status: resolved`, and add the context pointer to the map's Decisions-so-far.

## Sync and visibility

The tracker is local to the vault and can sync through the vault's existing file-sync mechanism. Because `.scratch/` begins with a dot, Obsidian may hide it from the standard file explorer even though the files exist and sync. Use a filesystem browser or another Markdown editor when direct access is required.
