# Provider triage: one DeepSeek route observation

Date: 2026-09-22. Baseline: `f5f620fec7c0bace8183611f48d10ae1be612244`.

## Authorization and bounds

Adam asked to test another non-Gemini profile (suggesting research/DeepSeek) and authorized triage and closure of finished work. Read-only discovery found research currently uses Codex; content-scout uses DeepSeek. The selected alternative was disclosed before execution.

This observation used the content-scout **configured model route**, not the research profile, not scout role instructions, and not a spawned Hermes session. A tools-disabled synthetic `OK` request contained no user draft, source content, SOUL, private guidance or history. It cannot establish editorial quality or completed-workflow conformance.

The probe allowed one local generation POST with a one-shot destination/guard, no redirect following, retries or fallback, a 60-second local alarm, 65,536-byte response collection limit and `max_tokens: 128`. Local timeout does not promise remote cancellation or a spend ceiling. Ollama/cloud internals and retry behavior were not audited. Profile configuration was read only and verified byte-identical after execution. No Gemini/Vertex auth or generation was requested.

## Actual execution

Preflight `GET /v1/models`: the exact configured model was listed; zero generation requests.

Generation: `POST http://127.0.0.1:11434/v1/chat/completions`.

Exact credential-free request:

```json
{"model":"deepseek-v4.1-flash:cloud","messages":[{"role":"system","content":"This is a synthetic connectivity test. Do not use tools. Reply with only OK."},{"role":"user","content":"Reply with only OK."}],"stream":false,"tools":[],"max_tokens":128}
```

Observed result, read back from the saved receipt:

- HTTP status: **200**.
- Exact content check: **OK**, true.
- Elapsed: **0.613 seconds**.
- Requested model: **`deepseek-v4.1-flash:cloud`**.
- Reported model: **`deepseek-v4.1-flash`**.
- Finish reason: **`stop`**.
- Provider-reported usage: prompt **52**, completion **33**, total **85**, cached prompt **0**. Reasoning detail and billed cost were not supplied in the retained usage object; do not infer zero.
- Local generation dispatches: **1**; backend retry behavior unknown.
- Profile unchanged: **true**.
- Strict probe status: **`unexpected_result`**, process **exit 1**. The response passed connectivity/content checks but failed exact requested/reported model equality. No identifier was silently rewritten, no second call was made, and the gate was not weakened retrospectively.

This makes the route a viable **connectivity candidate**, not a fully verified replacement adapter. A production integration must explicitly settle and test requested/reported identity handling. The `:cloud` difference may be routing/tag behavior; this probe alone does not prove that explanation or backend model identity.

## Artifacts and reproducibility

- Probe: `/home/hermes/.hermes/profiles/astra-pinned/cache/scratch/workflow-deepseek-probe.py`.
- Probe SHA-256: `701aed04afe9c139c18e7a2139d01388acecae2a34ffe2308a744e3d02de7627`.
- Receipt: `/home/hermes/.hermes/profiles/astra-pinned/cache/scratch/workflow-deepseek-probe-20260922/result.json`.
- Receipt SHA-256: `72ade24d15acc3db9eab4512f3eae3f50c8c13f423235826c1ddba6cf65d0e80`.
- Commands: `.venv/bin/python <probe-path>` for read-only endpoint listing, then `.venv/bin/python <probe-path> --invoke` for the single consumed generation observation.
- Config inspected: `/home/hermes/.hermes/profiles/stillroom-content-scout/config.yaml`. The credential value was neither printed nor persisted in the receipt/report.

Scratch artifacts are temporary; this report preserves the exact request, outcome, limits and hashes. Do not rerun the generation command, remove its guard or treat this authorization as an unlimited provider test allowance.

## What this establishes and what it does not

The non-Gemini route responded now. It does **not** demonstrate that Gemini rate limiting caused prior failures. Private `live-smoke-05/SMOKE.md:11–23,29–49` explicitly records a Generator-only Codex request, `missing_http_content_type` with HTTP 200, and no Guardian invocation. Prior full-suite failures were offline evidence-directory guard failures, not rate limits.

Changing only Guardian leaves the observed failing Codex Generator path in place. The current application server constructs Codex and Vertex sources; there is no production Ollama/custom adapter connected by this probe. Do not label this a successful draft, Guardian review, completed pair or ticket-19 closure.

## Adam's decision and Codex continuation

Adam selected **“Keep the existing model pair and investigate the Codex Generator failure.”** This supersedes the earlier DeepSeek-Generator suggestion. Preserve both configured models and role instructions; no alternate adapter is being built.

The continuation inspected the actual default Codex path and the installed Hermes identity helper, without importing/running Hermes or reading real Codex credentials:

- `agent_lab/designer/codex.py:140–149`: direct verified TLS/SNI to `chatgpt.com:443`, POST `/backend-api/codex/responses`. This agrees with the official endpoint family in installed `agent/codex_headers.py:16–28`; no endpoint typo was found.
- `codex.py:451–491`: the request requires model/instructions/input, empty tools, `store=false`, `stream=true`; forwards the exact canonical request and sends truthful `WorkflowGenerator/1` / `workflow-generator` identity. No request is routed to Vertex here.
- `codex.py:151–187`: media-type validation occurs on the first complete header section before body collection; a missing Content-Type is not a Guardian error or evidence of a successful generation. Existing investigations already checked field preservation and request framing; no new field-loss defect was found.
- Installed Hermes source at `524041b9d0437cd4424a524af4b9e26145e69ab0` includes an optional `x-openai-internal-codex-residency` header derived from JWT claims (`agent/codex_headers.py:51–75`), absent from this adapter. Its documented missing-header symptom is HTTP 401 for residency-enforced workspaces, not the observed 200. No real claims were read. This is a compatibility difference, **not a diagnosed cause** or reason to patch speculatively.
- ALPN/client identity/connection handling remain known implementation differences from the previous transport study. That study already established that a plain HTTPX replacement changes the approved byte-level evidence/acceptance policy. Do not repeat it or impersonate Hermes.

Fresh targeted execution:

```sh
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q \
  tests/test_designer_codex.py tests/test_designer_response_headers.py
```

**329 passed in 2.25 seconds**, exit 0. Actual log:
`/home/hermes/.hermes/profiles/astra-pinned/cache/scratch/workflow-codex-triage-tests.log`.
These tests use injected/synthetic transport and credential boundaries; they exercise
request validation, framing, usage, timeouts and secret-safe response handling.
They reproduce approved offline behavior, not the unknown live upstream response,
and do not replace the full regression currently blocked by evidence-root policy.

### Remaining blocker and smallest useful next experiment

**Root cause remains unresolved.** The retained live evidence cannot establish who
produced the HTTP 200, why Content-Type was absent, or whether an equivalent request
through a different TLS configuration would work. There is no demonstrated code
remedy to implement responsibly yet. No further paid Codex request was made.

If Adam authorizes a new live experiment, use a synthetic Generator-only request,
same model/credentials/truthful client identity, preserved header rejection and
response bounds, new private destination and explicit stop conditions. A bounded
comparison of default TLS against explicit `http/1.1` ALPN could isolate one known
transport difference; this is a **proposed discriminating experiment, not a ranked
root-cause claim or approved fix**. Both cases failing would leave the hypothesis
unsupported; a difference would justify repeatability investigation, not automatic
production adoption. Requests, possible spend, destination and any transport override
must be approved before running. Do not spend another private draft merely to obtain
the same failure code, and do not expand diagnostics without an evidence question.

No profile/routes/SOUL/tools were edited, no Hermes agent was launched, no source metadata or previous smoke store changed, and no commit or push occurred.
