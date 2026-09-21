# Ticket 19 — read-only provider feasibility

Static inspection only. No network/model calls, credential-content reads, Hermes
imports/execution, or protected writes. Two independent research agents inspected
the installed integrations and SDK source. This establishes local implementation
behavior, not successful authentication, model access or live endpoint semantics.

## Summary

The configured role models can plausibly be used through dedicated tool-free
adapters, but the proposed contract cannot currently be claimed implementable
unchanged. In particular, the **4,096-token hard output ceiling was proposed by
the coding agent, not required by Adam**, and conflicts with the installed Codex
integration. Adam agreed a two-model-call ceiling, which is a different constraint.

| Requirement | Generator: OpenAI Codex | Guardian: Vertex |
|---|---|---|
| Configured default | `gpt-5.6-sol` | `google/gemini-3.1-pro-preview` |
| Single tool-free request | Supported by local request shape | Supported by local request shape |
| No generation retries/fallback | Dedicated client with retries zero | Dedicated client with retries zero |
| Proposed hard 4,096 output-token cap | Installed integration documents endpoint rejection | Exact endpoint/model semantics not established |
| Read-only credential path | New strict token reader needed; existing resolver can write | Explicit credential mechanism needed; normal ADC path refreshes/discovers |
| 180-second absolute deadline | Requires an outer deadline, not just SDK timeout | Same |
| Live auth/model availability | Not tested | Not tested |

No existing Hermes agent/session or auxiliary helper should be invoked unchanged.
They can introduce retries, fallback, credential maintenance or altered token limits.

## Generator findings

Let `H = /home/hermes/.hermes/hermes-agent`.

- Codex uses the ChatGPT backend Responses endpoint, streaming, not generic public
  OpenAI Chat Completions: `H/agent/codex_headers.py:16`,
  `H/agent/auxiliary_client.py:1470–1481`.
- `H/agent/auxiliary_client.py:1383` explicitly documents rejection of
  `max_output_tokens` with HTTP 400. `H/agent/transports/codex.py:643–654`
  omits the cap for Codex. Generic Responses SDK support is not endpoint support.
- Empty tools omit tool configuration: `H/agent/transports/codex.py:601–605`.
- Existing token reading may acquire a writable lock:
  `H/hermes_cli/auth_codex.py:75–100`, `H/hermes_cli/auth.py:608`.
  Malformed-store recovery can write a backup: `H/hermes_cli/auth.py:665–680`.
  Runtime resolution may recover/import credentials, probe quota and update state:
  `H/hermes_cli/auth_codex.py:428–453`.
- Disabling refresh is not a strict expired-token rejection policy:
  `H/hermes_cli/auth_codex.py:465–480`. A dedicated approved reader must reject
  missing/malformed/expired credentials and never refresh, lock, probe or save.
- Configured model identity is preserved; the special suffix handling does not
  establish a different alias for this slug: `H/agent/model_metadata.py:1573–1577`.

A prompt length instruction, stream cutoff, byte bound or reasoning-effort setting
is **not** a provider-enforced output-token/spend cap. A timeout cannot prove that
remote generation stopped or that no further usage was charged.

## Guardian findings

- Vertex resolves to OpenAI-compatible chat completions with OAuth2:
  `H/hermes_cli/runtime_provider.py:763–774`.
- Credential options include service-account paths and ADC:
  `H/agent/vertex_adapter.py:66–75,100–118`. The conventional ADC file exists;
  its content/type, identity and usability were not inspected.
- The existing adapter may install dependencies at import (`:18–23`), refresh
  tokens (`:121–153`) or try alternative credential sources (`:155–164`).
  These helpers do not establish the required isolated read-only mechanism.
- In-memory OAuth access-token acquisition is distinct from writing credential
  files, but it is network activity and must be explicitly scoped. Current proposed
  contract fails on expired credentials rather than authorizing refresh. Auth
  retries must be disabled separately from generation retries if such acquisition
  is later approved. Never count an auth exchange as a generation call, or conceal
  its existence when claiming no network activity.
- Existing Gemini-aware helpers may increase an explicit output limit to 65,535:
  `H/agent/transports/chat_completions.py:188–195,262–271`,
  `H/agent/gemini_native_adapter.py:40,383–393`. Do not reuse those builders.
  Exact reasoning/output limits for the selected endpoint remain unverified.

## SDK constraints common to both

The inspected OpenAI SDK has default retries of two; explicit `max_retries=0`
disables them (`openai/_constants.py:9–10`, `_base_client.py:395–399`).
Transport timeout parameters are per operation/read, not a total wall-clock
limit; use an enclosing absolute deadline. Codex streaming and Vertex nonstreaming
responses both need bounded collection and uncertain-completion handling.

Local SDK types expose token usage and optional cache/reasoning fields, but that
does not establish what these providers actually return. Preserve unknown usage
and do not double-count reasoning included in provider completion totals.

Research inspected the installed `H/.venv` and `H/venv` SDK trees; a future adapter
must pin/test its own project dependencies, not assume those environments match.

## Approved follow-up

Adam explicitly approved the recommended provider adjustments: retain both profile
defaults and the two-generation-call cap with no retries; bound local response size
and elapsed time without promising remote cancellation or capped spend; permit
Vertex token acquisition in memory only, with no credential-file or Hermes-state
writes. The execution contract has been updated. This is not permission for live
smoke calls or a claim that authentication/model access has been verified.

## Original recommendation (resolved by the approval above)

**Recommended for discussion:** retain Adam's selected profile defaults and hard
**two-generation-call limit**. Revise the additional proposed output-token promise
to accurately reflect each provider: bounded prompts, response collection and
wall-clock duration locally; provider-enforced output caps only where verified.
Explicitly state that those local limits do not guarantee a token or monetary cap
or remote cancellation. This revision was subsequently approved as recorded above.

Alternative: retain the proposed hard token ceiling and ask Adam to select a
Generator provider/model that supports it. Do not substitute one automatically.

Pin the precise credential-source configuration per provider. A read-only existing
Codex access token may suffice until expiry; Vertex in-memory token acquisition
is now approved. No permission to save/refresh protected credential
files, run Hermes sessions or initiate live generation follows from this research.

Ticket 19 remains `needs-info`. Offline fixture/replay feasibility is distinct
from proving that the selected live providers meet the final approved contract.
