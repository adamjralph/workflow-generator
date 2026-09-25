# Ticket 29 — executable-closure attempt stopped, not delivered

## Outcome

Ticket 29 remains incomplete. No Gate runtime implementation from this attempt is retained in project source. The controller's existing `gate_identity.py`, `gate_store.py` and their tests are unchanged; they still describe and test **identity inputs only**, not an executable bundle. No ticket status or accepted D2 wording was changed.

The first public-seam tracer asserted the hand-authored pending state for both `reference` and `graph`: value 1, used 2, remaining 1, `before/done` followed by `review/pending`, a typed checkpoint and verified retained-runtime evidence. It first failed because the public runtime seam was missing. A trial retained-runtime implementation then failed **before either workflow driver ran**, in native dependency capture:

```
GateIdentityError: Native dependency closure cannot be resolved:
/usr/lib/python3.14/lib-dynload/_tkinter.cpython-314-x86_64-linux-gnu.so
```

The trial collected the CPython executable, standard-library source/extensions, the installed `pydantic-graph` dependency tree and native library bytes, and proposed copying hash-verified bytes into a private read-only bubblewrap filesystem. Its broad standard-library capture encountered the above unresolved native closure. The exception did not preserve the underlying `ldd` stdout/stderr, so **the exact unresolved native library or other cause is not established**. Tk is not demonstrated to be required by this narrow workflow; this result does **not** prove the accepted narrow design impossible, and does not justify adding a Tk installation prerequisite to D2.

A follow-up read-only diagnostic to enumerate unresolved standard-library native dependencies returned **pending tool approval** (`tirith:interpreter_suspicious_inline_exec`). It was not rerun, rewritten into another execution route, or bypassed. The attempt stopped there rather than silently omit a dependency or label the unverified runtime exact. A controller continuation needs that diagnostic approval resolved first, then an explicit supported runtime/extension closure with negative tests proving excluded imports cannot execute. Bubblewrap namespace availability alone is not executable attestation.

## Retained evidence (outside Git)

All pytest/mypy commands below used `/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation`, with a fresh short child `TMPDIR`, `TMP`, and `TEMP` exported inside the runner.

| Evidence | Result |
| --- | --- |
| `/home/hermes/workflow-validation-scratch/v-0VQxSN/red.log` | Initial collection error, exit 2; **not** the valid RED assertion |
| `/home/hermes/workflow-validation-scratch/v-NRpS4G/red.log`, `red-exit.txt` | Valid missing-public-seam RED: **2 failed**, exit **1** |
| `/home/hermes/workflow-validation-scratch/v-AhUrJ0/namespace.log`, `namespace-exit.txt` | Minimal bubblewrap user/PID/network namespace probe, exit **0**; no closure or workflow claim |
| `/home/hermes/workflow-validation-scratch/v-Vcglct/focused.log`, `focused-exit.txt` | Trial public-seam tests: **2 failed**, exit **1**, native closure refused before worker launch |
| `/home/hermes/workflow-validation-scratch/v-Vcglct/mypy.log`, `mypy-exit.txt` | Trial source: **4 errors in 3 files**, exit **1**; not type-clean |
| `/home/hermes/workflow-validation-scratch/v-t75RKJ/baseline-focused.log`, `baseline-focused-exit.txt` | After archiving trial files, original identity/store tests: **11 passed**, exit **0** |
| `/home/hermes/workflow-validation-scratch/v-t75RKJ/baseline-mypy.log`, `baseline-mypy-exit.txt` | Original identity/store source: **2 files clean**, exit **0** |

No full-suite run was started after the explicit closure stop. The green baseline checks do **not** establish Gate pause, operator approval, rejection, continuation, conformance, audit ordering, mutation resistance, or transactional guarantees. No independent review was delegated.

## Trial archive and source baseline

The four files created during the attempt were moved, not discarded, to:

`/home/hermes/workflow-validation-scratch/v-Vcglct/prototype/`

- `agent_lab/gate_bundle.py`
- `agent_lab/gate_runtime.py`
- `agent_lab/gate_worker.py`
- `tests/test_gate_runtime.py`

`prototype/manifest.json` holds their individual SHA-256 hashes. These files are **failed experimental work, not a candidate implementation**. In addition to the closure refusal and mypy errors, CLI decisions/continuation/conformance and transactional failure evidence were not implemented. Do not install this archive or treat its proposed attestation and journaling as verified guarantees.

After archiving, the source/test/contract manifest is:

`/home/hermes/workflow-validation-scratch/v-Vcglct/source-test-contract-manifest.json`

SHA-256: `e8f69e0e4c1f94ba8256a53a00e3030db8bde90d3546a563c656cb747ccf360b`

Its **98 entries** are sorted relative paths and file SHA-256 values: `.py`, `.js`, `.html`, and `.css` files under `agent_lab/` and `tests/` (excluding `__pycache__`), plus D2 contract, ADR 0012, issue 29, and `docs/ticket-29-expected-cases.md`. Encoding is `json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n"`, UTF-8. This report is excluded to avoid a self-referential digest. The manifest identifies the surviving baseline, **not a completed ticket-29 implementation**.

A final combined `git status` / `git diff --check` / manifest recheck also returned **pending tool approval** (`tirith:analysis_incomplete`) and did not execute. No final diff-check success or post-report hash recheck is claimed. The manifest above was successfully computed before this report was written; the last successful `git status` was immediately after the prototype archive.

Only this report remains as a project-file addition from this attempt. Existing sibling docs, briefs, identity sources/tests and ticket statuses were preserved. Graft navigation refreshed its ignored index automatically. No live provider/tool workflow call, Hermes profile/credential change, independent delegation, ticket-30 work, commit or push occurred.
