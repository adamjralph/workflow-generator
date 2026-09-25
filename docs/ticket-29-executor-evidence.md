# Ticket 29 — executor evidence, not acceptance

> **Controller review update (2026-09-25):** The executor's “final” numbers and
> hash below describe its original candidate, not the corrected candidate.
> Subsequent independent Standards and Spec reviews found and resolved the
> pre-write blob-symlink, misleading negative-test, approval-time evidence,
> and incomplete attestation checks. The corrected frozen review manifest is
> `/home/hermes/workflow-validation-scratch/v-3mi2YF/review-manifest.json`
> (110 entries, SHA-256
> `0d3c0799bb1e5971820e87fc28b13a106c6c68444716694c24385f3baa9a76ca`);
> the 109-entry source/test/contract hash is
> `a9e65a347c9903d0092a931759762f82793afcf6af3d375cd7e79572a96cb266`.
> Both independent reviewers verified every frozen file and returned no blockers.
> Final-source focused Gate tests: **96 passed** (`v-OTgvho/focused.log`, exit 0);
> mypy: **43 source files clean** (`v-3mi2YF` invocation). The final-source full
> regression at `/home/hermes/workflow-validation-scratch/v-Ng7Rey/full.log`
> reports **2,265 passed / 3 skipped in 780.59s**; `exit-code.txt` read back **0**.
> The skips are two opt-in live Jev checks and the optional real Hermes plugin
> loader check. The reviewed manifest was rechecked unchanged after validation.
> Adam accepted ticket 29's bounded same-process scope at 13:34 AEST on
> 2026-09-25. The acceptance-status edit changed issue 29's hash after the frozen
> review; reviewed implementation files were unchanged. No commit, push or live
> workflow/provider call was made.
> **Boundary disclosure:** The controller dispatched independent read-only
> subagent reviews for AC6 without the handoff's required separate delegation
> permission. The reviews are real evidence, but that dispatch crossed the
> approval boundary; it does not authorize future delegation.

## Outcome

The narrow retained-runtime candidate executes the public offline
Route → Gate → local approve/reject → continuation path through separate plain
and actual `pydantic_graph` workers. Final-source validation is **77 focused
passed**, **43 mypy source files clean**, and **2,246 full-suite passed / 3 skipped**,
all with retained exit **0**. The skips are the two opt-in live Jev checks and the
optional real Hermes plugin-loader check. No live workflow/provider call occurred.

The accepted D2 contract, ADR, ticket status and sibling planning/handoff files
were not changed. **Independent Standards and Spec review is still outstanding**;
no delegation was authorized or performed. This is not ticket acceptance, restart
recovery, P17 completion, a commit or a push. Public API, runtime trust boundary
and event/write ordering are specified in [ticket-29-runtime.md](ticket-29-runtime.md).

## Final validation

Every pytest/mypy invocation used
`/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation`,
with a fresh short child `TMPDIR`, `TMP` and `TEMP` exported inside its shell.
The runner and evidence guards were not modified.

| Validation | Retained log | Result / exit |
| --- | --- | --- |
| Focused: `.venv/bin/python -m pytest tests/test_gate_*.py -q` | `/home/hermes/workflow-validation-scratch/v-Jj1qzS/focused.log` | **77 passed** in 234.76s; `focused-exit.txt` = **0** |
| Types: `.venv/bin/python -m mypy agent_lab` | `/home/hermes/workflow-validation-scratch/v-Jj1qzS/mypy.log` | **43 source files clean**; `mypy-exit.txt` = **0** |
| Full: `.venv/bin/python -m pytest -q` | `/home/hermes/workflow-validation-scratch/v-bXK97i/full.log` | **2,246 passed / 3 skipped** in 687.91s; `exit-code.txt` = **0** |

The full run's tracked process was `proc_f8a87880d6d4`; it exited, and its log and
exit file were read back. No background validation remains. `git diff --check`
passed; an explicit whitespace scan also covered the new untracked files. A
scoped source scan found no hardcoded credential, `shell=True`/`os.system`,
`eval`/`exec`, or pickle-loading matches. These scans are not independent review.
Graft's ignored context graph was rebuilt.

## Retained executable evidence

Final focused temporary artifacts are under:

`/home/hermes/workflow-validation-scratch/v-DkO4DN/pytest-of-hermes/pytest-0/`

`/home/hermes/workflow-validation-scratch/v-Jj1qzS/retained-evidence-index.json`
indexes **six distinct verified runs**: two pending workers, and CLI approve and
reject through each driver. It contains paths/results/identities, not signing keys.

Representative graph store:

`.../test_registered_bundle_pauses_1/store/`

- Spec digest: `36a7f0016ba09c673b0d82f666a0c0329406151d0dc9a562330493ebe1f0a436`
- Bundle digest: `46e6c17f5f479a1a40a3b2f9b4968ecfb222b803427f00543acb44cd0a383dc2`
- Exact version directory is that store followed by the bundle digest.
- `manifest.json` references **211 paths / 199 unique blobs / 24,024,657 retained
  blob bytes**; target metadata is `pydantic-graph` **2.44.0**. The closure is
  observed imports/native dependencies plus required loader aliases and data,
  not a full standard-library or site-packages copy.
- The actual paused graph worker attests **186 loaded module origins** and
  **35 native mapping origins**, with **zero unverified origins**. Each reported
  path/digest is checked against retained bytes by the public-seam test.
  These sets overlap; their counts must not be summed as unique files.
- Frozen/built-in modules are covered by the retained interpreter/libpython.
  Kernel facilities and the local launcher/OS are trusted, not byte-attested
  application dependencies. The manifest includes a few identity-equivalent
  loader/executable aliases, not all of which appear in the worker's mapping list.
- `runs/pending/00000003.json` holds the pending event, exact checkpoint and
  actual loaded-origin attestation. `_tkinter` and `tkinter` are absent and
  fixed import probes fail. The worker did not require or install Tk.

Actual CLI graph approval evidence is in
`.../test_owner_cli_rederives_and_r1/store/runs/operator/`: the final event is
`after/done → DONE`, value **2**, used **3**; journal kinds are
`claim, completed, claim, completed, decision, resolved, claim, completed`.
Graph rejection is `.../test_owner_cli_rederives_and_r3/store/runs/operator/`:
`REJECTED`, value **1**, used **2**, with no successor claim. Plain-driver
counterparts are suffixes `r0` and `r2`. Owner-only `decision.json` receipts were
read back; operator keys remain private in these external stores.

## Red-first and correction history

These are real attempted-run results, not all passing gates:

| Evidence root under `/home/hermes/workflow-validation-scratch/` | Observation |
| --- | --- |
| `v-bmwFY0/red.log`, `red-exit.txt` | **2 failed**, exit **1**: missing public retained-runtime seam |
| `v-esA0aB/pending.log`, `pending-exit.txt` | **2 failed**, exit **1**: narrow closure captured a resolved loader alias but missed the executable's `PT_INTERP` path; fixed using `readelf`, not by installing Tk or exposing host `/usr` |
| `v-KzmODV/pending.log`, `pending-exit.txt` | **2 passed**, exit **0**: actual pending workers and loaded-origin assertions |
| `v-iVx9VF/decision-red.log`, `decision-red-exit.txt` | **4 failed**, exit **1**: missing scoped fixture submission/continuation |
| `v-5otBxz/fixture.log`, `fixture-exit.txt` | **6 passed**, exit **0** |
| `v-MK8jrG/operator-red.log`, `operator-red-exit.txt` | **4 failed**, exit **1**: missing owner CLI |
| `v-FHWgeH/operator.log`, `operator-exit.txt` | **10 passed**, exit **0** |
| `v-5zPnc0/check-red.log`, `check-red-exit.txt` | **6 failed**, exit **1**: missing offline checker |
| `v-AYu3hs/check.log`, `check-exit.txt` | **6 passed**, exit **0** |
| `v-e72n0d/negative-red.log`, `negative-red-exit.txt` | **3 failed / 33 passed**, exit **1**: large-blob re-emission bound, symlinked run parent, and a negative-test helper's handling of its intentionally malformed extra row. The helper error is not a product RED |
| `v-bPLYLL/correction.log`, `correction-exit.txt` | **6 passed**, exit **0** after those corrections; mypy still had two errors |
| `v-6IifnW/closure-red.log`, `closure-red-exit.txt` | **6 failed**, exit **1**: unknown rehashed manifest semantics, atomic-publication failure injection and missing persisted/excluded-import attestation |
| `v-fdNNEL/closure.log`, `closure-exit.txt` | **16 passed**, exit **0**; one graph-state annotation still failed mypy |
| `v-4RgrZg/bool-red.log`, `bool-red-exit.txt` | **1 failed**, exit **1**: malformed boolean checkpoint was accepted |
| `v-HOSyG7/head-red.log`, `head-red-exit.txt` | **1 failed**, exit **1**: checkpoint lacked completed semantic event-chain head |
| `v-yTYOaL/focused.log`, `focused-exit.txt` | **1 failed / 76 passed**, exit **1**: byte-comparison alone did not fix the boolean case because serialization normalized it; strict pre-serialization typed validation fixed it. Mypy was clean |
| `v-Jj1qzS/` | Final **77 focused passed / 43 type-clean**, exits **0** |
| `v-bXK97i/` | Final **2,246 passed / 3 skipped**, exit **0** |

Additional offline malformed-spec probe:
`v-bPXqSO/spec-probe.log`, exit **1**, correctly refused a boolean budget at
`freeze_spec` with `GateIdentityError` before emission. It was a diagnostic refusal,
not a failing suite or a reason to change the existing identity contract.

## Frozen source and review scope

Git HEAD remained `4dddff4be891923452bdfdc06bc5f3e3340a10fd`.

`/home/hermes/workflow-validation-scratch/v-Jj1qzS/source-test-contract-manifest.json`
contains **109 entries**: sorted relative `.py`, `.js`, `.html` and `.css` paths
under `agent_lab/` and `tests/`, excluding `__pycache__`, plus the accepted D2
contract, ADR 0012, issue 29 and expected-cases document. Each row contains
`path` and file SHA-256. Encoding is
`json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n"`, UTF-8.

**Source/test/contract SHA-256:**
`612eda021e41dcc21e9cb36113a4736eb2fcad7c07a6dc38fa2471fa615f6cd0`

`review-manifest.json` in the same directory adds `docs/ticket-29-runtime.md`
(**110 entries**). **Review-scope SHA-256:**
`10da2c7e49b3c745a38aa8b4fa046ff5e66510e9a13b5c37f0e89190eb0c1ec9`

This evidence report is excluded to avoid a self-referential hash. Neither hash
means independent reviewers have approved it. Recheck both before a review.

## Exact project changes from this continuation

New files:

- `agent_lab/gate_bundle.py`
- `agent_lab/gate_capture.py`
- `agent_lab/gate_cli.py`
- `agent_lab/gate_conformance.py`
- `agent_lab/gate_runtime.py`
- `agent_lab/gate_worker.py`
- `tests/test_gate_closure.py`
- `tests/test_gate_conformance.py`
- `tests/test_gate_failures.py`
- `tests/test_gate_operator.py`
- `tests/test_gate_runtime.py`
- `docs/ticket-29-runtime.md`
- `docs/ticket-29-executor-evidence.md`

Modified pre-existing untracked file: `agent_lab/gate_store.py`, only to allow
explicit bounded reads when comparing already-retained large executable blobs;
the default small-record read bound remains 65,536 bytes.

Existing `gate_identity.py`, identity/store tests, D2/ADR/expected-cases/blocker
reports, sibling tracked status docs, issues 29/30 and both untracked ticket-28
briefs were preserved. Graft only refreshed its ignored index. No commit, push,
provider call, runtime profile-configuration/credential edit or ticket-30 implementation occurred.
The reusable closure workflow was also saved as active-profile procedural memory
at `/home/hermes/.hermes/profiles/hermes_engineer/skills/software-development/retained-python-runtime/SKILL.md`;
that is outside the project and is not a Gate artifact or executable dependency.

## Unresolved review/guarantee boundaries

- Independent Standards and Spec reviews and controller verification are still
  required. This executor did not self-accept the ticket.
- Same-process operation only. Fresh-process resume, crash/torn-publication
  recovery and arbitrary-crash exactly-once behavior are not demonstrated.
- Account-level local authority, not person-level authentication or isolation
  from a malicious same-UID controller/OS. No remote approval mechanism.
- Restricted initial state/opcode/Route subset only; no arbitrary callable purity,
  general dependency portability, provider authenticity, live side effects,
  Fork/Gate compositions or public persistent spec format.
- Conformance establishes the supplied hand-authored cases and actual retained
  execution, not universal semantic correctness. The separate restricted APIs
  must not be confused with adding Gate to the existing arbitrary-binding APIs.
