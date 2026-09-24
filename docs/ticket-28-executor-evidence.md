# Ticket 28 executor evidence

**Final controller validation (05:36 AEST):** Full suite `proc_aace941d89aa` exited **0**; controller read `/home/hermes/workflow-validation-scratch/v-Z4Ti6p/full.log`: **2,169 passed / 3 skipped in 465.55s**, and `exit-code.txt`: **0**. Short browser temp directory was `/home/hermes/workflow-validation-scratch/v-y58wEK`. The unchanged six-/nine-file review hashes below were rechecked after completion and scoped diff check passed. A subsequent status-only note changed the issue document's hash, not the code or accepted contract. Three skips are two opt-in live Jev checks and optional Hermes plugin-loader check. All technical gates are green for the corrected source and approved observed-case contract; no live workflow execution or callable-purity proof is claimed. Ticket acceptance remains Adam's decision; no commit/push.

**Independent confirmation update (05:34 AEST):** Fresh Standards and Spec reviews `deleg_d6fdeb57` each approved the corrected six-/nine-file hashes below without blocking findings. Standards independently ran 252 focused tests and mypy (35 files), exit 0 under `/home/hermes/workflow-validation-scratch/v-EvRNIZ/`; Spec verified the controller RED and green logs, not a fresh suite. Controller rechecked both hashes unchanged. Sessions declared `openai-codex/gpt-6-astra`, not wire-attested. Full regression `proc_aace941d89aa` is still pending; no ticket acceptance or commit/push.

## Controller continuation — 2026-09-25 05:29 AEST (full run pending)

Adam approved the narrow observed-case amendment and explicitly approved retrying
the read-only Standards prerequisite and both independent reviews. The original
corrected code/test manifest `0a77b0bc3a1f517bc79f38ed2079701130f5ac527db5cb4283935ac82282ddb7`
passed Standards with zero blockers, including 251 focused tests and mypy 35 files.
The Spec review returned **changes_requested**: a deterministic candidate join
result differing from the plain driver's could pass when a later Transform masked
it. Reviewer reproduced a one-case/two-case false pass with identical captured
inputs and different admitted join states, retained privately under
`/home/hermes/workflow-validation-scratch/v-r1Afoc/`; no raw private source was
used. Reviewers declared `openai-codex/gpt-6-astra`, not wire-attested. Standards'
optional wording fix clarified that IPv4/IPv6 network sockets are denied while
AF_UNIX remains for asyncio.

Controller added a public-seam masked-join regression, saw **1 failed / 86
deselected**, `assert not report.passed` at
`/home/hermes/workflow-validation-scratch/v-wX3zL3/red.log`, then added a per-case
strict comparison of the two drivers' captured reducer observations while retaining
each driver's repeated-input check. Final-source focused **252 passed** and mypy
**35 files clean**, exits 0, under `/home/hermes/workflow-validation-scratch/v-qvgX4M/`.
Current six-file hash `24816c99411acf7e7e3bf2f300161b85511a7a2c551c0d1dbfe04471a3f2856b`;
code/test/contract/ADR/issue nine-file hash
`a1b7d407e240e1ebcd5d1742a3be52bd8f54e2dbb72aa4647c586e169ba5b5e8`.
Scoped diff check passed. A new full suite is running as `proc_aace941d89aa` with
a fresh short browser TMPDIR; **not yet a pass**. Neither review approved this new
hash. Ticket remains blocked pending full-suite exit/read-back and independent
confirmation. No live call, commit, push or publication.

Status: implementation frozen for verification; focused tests, mypy, and full regression passed. Not independently reviewed or accepted. Hermes owns verification and the final answer. No commit, push, publication, delegation, live model call, credential/profile change, or P14+ implementation.

## Frozen scope

Baseline: `main`, HEAD `585927e2d13f72513f0854bf57cecb3c0254afdd`. Initial tracked worktree was clean; existing untracked `.scratch/workflow-generator/ticket28-executor-brief.md` was preserved.

Six implementation/test files, in manifest order:

| File | SHA-256 |
|---|---|
| agent_lab/spec.py | 1563ff2f7d3b45ccbb13575ec0d6eea2792d5b7f7a2c38aca8580734f6966101 |
| agent_lab/reference.py | 70afaa0893faa070b5668e1ff1876c8a140388e44e8152c5f157dbbe4d4b6e79 |
| agent_lab/generation.py | 639b09b9872f82183d1da749f3591f2facd9dd620690dcb0f1c360b0cfab768d |
| agent_lab/conformance.py | f728b09e723369955eb5e8756b7c36c30731340e581510818010c8a6bf7a0aac |
| tests/test_reference.py | ad03f821a1e00ab5bf2bccaadc8b5f9ef5fe04582344bfb017b395df543f2f5d |
| tests/test_parallel_wave.py | 830f857540bc53ae7ec3dbb7669e0eb9a44d8f3a55ed6f0a99f4368de61542ca |

Frozen manifest hash: `f4a75d9daf7bcfdcb5cbf462ae6dd03482a584f1ff55f6a10cab3283e8c712c0`.
Reproduce with `sha256sum agent_lab/spec.py agent_lab/reference.py agent_lab/generation.py agent_lab/conformance.py tests/test_reference.py tests/test_parallel_wave.py | sha256sum`. This document is not included in that implementation hash.

## Implementation

- `branch_regions` is shared by structural join validation, executable admission, static budget refusal, and canonical projection. Admission rejects unsupported, unreachable, overlapping, nested/sequential, shared-join, model-backed and alternate-entry shapes before user bindings. Reducers are keyed by join ID; the join operation label is exempt from ordinary binding resolution.
- Plain execution walks branches sequentially. Generated execution uses a real pydantic-graph mapped fork and private `reduce_list_append` collector. Each worker step uses `asyncio.to_thread` under the per-wave semaphore. The join receives indexed branch items and orders them before invoking the caller reducer once.
- Branch execution holders own detached state and repeat counters; accounting and the append log are shared. `RunAccounting` and `RunLog` were not edited. A branch holder records its own reservation. The join reserves its step on both success and failure; failed branches complete before declared-order selection, without merging their state.
- Dispatch records configured `wave_concurrency`; successful reducer invocation records declared branch indices. Wave conformance retains raw logs and their digests, compares canonical projection digests plus typed state/terminal/total spend, and excludes scheduling configuration from comparison. Non-wave byte comparisons remain in place.

## Real validation evidence

All pytest and mypy commands used `/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation` from the project directory. Each invocation created a fresh private evidence directory; none were removed or reused.

| Stage | Evidence directory | Result |
|---|---|---|
| Initial hand-authored two-branch oracle, both public drivers | `/home/hermes/workflow-validation-scratch/v-rIF0ki/` | `red.log`: 2 failed because `reducers` was not accepted; exit 1 |
| First focused invocation | `/home/hermes/workflow-validation-scratch/v-kpQoQW/` | pytest exit 4, zero tests: incorrect filename `tests/test_spec.py`; mypy exit 0. Not a test pass |
| Corrected early focused invocation | `/home/hermes/workflow-validation-scratch/v-qXYEos/` | 115 passed, 1 failed: legacy test expected `unsupported_edge` instead of missing-reducer rejection; exit 1 |
| Intermediate focused/type runs | `/home/hermes/workflow-validation-scratch/v-VEOvLm/`, `/home/hermes/workflow-validation-scratch/v-DtyQLh/` | pytest and mypy exit 0; superseded by final-source evidence below |
| Final-source focused/type run | `/home/hermes/workflow-validation-scratch/v-0gAfhN/` | `focused.log`: 246 passed in 1.64s; `mypy.log`: no issues in 35 source files; `exit-codes.txt`: pytest=0 mypy=0 |
| First full regression attempt | `/home/hermes/workflow-validation-scratch/v-5NVcut/` | Terminal tool timed out at 420s despite requested 600s; log incomplete around 79%, no exit-code file, no pytest process remained. **Not a pass** |
| Tracked unchanged-source full retry | `/home/hermes/workflow-validation-scratch/v-XIgzzS/` | Process `proc_90d9abbe3bff` exited 0; read-back `full.log`: **2,163 passed, 3 skipped in 465.67s**; `exit-code.txt`: **0** |

Focused command: `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest tests/test_parallel_wave.py tests/test_workflow_spec.py tests/test_reference.py tests/test_generation.py tests/test_conformance.py -q`.
Type command: `.venv/bin/python -m mypy agent_lab`.
Full command: `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q`.

For Chromium, each full-run child shell created an additional fresh mode-0700 short sibling directory and exported TMPDIR/TMP/TEMP there, leaving HOME/HERMES_HOME unchanged. First attempt: `/home/hermes/workflow-validation-scratch/v-a9Z0Nw`; tracked retry: `/home/hermes/workflow-validation-scratch/v-axFbSj`. The log directories contain `browser-tmp.txt` identifying these paths.

## Acceptance evidence index

All new tests are in `tests/test_parallel_wave.py` and use public compile/generate/run/check seams and actual logs.

| Requirement | Test |
|---|---|
| Independent two-branch state/reducer/spend oracle | `test_two_branch_hand_authored_state_reducer_and_spend` |
| Independent three-branch oracle and uneven lengths | `test_three_uneven_branches_expected_states_and_spend` |
| Barrier overlap, serial timeout, 1-16 range | `test_barrier_overlap_not_elapsed_time`, `test_invalid_concurrency_before_work` |
| Observed worker bound/default cap and sequential reference | `test_worker_bound_and_default_observed`, `test_reference_is_sequential_even_with_concurrency_parameter` |
| Adversarial completion, declared reducer order | `test_out_of_order_raw_evidence_and_declared_reducer` |
| Detached mutable state/reducer inputs | `test_mutable_state_detached_at_branch_and_reducer_boundaries` |
| Single/multiple failures, complete siblings, charged join | `test_branch_failure_completes_siblings_and_charges_join` |
| Invalid reducer type/state/outcome | `test_invalid_reducer_fails_closed` |
| Exact and one-short static budgets | `test_exact_and_short_budget` |
| Audit failure produces no successful result | `test_audit_failure_produces_no_result`, `test_failed_wave_conformance_retains_evidence` |
| All contract section 7 admissions and excluded node/wave shapes | `test_negative_admission_before_any_binding` |
| Authoritative reducer and join-label exemption in both directions | `test_join_binding_is_authoritative_and_stray_binding_ignored` plus initial oracle |
| Altered order/branch count/join and reducer output | `test_structural_wave_adversaries`, `test_altered_reducer_is_behavioral_mismatch` |
| Raw interleaving preserved, equal canonical evidence despite different scheduler limits | `test_canonical_projection_keeps_raw_adversarial_order` |
| Refused/failed waves compared, incomplete audit rejected | `test_failed_wave_conformance_retains_evidence` |
| Offline path with network sockets denied | `test_conformance_without_network_sockets` |

The socket test denies AF_INET and AF_INET6 socket creation and first proves the denial by attempting it. AF_UNIX remains available for asyncio's local wakeup socketpair. This is an offline-path test, not a claim that trusted caller Python is sandboxed. Barrier and worker-bound tests retain `overlap-observations.json` and `bound-observations.json` beside synthetic run logs in pytest evidence directories; elapsed time is never a pass/fail criterion.

## Remaining gates / handoff

- Full-regression log and exit code were read back after process completion. The three skips are the two opt-in live Jev checks and the optional real Hermes plugin loader check. The frozen six-file manifest hash was rechecked unchanged after the full run. No background validation remains running.
- Hermes coordinates independent Standards and Spec review of the frozen implementation hash. Neither review was launched by this executor; no acceptance boxes were checked and no ticket closure is claimed.
- Scoped tracked diff and new test code were inspected; `git diff --check` passed. No private source/response or credential content was added. Graft was refreshed with `graft build` (ignored local graph cache).
- No separate lint command is specified in the project's dependency manifest/README; mypy and pytest are the exercised project checks. Configured route/fallback was not independently wire-attested; no degradation/fallback notification was observed during execution.

## Focused Spec correction — supersedes the frozen-source status above

The preceding executor evidence is historical and preserved verbatim. This correction
does not claim ticket acceptance. The initial six-file manifest was verified as
`f4a75d9daf7bcfdcb5cbf462ae6dd03482a584f1ff55f6a10cab3283e8c712c0` before edits.

### Review findings and bounded correction

1. **High: synchronized stateful reducers passed conformance.** Two independently
   instantiated counters returned `(1,)`, then `(2,)` for identical reducer inputs,
   and both case pairs passed. The new public-seam regression reproduced precisely
   that false pass before implementation changes. Both drivers now return detached
   reducer observations: Python-mode fork-entry/declared-order branch inputs captured
   before caller mutation, and the admitted join state, selected outcome, target and
   failure captured before downstream work. Conformance retains separate per-driver
   histories and emits `behavioral_mismatch` at
   `cases/<case>/reducers/<join>/<driver>` when identical observed inputs have
   divergent admitted outputs. It does not replay a reducer, reset a counter,
   deepcopy a callable, or replace the supplied GraphCandidate's owned mapping.
   Actual raw logs and canonical comparisons remain unchanged.
2. **Medium: unused reducers changed no-Fork admission.** `_wave_findings` now
   returns before reducer-key validation when there is no Fork. Public reference
   and generated-driver regressions prove extraneous callable/noncallable entries
   are unused, outputs and raw log bytes match omission, and existing unbound
   findings are unchanged. Existing wave `extra_reducer` rejection tests still pass.

The reducer regression also covers different initial states converging to identical
reducer inputs and a downstream transform masking divergent join states. Both
drivers still produce the actual divergent counter values; it is the report that
fails closed, not a fabricated reset that makes the defect disappear. A deterministic
reducer passes repeated identical inputs and legitimately different inputs. Existing
detached-input, failure, audit, canonical projection and offline tests remain green.

### Actual correction validation

Every validation used the approved external runner; each invocation received a fresh
owner-only directory. No full regression was launched, avoiding any overlap with a
controller run on the old hash. No claim is made about the controller's process state.

| Stage | Evidence directory | Actual result |
|---|---|---|
| Red public-seam regressions, before implementation fixes | `/home/hermes/workflow-validation-scratch/v-TgbN92/` | `red.log`: 3 failed, 81 deselected in 0.24s; counter false pass and both no-Fork drivers reproduced; exit 1 |
| Intermediate focused/type checks | `/home/hermes/workflow-validation-scratch/v-x9pjQe/` | `focused.log`: 251 passed in 1.70s; mypy exit 1, missing `findings` list annotation after early return; corrected, not hidden |
| Final-source focused/type checks | `/home/hermes/workflow-validation-scratch/v-x2cQvE/` | `focused.log`: 251 passed in 1.67s; `mypy.log`: success, 35 source files; `exit-codes.txt`: pytest=0 mypy=0 |

Commands inside the runner:

- Red: `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest tests/test_parallel_wave.py -k "identical_reducer_inputs or linear_extraneous" -q`
- Focused: `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest tests/test_parallel_wave.py tests/test_workflow_spec.py tests/test_reference.py tests/test_generation.py tests/test_conformance.py -q`
- Types: `.venv/bin/python -m mypy agent_lab`

Final logs, exit codes and manifest were read back. `git diff --check` passed.
Only `agent_lab/reference.py`, `agent_lab/conformance.py`,
`tests/test_parallel_wave.py`, and this evidence document were edited in this
correction. The sibling implementation in `spec.py`, `generation.py` and
`tests/test_reference.py` retains its initial hash; private briefs and files were
not edited. No commit, push, live call, agent, independent review or profile edit.
No route-degradation notification was observed; runtime identity was not independently
wire-attested and no alternative model was invoked by this executor.

### Correction freeze

Same six-file manifest order and hash command as the historical freeze:

| File | SHA-256 |
|---|---|
| agent_lab/spec.py | 1563ff2f7d3b45ccbb13575ec0d6eea2792d5b7f7a2c38aca8580734f6966101 |
| agent_lab/reference.py | c7d16bd8fa7d1b3cf31f3234e0e216b40addaa46d218b2585ccd275fed76a07e |
| agent_lab/generation.py | 639b09b9872f82183d1da749f3591f2facd9dd620690dcb0f1c360b0cfab768d |
| agent_lab/conformance.py | b195fc4c85b0fb195480caff5e76aea70f88f020021f0e0780f4f225dc717d61 |
| tests/test_reference.py | ad03f821a1e00ab5bf2bccaadc8b5f9ef5fe04582344bfb017b395df543f2f5d |
| tests/test_parallel_wave.py | 715a766e71a24d365ca92bfa06a74f4d77453a5b1518aba2c1243f1efa834e9e |

Correction manifest hash:
`0a77b0bc3a1f517bc79f38ed2079701130f5ac527db5cb4283935ac82282ddb7`.
The exact manifest is retained as `manifest.sha256` in the final validation directory.
This evidence document remains outside the implementation manifest to avoid a
self-referential hash.

### Unresolved contract limit / required controller decisions

**Blocked for ticket acceptance, not for the requested minimum correction.**
Contract §3's broader fresh-mapping-per-driver/per-case and statelessness guarantee
is not fully implemented. Compile/generate still own shallow mapping copies;
conformance reuses those mappings and their supplied callable objects across cases.
The mapping API provides no factory/reset protocol, and GraphCandidate owns its
mapping. Copying a dictionary cannot isolate closures, globals, bound instances or
hidden external state; deepcopy of arbitrary Python callables is not a solution.

The new check establishes only observed identical-input consistency within the
supplied cases, separately for each driver. A single call, distinct inputs, or hidden
state that does not affect observed outputs cannot establish purity. Observations
compare Python-mode state dumps and normalized admitted join results; distinct invalid
raw return objects/exceptions collapsing to the same validation failure are not
distinguished. These observations are in-memory run-result evidence, not new durable
state payloads in raw logs. The reproduced valid counter divergence cannot pass.

Hermes/Adam must resolve whether this explicitly bounded guarantee is acceptable or
authorize a public factory/isolation contract. No acceptance criterion was waived or
checked off by this executor. A **final-source full regression on the correction
hash is still required**; the historical full pass and any controller run of the old
hash do not validate these edits. Hermes coordinates confirmation and independent
review; this executor launched neither.

### Controller verification and decision boundary — 2026-09-25 05:12 AEST

Hermes read back the corrected six-file manifest hash
`0a77b0bc3a1f517bc79f38ed2079701130f5ac527db5cb4283935ac82282ddb7`.
The independently launched **final-source** full suite at
`/home/hermes/workflow-validation-scratch/v-rKzn37/full.log` reports
**2,168 passed / 3 skipped in 479.06s**; `exit-code.txt` reads **0**.
The short browser TMPDIR was `/home/hermes/workflow-validation-scratch/v-jKOhyd`.
`git diff --check` passed; no commit or push. The earlier controller full run
`/home/hermes/workflow-validation-scratch/v-j0keaK/` was killed when the source
changed and is **not** counted as a pass.

The first independent Spec review returned changes requested for the two findings
above. The first Standards reviewer did not inspect source after a read-only
Graft/hash command hit an approval denial; that is **not** an approval or a code
finding. The corrected hash has not received independent confirmation on either
axis. Adam was asked to decide between an honest observed-case §3 amendment,
a wider reducer-factory contract, or leaving ticket 28 blocked, and separately
whether to retry the Standards review. The clarification timed out with no
answer; **no option is approved by silence**. Ticket 28 remains unaccepted.
