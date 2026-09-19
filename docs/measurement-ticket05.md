# Ticket 05 — all four measurement units

Authorized by Adam, including diagnosis, read-only adapter and CLI/plugin test
seams. Review baseline: `35f45fb7ba5e511a9cc73170e833b9fd021483e0`.

## Contract and scope

`UsageSource.usage(session_ids)` now returns validated `UsageRow` counters with
session id and task, rather than calls-only session totals. `diagnose()` accepts
only usage covering exactly the attributed session set, then sums all rows. The
Hermes adapter queries only those sessions, across profile `state.db` files; it
never consults the sessions rollup, backup databases or unlinked chat sessions.
The read-only checked DB/WAL copy mechanism from ticket 04 is unchanged.

New immutable observations use schema 2. Existing schema-1 observations still
load as calls-only records, without rewriting their bytes or inventing tokens.
No workflow-spec serialization decision is implied.

For a single run (and each task breakdown):

- **Calls/run:** sum of `session_model_usage.api_call_count`.
- **Context/call:** `(input_tokens + cache_read_tokens) / calls`.
- **Tokens/run:** separate fresh input, output, cache-read, cache-write and
  reasoning counters. These are not collapsed into an ambiguous billable total:
  provider output/reasoning and cache accounting can overlap.
- **Cache hit rate:** `cache_read_tokens / (input_tokens + cache_read_tokens)`,
  stored as a fraction and displayed as a percentage.

These context/cache formulas are exactly those in `measure_cost_baseline.py`;
cache-write, output and reasoning are not added to their denominators. Zero
calls yield null context/call; zero input-plus-cache yields null cache hit rate.
The terminal renders undefined rates as `n/a`. Missing columns, null counters,
negative/fractional/nonnumeric counters and missing usage fail explicitly rather
than masquerading as zero. Explicit zero counters remain valid observations.

`task` null/empty means **worker**; `background_review` means **review**; every
other nonempty task is **auxiliary**, retained by name (including future unknown
auxiliary tasks). Thus unknown overhead is not silently charged to the worker's
own loop. All categories remain included in run totals. The terminal and plugin
show the same four units for totals and every task, including reasoning tokens.

Scope is **attributed sessions only**, not total profile/account spend. The
baseline's later $4.41 all-profile Gemini observation includes unrelated traffic;
this ticket deliberately does not attribute it to the 23 worker runs or claim
billed-dollar accuracy. No new reviewer is invoked, Hermes config/authentication
is untouched, and ticket 04's activation constraint remains unchanged.

## Baseline reproduction

Sources read (not executed or modified):
`~/Documents/life-os/Business/Stillroom/agent-team/verification/2026-09-18-cost-baseline/`
contains `cost-baseline.md` and `measure_cost_baseline.py`.

`tests/fixtures/cost-baseline-2026-09-18.json` records only attribution and numeric
usage/task counters from the original 23 linked runs, via checked temporary
DB/WAL copies and the public adapters. No messages, prompts, credentials, dollar
estimates or whole databases are checked in. The newer September 19 research
run is excluded; blindly sweeping current boards now includes 24 linked runs.

Live read-only reproduction succeeded with:

```bash
.venv/bin/python -m docs.reproduce_ticket05 \
  --hermes-home /home/hermes/.hermes --store /tmp/workflow-ticket05-baseline-evidence
```

The helper pins the original attribution manifest and checks published counters;
it is evidence tooling, not ticket 06's role/baseline-management interface.

| Measurement | Reproduced |
|---|---:|
| Runs | 23 |
| Calls | 214 = 188 worker + 26 auxiliary + 0 review |
| Fresh input | 1,132,524 |
| Cache-read | 4,608,338 |
| Output | 89,103 |
| Cache-write | 0 |
| Reasoning (newly exposed, not in original table) | 19,237 |
| Calls/run | 9.3 |
| Context/call | 26,826 |
| Fresh input/run | 49,240 |
| Cache hit rate | 80% |

The offline baseline test recreates SQLite fixtures, calls the real public
adapters and diagnosis/store, and compares totals and all six published role
rows against independent literals from the baseline document. Role aggregation
in this test verifies the published evidence; product-level role breakdown and
baseline management remain ticket 06. A large unlinked interactive session is
included as a negative control.

## Verification

Red/green slices reproduced missing four-unit/schema output, missing task
breakdowns, missing terminal measurements, and inability to load historical
schema-1 artifacts, before implementation. Additional counter-validation,
multi-session, zero-denominator and baseline tests cover the completed contract.
The plugin smoke test also asserts the new output under the byte-preservation
boundary. Tests use offline fixtures, not live Hermes.

Targeted diagnosis and baseline tests: **45 passed**. Typechecking was run
repeatedly: **11 inherited errors in 3 files**, no new errors in diagnosis.
Final full suite, including the real Hermes loader in isolated fixture homes:
**131 passed, 2 optional live-Jev skips**. No live configuration was edited or
plugin activated. Reproduce from the repository root:

```bash
AGENT_LAB_JUDGMENT=stub \
HERMES_PLUGIN_TEST_SOURCE=/home/hermes/.hermes/hermes-agent \
HERMES_PLUGIN_TEST_PYTHON=/home/hermes/.hermes/hermes-agent/venv/bin/python \
  .venv/bin/python -m pytest -q
.venv/bin/python -m mypy agent_lab
```

Without the optional loader environment, that check also skips. Mypy still
reports exactly the inherited 11 errors in `encoding.py`, `judgment.py` and
`workflow.py`; this is not a green typechecking claim.

## Standards

Independent parallel review of `git diff 35f45fb...HEAD` at implementation
commit `3106982`: **no documented-standard breaches or actionable baseline
smells identified**. The reviewer made no edits and accessed no live Hermes state.

## Spec

Independent parallel review: **no spec findings**. Verified all four units,
worker/auxiliary/review separation, separate reasoning counters, exclusion of
unlinked sessions, and baseline formulas and published figures. No ticket-05
scope creep identified. The reviewer independently ran the 45 diagnosis/baseline
tests, all passing, without live Hermes access.

**Review summary:** Standards: 0 findings; Spec: 0 findings. Implementation is
complete; ticket acceptance/closure remains Adam's decision.
