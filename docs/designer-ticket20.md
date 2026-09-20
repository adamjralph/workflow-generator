# Ticket 20 — capture and preview the oldest eligible draft

**Accepted and closed:** Adam explicitly accepted ticket 20 ("accept").

Ticket 20 delivers capture only, not Generator/Guardian execution or conformance.
Implementation review baseline approved by Adam:
`35b9a5d7ac8784c062d25ec91f367e6c6d9ffb93`.

## Observable behavior

Choose **LinkedIn draft capture (no execution)** in the browser. Capture previews
one exact source, the selection inventory, explicit guidance with provenance and
digests, both profiles' current non-secret provider/default selections, instruction
version and private evidence destination. No Run or Check is offered for this mode.
Existing offline modes and controlled JSON writing briefs remain available.

Only top-level regular UTF-8 `.md` files in the configured content-drafts directory
are eligible. Folder membership supplies article/post classification. Exact
`public-copy-bank.md` is excluded *before parsing*; it need not have frontmatter.
Directories and non-Markdown entries are listed as exclusions, not traversed.
Inbox and published directories are not searched. `processed: true` and explicit
published metadata exclude content. `processed` must be a literal YAML boolean;
false requires `date_created: YYYY-MM-DD`, quoted or unquoted. Invalid potential
drafts block the entire selection rather than silently skip possibly older input.
Duplicate YAML keys, aliases, unsafe files and oversized inputs fail visibly.
Dates are never manufactured. Equal dates sort by exact filename, ascending.

Approved bounds: 256 directory entries, 64 KiB per draft, 128 KiB per guidance file,
512 KiB total text read from inspected drafts and captured guidance. No truncation.
The manifest is bounded to 64 KiB and each profile YAML to 128 KiB. Model identifiers
are bounded nonempty strings, never URLs, and are not authenticated at capture.

Capture does not establish publication permission, model availability or semantic
correctness. It never changes processing flags, moves sources or archives content.
A repeated capture can select the same oldest draft. Capturing private material
is not authorization to use it publicly. The eventual two-generation-call ceiling
is shown as future execution policy, not a claim that execution exists here.

## Operator setup

Install the pinned development dependencies, including PyYAML and its type stubs.
Create an operator-owned JSON manifest **outside the evidence directory**. The
following example uses the authority set explicitly approved for ticket 20; paths
are local operator configuration, never browser input. Relative paths resolve
against the manifest's parent; `~` is expanded. Do not put credentials in it.

```json
{
  "drafts_dir": "~/Documents/life-os/Business/Personal Brand/content-drafts",
  "guidance": {
    "generator_soul": "~/.hermes/profiles/stillroom-signal-generator/SOUL.md",
    "guardian_soul": "~/.hermes/profiles/stillroom-signal-guardian/SOUL.md",
    "generator_skill": "~/.hermes/profiles/stillroom-signal-generator/skills/stillroom-writing-workflow/SKILL.md",
    "guardian_skill": "~/.hermes/profiles/stillroom-signal-guardian/skills/stillroom-signal-workflow/SKILL.md",
    "writing_skill": "~/.hermes/skills/business/adam-content-writing/SKILL.md",
    "voice_profile": "~/.hermes/skills/business/adam-content-writing/references/voice-profile.md",
    "writing_craft": "~/.hermes/skills/business/adam-content-writing/references/writing-craft.md",
    "brand_index": "~/Documents/life-os/Business/Personal Brand/INDEX.md",
    "offer": "~/Documents/life-os/Business/Personal Brand/offer.md",
    "audience": "~/Documents/life-os/Business/Personal Brand/audience.md",
    "product": "~/Documents/life-os/Business/Personal Brand/product.md",
    "content_system": "~/Documents/life-os/Business/Personal Brand/content-system.md",
    "guardian_checklist": "~/Documents/life-os/Business/Personal Brand/signal-guardian-checklist.md",
    "current_vs_superseded": "~/Documents/life-os/Business/Stillroom/CURRENT VS SUPERSEDED.md"
  },
  "profiles": {
    "generator": "~/.hermes/profiles/stillroom-signal-generator/config.yaml",
    "guardian": "~/.hermes/profiles/stillroom-signal-guardian/config.yaml"
  }
}
```

```bash
.venv/bin/python -m agent_lab.designer \
  --evidence-dir /your/private/capture-evidence \
  --draft-config /your/operator/capture.json
```

Open the exact printed loopback URL. Guidance files may be explicitly configured
links (installed skills are linked); resolved targets and their exact text are
captured. Their internal links are **not followed**. The complete set of 14 labels
is required. Missing/unreadable guidance or model selections fail capture rather
than silently dropping authority or substituting a model. Profile YAML is read
only to extract `model.provider` and `model.default`; full config and credential
values are never persisted or returned. No Hermes code is imported or invoked.

Manifest paths are pinned at server startup. Restart after changing the manifest.
Source/guidance/model edits require explicit recapture; existing bundles are not
rewritten. A mode change or recapture clears the visible preview and invalidates
late success, blocked and error responses. Inputs are rendered as inert text.

## Public seams and evidence

- `DraftSource(config_file, evidence_dir, protected_roots=()).capture()` selects,
  validates and stores a snapshot, or returns visible selection findings without
  storing an input bundle. I/O/configuration failures raise sanitized errors.
- `DraftSource.load(snapshot)` verifies the bounded canonical bundle and all
  embedded text digests without rereading original inputs. This is input-bundle
  integrity checking, **not** workflow replay or conformance.
- `GET /api/drafts` reports configuration availability only. It does not capture
  inputs. `POST /api/drafts/capture` accepts only `{}` under the existing exact
  loopback Host/Origin/token and JSON/body protections. There are no draft run,
  check or arbitrary-path/load HTTP endpoints.
- Canonical, digest-addressed input bundles live under `draft-snapshots` in the
  caller-selected protected evidence root. UTF-8 strings preserve exact source
  and guidance bytes, including CRLF. Records include source/guidance digests,
  inventory, non-secret models, provenance and private format/instruction versions.
- Publication uses an fsynced temporary file and atomic no-overwrite link;
  recapture verifies existing content instead of overwriting corruption. Snapshot
  directory permissions are private; bundles are owner-only regular files. Hashes
  establish local integrity, not signatures or protection against an owner who
  rewrites history. General crash-durable workflow resume is not implemented.
- Source/evidence overlap, changed parent aliases, unsafe draft files, output
  symlinks, non-private stores and configured Hermes/project evidence roots fail.

## Verification

Tests use synthetic temporary inputs only; no production draft/guidance content
is committed. Public capture/load tests cover selection and invalid metadata,
limits, immutable bytes, model/guidance recapture, protected roots and corruption.
Actual HTTP/CLI tests cover auth/body boundaries, strict request/config schemas,
no capture on availability, error sanitation and concurrent captures. Real Chromium
tests cover preview, invalid/missing sources, inert rendering and stale responses.

- Full offline suite: **1,139 passed, 3 expected skips**, including **114 real
  Chromium tests** (none skipped). Console: `/tmp/workflow-ticket20-full-suite.txt`.
- The skips are two opt-in live Jev tests and the optional real Hermes loader check.
- Ticket-20 capture, HTTP/CLI and Chromium seams add **135 tests**, including two
  review regressions; the initial focused run was 133 passed before those additions.
- Mypy: **27 source files, no issues**. Diff whitespace checks passed; Graft refreshed.
- Implementation: `e000f8a`; review fixes: `3b6224a`. Full suite ran once after
  review fixes, with `AGENT_LAB_JUDGMENT=stub`. No runtime edits after that run.
- Read-only configuration inspection confirmed the profile defaults still resolve
  to Generator `openai-codex / gpt-5.6-sol` and Guardian
  `vertex / google/gemini-3.1-pro-preview`. The public copy bank no longer has
  frontmatter. This is not live authentication/model or production-capture evidence.

No live smoke, credential-content reads, authentication traffic, model calls or
protected writes occurred. Private production text was not copied into fixtures
or evidence. Actual-input capture remains an operator action with a named output
root. Adam has accepted this delivered capture-only slice.

### Standards

Initial independent review found one low-severity documented violation: missing
`Type: task` in the local ticket. Fixed. One optional duplicated-eligibility-predicate
heuristic remains intentionally deferred. Follow-up review confirmed **0 outstanding
hard findings and 0 new heuristic findings**.

### Spec

Initial independent review found two correctness defects: successful publication of
an unloadable bundle when an excluded filesystem name is not UTF-8, and false
rejection of valid evidence while atomic publication temporarily gives its inode
two hard links. Both were reproduced red-first and fixed. Capture now validates
the complete bundle before writing; privacy is checked through ownership and
permissions, not transient link count. A deterministic filesystem-boundary test
exercises public capture/load during the publication window. Independent follow-up
confirmed both fixes, **0 outstanding actionable findings**, and reran all 78
capture/load tests successfully. The reviewer described the HTTP concurrency test
as single-threaded; the server actually uses ThreadingHTTPServer, but the identified
interleaving was real and is now exercised deterministically.

**Review summary:** Standards 0 outstanding hard findings (1 optional heuristic);
Spec 0 outstanding actionable findings.
