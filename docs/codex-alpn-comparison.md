# Codex ALPN comparison — blocked, no production fix

## Scope and authorization

Resumed from HANDOFF.md at clean baseline `3224103e06a7963cccdc44a64b992ada1e3ed984`.
Adam prioritized unblocking/diagnosis, approved the explicit two-request synthetic
comparison, and subsequently permitted model calls as needed for this session.
That permission is session-scoped, not permission for future automatic retries.
No model or worker was spawned. The selected Generator/Guardian pair is unchanged.

## Fresh validation diagnosis

Command: `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q tests/test_designer_server.py -x --tb=short`.
Result: **1 failed in 0.16s**. `test_http_authors_design_and_checks_real_cases`
fails at server creation, through `validate_evidence_root`, with
`ValueError: Evidence directory must be outside Hermes and project source`.

The current mandatory TMPDIR is
`/home/hermes/.hermes/profiles/astra-pinned/cache/scratch`.
`agent_lab/designer/__init__.py:240–250` resolves the destination and rejects
anything beneath `Path.home() / '.hermes'`. This is a confirmed configuration/policy
conflict, not a provider failure. The guard is working as written. No HOME disguise,
symlink workaround, alternative temporary root or weakened guard was used.
A permitted validation runtime with scratch outside protected roots is required.

Command: `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q tests/test_designer_codex.py tests/test_designer_response_headers.py`.
Result: **329 passed in 2.53s**. Full regression was not repeated; it remains blocked.
The compound shell command exited 0 because its second command passed; that does
not turn the first test command green. Graft wiring freshness check passed.

## Actual live comparison

Exactly two sequential direct Codex requests; one connection each, no retry,
auth refresh, Guardian call, profile modification or private source capture.
The production read-only credential loader used `~/.hermes/auth.json` once.
Both requests used identical UTF-8 JSON:

```json
{"model":"gpt-5.6-sol","instructions":"This is a synthetic connectivity test. Do not use tools. Reply with only OK.","input":[{"role":"user","content":[{"type":"input_text","text":"Reply with only OK."}]}],"tools":[],"store":false,"stream":true}
```

Truthful identity remained `WorkflowGenerator/1` / `workflow-generator`.
Production `_https` bytecode was reused with an isolated globals mapping; only
SSL context ALPN configuration differed. Both contexts retained certificate and
hostname verification. A connection wrapper recorded negotiated ALPN without
retaining headers or bodies. Limits remained 180 seconds and 65,536 bytes.
Before dispatch, synthetic checks for each variant verified one POST, rejection
at the first missing-MIME section, no subsequent read and writer closure.

- **Default TLS:** negotiated ALPN null; HTTP **200**, rejected with
  `missing_http_content_type`; **0.607 seconds**.
- **Explicit ALPN:** negotiated **http/1.1**; HTTP **200**, rejected with
  `missing_http_content_type`; **0.651 seconds**.
- Both retained the same allowed observation: **2,647 section bytes, 35 field
  lines**, Content-Type/Content-Length/Content-Encoding absent,
  Transfer-Encoding present. No raw fields or body were inspected or persisted
  beyond production header parsing. This is equal shape, not proof of equal bytes.
- Generation success, reported model identity, token usage and billing are unknown.
  Neither response reached body parsing. Probe exit 0 means observations were
  recorded, not that generation passed.

**Conclusion:** advertising HTTP/1.1 ALPN did not fix or distinguish this failure
in the tested pair. The historical failure reproduces with a synthetic prompt,
so it is not confined to the previous private-draft payload. This does not prove
all payload independence or eliminate every TLS/client-fingerprint difference.
There is no evidence to justify a production ALPN patch or HTTPX replacement.
The response author and reason for missing Content-Type remain unknown.

## Artifacts

Private, one-shot diagnostic destination (not an application workflow evidence
store): `/home/hermes/.hermes/profiles/astra-pinned/cache/scratch/workflow-codex-alpn-comparison-01`.
Authorization/request and per-case reservations precede dispatch. Both result
files were independently read back after execution. Preserve the directory and
its guards; do not rerun the invocation.

Probe: `/home/hermes/.hermes/profiles/astra-pinned/cache/scratch/workflow-codex-alpn-probe.py`.
Command: `PYTHONPATH=. .venv/bin/python "$TMPDIR/workflow-codex-alpn-probe.py" --invoke`.
SHA-256:
- Probe: `1201d3087e07b630bb36d14da81f2d87ae2463168a34c2ec9f513a0735b181fc`.
- `default-result.json`: `97fe731684be6966970aa102294cf52882844913cf82ba8edce3d59a61f77030`.
- `http1-alpn-result.json`: `071b36de8fb3a3a79d5a785334ee4bf732461b80d48f65bfbecafb2046dd73bd`.

Scratch may be pruned; this report preserves the request and complete allowed
observations. No production/test code changed, no independent review was run,
and no commit or push occurred.

## Remaining unblock path

1. Run validation in a session whose authorized scratch root lies outside Hermes
   and project sources. This runtime cannot change its own live configuration.
2. Do not repeat the ALPN experiment or run another private draft for the same
   failure category. Current allowed observations do not identify the responder.
   Further live diagnosis needs a discriminating comparison or an explicitly
   agreed, privacy-bounded response-metadata observation contract; broader model
   call permission alone does not relax existing raw-header/body boundaries.
3. Keep ticket 19 Blocked and ticket 28 unimplemented. No runtime completion or
   successful Generator/Guardian pair is established by this investigation.
