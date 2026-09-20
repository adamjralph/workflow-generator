# Ticket 16 — custom support-request runs

Review baseline: `eabde12de4cda2c8e2040e6b568902ff75c608d7` (implementation starting HEAD).
Scope: `.scratch/workflow-generator/issues/16-try-custom-support-requests.md`.

## Try it

```bash
.venv/bin/python -m agent_lab.designer --evidence-dir /tmp/workflow-ticket16-evidence
```

Open the printed loopback URL, select **Support-request triage**, and enter
**Request ID**, **Request category**, **Request urgency**, and **Short description**
in **Try a custom support request**. Click **Run request**. **Generate / check**
continues to check only the six supplied cases. Its displayed evidence is not
changed by editing custom inputs or running them.

## Contract

- `designer.custom.run_request(design, request, evidence_dir=...)` admits the
  current triage design and strictly validates all four request fields before
  generation. `TriageRequest` holds the existing input fields; `TriageState`
  inherits them and adds the existing output fields. There is no second field
  rule set or execution model. HTTP cannot initialize team, priority or summary.
- Private `POST /api/run` accepts exactly `{design, request}`. The existing exact
  loopback Host, Origin, page token, JSON content type, 4096-byte body limit and
  read timeout apply. No HTTP-selected code, file paths or output roots.
- The admitted Spec generates a real `GraphCandidate`, whose structure and state
  type must match before execution. The existing graph engine executes once,
  with fresh state, Budget/RunAccounting, a fresh run ID and a fresh log under
  the caller-selected protected evidence root. No reference execution or
  conformance check is added for custom input.
- Results show submitted input, observed labeled route, final state, terminal,
  spent steps and the candidate log path. `succeeded` means only `COMPLETED`,
  never conformance PASS or semantic correctness. Safety terminals are failed
  runs. Generation/runtime/audit/evidence exceptions cannot return success;
  persisted evidence is read before a result is returned.
- Custom responses use their own revision counter. Every workflow edit and
  every request input/change invalidates completed and in-flight custom results,
  including late failures. They do not invalidate an otherwise current
  supplied-case check. Invalid designs disable both actions.
- All custom output, input and error text uses `textContent`, not HTML. Category
  and urgency alone select routes; descriptions are never interpreted.
- No model calls, live integrations, Hermes writes, activation, persistent Spec
  format, bulk inputs, Parallel, Gates or new runtime.

## Test-first verification

Ticket-specified seams: public run API, actual loopback HTTP, real Chromium.

1. Public tracer failed with missing `designer.custom`; after implementation it
   executed six independently specified category/urgency examples with fresh
   evidence and accounting. Added strict invalid-field, edited design, actual
   candidate output, maximum Unicode bounds, protected-root and I/O probes.
2. HTTP tracer failed with 404 for `/api/run`; adding the protected endpoint made
   it pass. Added invalid envelope/design/field, security/body-bound and visible
   generation/execution/evidence failure tests.
3. Chromium tracer failed because **Run request** did not exist. Added the form
   and separate results; tested all six examples, unchanged conformance evidence,
   inert markup, invalid inputs/designs, current authored operations, failures and
   held/released success/error responses after all four request fields and
   workflow team/entry/removal/mode edits.

Targeted commands (run throughout implementation):

```bash
.venv/bin/python -m pytest -q tests/test_designer_custom.py
.venv/bin/python -m pytest -q tests/test_designer_custom_server.py
.venv/bin/python -m pytest -q tests/test_designer_custom_browser.py tests/test_designer_triage_browser.py tests/test_designer_browser.py
.venv/bin/python -m mypy agent_lab
```

## Final verification and review

Two independent reviewers examined the scoped staged changes against the starting
HEAD above, excluding unrelated working-tree edits:

- **Standards:** no documented violations or material heuristic smells.
- **Spec:** two confirmed gaps, both fixed. Dropping an audit write silently could
  leave contiguous sequence numbers and still report success; custom runs now
  require the complete event count, per-event accounting and route continuity.
  Chromium's native `maxlength` counted UTF-16 units instead of Python Unicode
  code points; description limits now use the authoritative strict server rules.
  Both reproductions failed before fixes and pass afterward, including real
  Chromium entry of 240 emoji and rejection of 241.

Final targeted custom API/browser run: **73 passed**. Full offline regression
was run once after fixes:

```bash
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q -rs
# 808 passed, 3 skipped in 150.18s
.venv/bin/python -m mypy agent_lab
# Success: no issues found in 24 source files
 git diff --check
# clean
```

Expected skips: two opt-in live Jev calls and the optional real Hermes plugin
loader check. All **44 real Chromium tests** ran, none skipped. Local console
record: `/tmp/workflow-ticket16-full-suite.txt`. Graph refreshed with `graft build`.
Existing score composition and supplied-case triage checks remain covered.
Unrelated working-tree changes were preserved.
