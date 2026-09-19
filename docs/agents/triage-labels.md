# Triage Labels

The engineering skills use five canonical triage roles. For this local Markdown tracker, the role string is written on a `Status:` line near the top of each issue.

| Canonical role | Tracker status | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Captured but not yet evaluated for scope, value, safety, duplication, or ownership. |
| `needs-info` | `needs-info` | Cannot be specified or progressed until required human information or authority is supplied. |
| `ready-for-agent` | `ready-for-agent` | Fully specified, adequately bounded, unblocked, and suitable for an autonomous agent. |
| `ready-for-human` | `ready-for-human` | Requires a human action, decision, credential, physical step, relationship action, or judgement that should not be delegated. |
| `wontfix` | `wontfix` | Deliberately declined, obsolete, duplicated, unsafe, or outside current scope. |

Use only one active triage role per issue.

## How to use the roles

1. Create an unassessed issue with `Status: needs-triage`.
2. Review its problem, evidence, desired outcome, scope, dependencies, authority, and risks.
3. Change it to `needs-info` when a specific missing answer prevents progress. State the missing information plainly.
4. Change it to `ready-for-agent` only when another agent can act without inventing requirements or exceeding authority.
5. Change it to `ready-for-human` when the next action inherently belongs to Adam or another named human.
6. Change it to `wontfix` when declining it, and record the reason so it is not repeatedly rediscovered.

These roles describe triage readiness, not implementation progress. A ticket claimed through a wayfinding workflow may additionally use that workflow's `claimed` and `resolved` states as defined in the issue-tracker guide.

## Examples

- A raw idea with no selected outcome: `needs-triage`.
- A client workflow proposal awaiting permission to inspect real records: `needs-info`.
- A complete specification with acceptance tests and no unresolved decisions: `ready-for-agent`.
- A task to call a prospect or approve access to client data: `ready-for-human`.
- A duplicate proposal or an unsafe autonomous decision workflow: `wontfix`.

## Changing the vocabulary

Edit the tracker-status column if the project later adopts different labels. Re-run the setup skill only when switching trackers or rebuilding the configuration from scratch.
