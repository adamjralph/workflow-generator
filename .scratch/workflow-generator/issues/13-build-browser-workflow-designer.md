# 13: Build a browser-based workflow designer

**Type:** task
**What to build:** A user answers static multiple-choice questions in a local browser UI, inspects the resulting workflow graph, generates an executable workflow and sees its offline conformance results. Changing answers updates the design and permits a new generation/check without writing Python.

**Blocked by:** None (can start immediately). Tickets 01–12 are accepted and closed; parallel and Gate work do not block this slice.

**Status:** ready-for-agent

**Scope approval:** Adam selected the visual designer as the first product checkpoint, selected browser UI, and approved this ticket's scope with “yes”. Adam subsequently approved the concrete threshold-routing demo and review baseline with “Approve”.

**Review baseline:** Approved `2047f1afe177ab60a993b68a56762689aa35fb0e` (repository HEAD when published). Unrelated working-tree edits are not part of this implementation.

## Approved scope

- Local browser app, static multiple-choice questionnaire and visual graph.
- Transform/Decision nodes and Route edges only, using a small catalog of safe prebound operations. No arbitrary Python supplied through the browser.
- Questionnaire answers author the existing typed in-memory spec. Display and execution use that same design through the shared generation/conformance core.
- Generate an executable graph and perform real offline conformance checks; display the result rather than a fabricated success or a graph-only preview.
- Editing means changing questionnaire answers and regenerating the graph. Drag-and-drop editing is deferred.
- No live model calls, Hermes writes/activation changes, or persistent spec format.

## Acceptance criteria

- [ ] A browser user completes one branching workflow design without writing code; the graph displays its nodes, labeled routes and terminals faithfully.
- [ ] The questionnaire is deterministic and uses only the approved prebound catalog; invalid answers and unsupported declarations fail closed without running arbitrary code.
- [ ] Generate/check invokes the existing core on the authored spec and actual generated candidate with explicit typed offline cases; the UI displays case scope, pass/failure findings and available evidence rather than claiming semantic correctness.
- [ ] A deliberately nonconforming candidate fails through the common check seam; the browser surfaces a failed check rather than reporting success merely because generation completed.
- [ ] Changing an answer changes the authored spec and graph; old generation/check results cannot be presented as evidence for the changed design.
- [ ] Validation, generation, check and evidence-write failures are visible, and incomplete evidence never produces a passing result.
- [ ] Evidence goes only to a caller-named permitted project directory/artifact store, never Hermes or protected source. Browser input cannot select arbitrary executable bindings or bypass output protection.
- [ ] Local serving has an explicit loopback/request-origin boundary; visiting an unrelated website cannot trigger workflow execution through an unprotected local endpoint.
- [ ] Public-seam tests prove questionnaire-to-spec and real generation/conformance behavior. A small real-browser smoke suite proves the complete answer → graph → generate/check path and answer-edit invalidation.
- [ ] Existing offline tests and type checks remain green; independent Standards/Spec review uses the approved baseline. Preserve unrelated edits and use scoped commits.

## Approved demo and public test contract

**Route a request:** choose a numeric threshold and outcomes → inspect the branching graph → generate/check cases below, at and above the threshold.

Use a small fixed catalog of deterministic request-routing operations and typed request state. Question choices must be finite and explicit; the comparison's equality behavior must be visible in the UI and pinned by the at-threshold case. Concrete catalog labels, numeric choices and state field names are bounded implementation details, not permission to add arbitrary expressions or a programming editor.

The public seam is questionnaire answers → typed authored spec and explicit bindings/cases → actual generated candidate → existing conformance report and real logs. Hand-authored expected routes for below/at/above cases constrain intended behavior independently of driver agreement. Tests can supply a deliberately altered candidate through the core seam; the browser must not expose arbitrary candidate code submission.

The caller selects a permitted evidence directory when starting the local app; browser requests cannot override that root. Present the current design's case names, findings, verdict and evidence references in the browser. Changing answers invalidates previous results. A private request representation does not define a persistent public spec format.

Framework and graph-rendering library selection are implementation choices within the approved scope, not reasons to add horizontal frontend/backend tickets. Any necessary small behavior-preserving preparation belongs first inside this slice; no broad prefactor is approved.

## Out of scope

Parallel, Gate or resume execution; Judgment and Loop authoring in this initial UI; drag-and-drop editing; user-provided code; role/data/skill composition; model completeness checks; persistent spec serialization; executable bundle distribution; public hosting; authentication for remote/multi-user use; Hermes plugin activation or protected writes; live calls; universal correctness or savings claims.

## Comments

This is the first published issue from planning-map item P26, not the former tentative parallel ticket 13. Parallel and artifact-identity planning can continue independently, but neither blocks this designer checkpoint. The rest of the whole-product map remains provisional.
