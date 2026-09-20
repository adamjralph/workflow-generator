"use strict";
const byId = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="request-token"]').content;
let revision = 0;
let runRevision = 0;
let checkRevision = 0;
let captureRevision = 0;
let snapshot = null;
let sourceAvailable = false;
let draftCaptureRevision = 0;
let draftsAvailable = false;
let designReady = false;
let nextId = 1;
const scoreDefault = {nodes: [
  {id: "receive", operation: "receive", done: "threshold"},
  {id: "threshold", operation: "compare", threshold: 50, below: "ACCEPTED", at_or_above: "REVIEW"}
]};
const triageDefault = {mode: "triage", entry: "category", nodes: [
  {id: "category", operation: "category", billing: "billing_team", technical: "technical_team", general: "general_team"},
  {id: "billing_team", operation: "assign_team", team: "billing", done: "urgency"},
  {id: "technical_team", operation: "assign_team", team: "technical", done: "urgency"},
  {id: "general_team", operation: "assign_team", team: "general", done: "urgency"},
  {id: "urgency", operation: "urgency", normal: "normal_priority", urgent: "urgent_priority"},
  {id: "normal_priority", operation: "assign_priority", priority: "normal", done: "summary"},
  {id: "urgent_priority", operation: "assign_priority", priority: "high", done: "summary"},
  {id: "summary", operation: "summarize", done: "COMPLETED"}
]};
const roleDefault = {mode: "roles", producer: "signal_generator", output: "evidence_handoff", consumer: "signal_guardian"};
let roleCatalog = null;
let draft = structuredClone(scoreDefault);
let suppliedCases = [];
const isDraftCapture = () => byId("mode").value === "drafts";
const isTriage = () => draft.mode === "triage";
const isRoles = () => draft.mode === "roles";
const canRun = () => isTriage() || isRoles();
const usesSource = () => isRoles() && byId("role-input").value === "source";
const inputReady = () => !usesSource() || snapshot !== null;
function executionButtons() {
  byId("run").disabled = !designReady || !canRun() || !inputReady();
  byId("check").disabled = !designReady || !inputReady();
}
function clearSource() {
  ++captureRevision;
  ++checkRevision;
  snapshot = null;
  byId("source-preview").replaceChildren();
  byId("source-status").textContent = "No captured input; previous capture invalidated.";
  byId("result").replaceChildren();
  invalidateRun();
  executionButtons();
}
const terminals = () => isTriage() ? ["COMPLETED"] : ["ACCEPTED", "REVIEW"];
const routeLabels = n => n.operation === "compare" ? ["below", "at_or_above"]
  : n.operation === "category" ? ["billing", "technical", "general"]
  : n.operation === "urgency" ? ["normal", "urgent"] : ["done"];
const isDecision = n => ["compare", "category", "urgency"].includes(n.operation);
const answers = () => structuredClone(draft);
function editNodes() {
  byId("offline-workflow").hidden = isDraftCapture();
  byId("draft-capture").hidden = !isDraftCapture();
  const container = byId("nodes");
  container.replaceChildren();
  byId("custom").hidden = !canRun();
  byId("role-choices").hidden = !isRoles();
  byId("role-fixtures").hidden = !isRoles() || usesSource();
  byId("role-source").hidden = !isRoles();
  byId("source-controls").hidden = !usesSource();
  byId("triage-fields").hidden = !isTriage();
  byId("custom-heading").textContent = usesSource() ? "Try captured role input" : isRoles() ? "Try a synthetic role fixture" : "Try a custom support request";
  byId("run").textContent = usesSource() ? "Run captured input" : isRoles() ? "Run fixture" : "Run request";
  byId("check").textContent = usesSource() ? "Check captured input" : "Generate / check";
  byId("cases-heading").textContent = usesSource()
    ? "Built-in fixture scope (not used by captured-input check)" : "Case scope";
  byId("triage-entry").hidden = !isTriage();
  byId("triage-catalog").hidden = !isTriage();
  byId("add-adjust").hidden = isTriage() || isRoles();
  byId("add-compare").hidden = isTriage() || isRoles();
  if (isRoles()) {
    byId("limits").textContent = "One two-role connection; two deterministic fixture Transforms, budget two. No agents or model calls. Inspect declared contracts before running.";
    editRoles();
    return;
  }
  const destinations = [...draft.nodes.map(n => n.id), ...terminals()];
  byId("limits").textContent = isTriage()
    ? "Compose up to 12 nodes and three Decisions. Every path must assign team and priority before summary. Choose destinations; removed nodes leave routes to repair. No cycles. Check supplied cases or run a custom request."
    : "Compose 1–6 nodes, including one receive entry and at most two Decisions. Choose destinations to connect nodes; removing a node leaves incoming routes for you to repair.";
  if (isTriage()) {
    byId("entry").replaceChildren();
    [...new Set([draft.entry, ...draft.nodes.map(n => n.id)])].forEach(id => {
      const option = text(byId("entry"), "option", draft.nodes.some(n => n.id === id) ? id : `Missing: ${id}`);
      option.value = id;
    });
    byId("entry").value = draft.entry;
  }
  draft.nodes.forEach(node => {
    const group = text(container, "fieldset", "");
    group.dataset.node = node.id;
    text(group, "legend", `${node.id} · ${node.operation}`);
    function choice(key, label, values, numeric = false) {
      const id = `${node.id}-${key}`;
      text(group, "label", label).htmlFor = id;
      const select = text(group, "select", "");
      select.id = id;
      if (!values.includes(node[key])) {
        const missing = text(select, "option", `Missing destination: ${node[key]}`);
        missing.value = node[key];
      }
      values.forEach(value => {
        const option = text(select, "option", value);
        option.value = value;
      });
      select.value = node[key];
      select.addEventListener("change", () => {
        node[key] = numeric ? Number(select.value) : select.value;
        refresh();
      });
    }
    if (node.operation === "compare") {
      choice("threshold", "Threshold", [10, 50, 100], true);
      choice("below", "Below threshold", destinations);
      choice("at_or_above", "At or above threshold", destinations);
    } else if (["category", "urgency"].includes(node.operation)) {
      routeLabels(node).forEach(label => choice(label, `${label} destination`, destinations));
    } else {
      if (node.operation === "assign_team") choice("team", "Team", ["billing", "technical", "general"]);
      if (node.operation === "assign_priority") choice("priority", "Priority", ["normal", "high"]);
      if (node.operation === "adjust") choice("adjustment", "Score adjustment", [-10, 10], true);
      choice("done", "Done destination", destinations);
    }
    if (node.operation !== "receive") {
      const remove = text(group, "button", `Remove ${node.id}`);
      remove.type = "button";
      remove.addEventListener("click", () => {
        draft.nodes.splice(draft.nodes.indexOf(node), 1);
        editNodes();
        refresh();
      });
    }
  });
  ["team", "priority", "summary", "category", "urgency"].forEach(kind => {
    byId(`add-${kind}`).disabled = draft.nodes.length >= 12
      || (["category", "urgency"].includes(kind) && draft.nodes.filter(isDecision).length >= 3);
  });
  byId("add-adjust").disabled = draft.nodes.length >= 6;
  byId("add-compare").disabled = draft.nodes.length >= 6 || draft.nodes.filter(n => n.operation === "compare").length >= 2;
}
function editRoles() {
  if (!roleCatalog) return;
  const roles = roleCatalog.roles;
  const producer = roles.find(role => role.id === draft.producer);
  for (const [key, values] of Object.entries({producer: roles.map(r => r.id), output: producer.produces, consumer: roles.map(r => r.id)})) {
    const select = byId(`role-${key}`);
    select.replaceChildren();
    values.forEach(value => {
      const role = roles.find(r => r.id === value);
      const option = text(select, "option", role ? role.display_name : value);
      option.value = value;
    });
    select.value = draft[key];
  }
  const container = byId("role-contracts");
  container.replaceChildren();
  [producer, roles.find(role => role.id === draft.consumer)].forEach(role => {
    text(container, "h3", role.display_name);
    text(container, "p", `Accepts: ${role.accepts.join(", ")}`);
    text(container, "p", `Produces: ${role.produces.join(", ")}`);
    text(container, "p", `Reviews: ${role.reviews.join(", ") || "none"}; reviewed by: ${role.reviewed_by.join(", ") || "none"}. Historical status: ${role.status}.`);
  });
}
function addNode(operation) {
  const id = `${operation}_${nextId++}`;
  const defaults = {
    adjust: {adjustment: 10, done: "ACCEPTED"},
    compare: {threshold: 50, below: "ACCEPTED", at_or_above: "REVIEW"},
    assign_team: {team: "general", done: "COMPLETED"},
    assign_priority: {priority: "normal", done: "COMPLETED"},
    summarize: {done: "COMPLETED"},
    category: {billing: "COMPLETED", technical: "COMPLETED", general: "COMPLETED"},
    urgency: {normal: "COMPLETED", urgent: "COMPLETED"}
  };
  draft.nodes.push({id, operation, ...defaults[operation]});
  editNodes();
  refresh();
}
function draftView() {
  if (isRoles()) return {nodes: [{id: "generator", kind: "Transform", label: draft.producer},
    {id: "guardian", kind: "Transform", label: draft.consumer}],
    edges: [{source: "generator", outcome: draft.output, target: "guardian"},
      {source: "guardian", outcome: "done", target: "COMPLETED"}],
    terminals: ["COMPLETED", "FAILED_VALIDATION", "FAILED_BUDGET"], cases: suppliedCases, budget: "unvalidated"};
  const edges = draft.nodes.flatMap(n => routeLabels(n).map(outcome => ({source: n.id, outcome, target: n[outcome]})));
  const missing = edges.map(e => e.target).filter(id => !draft.nodes.some(n => n.id === id) && !terminals().includes(id));
  return {nodes: draft.nodes.map(n => ({...n, kind: isDecision(n) ? "Decision" : "Transform", label: n.operation})),
    edges, terminals: [...terminals(), ...new Set(missing)], missing, cases: isTriage() ? suppliedCases : [], budget: "unvalidated"};
}
function text(parent, tag, value) {
  const element = document.createElement(tag);
  element.textContent = value;
  parent.append(element);
  return element;
}
async function api(path, value) {
  const response = await fetch(path, {method: "POST", headers: {
    "Content-Type": "application/json", "X-Designer-Token": token}, body: JSON.stringify(value)});
  const result = await response.json();
  if (!response.ok) throw new Error((result.findings || []).map(f => f.message).join("; ") || "Request failed");
  return result;
}
function graph(view) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Authored workflow nodes, routes and terminals");
  const height = Math.max(view.nodes.length, view.terminals.length) * 105 + 80;
  const terminalX = Math.max(790, view.nodes.length * 260);
  svg.setAttribute("viewBox", `0 0 ${terminalX + 270} ${height}`);
  if (isTriage()) {
    svg.classList.add("triage");
    svg.setAttribute("width", terminalX + 270);
    svg.setAttribute("height", height);
  }
  function shape(tag, attrs, content, parent = svg) {
    const el = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
    if (content !== undefined) el.textContent = content;
    parent.append(el);
    return el;
  }
  const defs = shape("defs", {});
  const marker = shape("marker", {id: "arrow", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse"}, undefined, defs);
  shape("path", {d: "M 0 0 L 10 5 L 0 10 z", fill: "#456"}, undefined, marker);
  const positions = new Map();
  view.nodes.forEach((node, i) => positions.set(node.id, {x: 20 + i * 260, y: 40 + i * 105}));
  view.terminals.forEach((terminal, i) => positions.set(terminal, {x: terminalX, y: 40 + i * 105}));
  view.edges.forEach((edge, i) => {
    const source = positions.get(edge.source), target = positions.get(edge.target);
    if (!source || !target) return;
    const x1 = source.x + 210, y1 = source.y + 30, x2 = target.x, y2 = target.y + 30;
    shape("path", {d: `M ${x1} ${y1} C ${x1 + 55} ${y1}, ${x2 - 55} ${y2}, ${x2} ${y2}`, class: "route", "marker-end": "url(#arrow)"});
    shape("text", {x: (x1+x2)/2, y: (y1+y2)/2 - 8 - (i % 2)*14, class: "route-label"}, edge.outcome);
  });
  view.nodes.forEach(node => {
    const p = positions.get(node.id);
    shape("rect", {x: p.x, y: p.y, width: 210, height: 65, rx: 8, class: "node"});
    shape("text", {x: p.x+8, y: p.y+22}, `${node.id} · ${node.kind}`);
    shape("text", {x: p.x+8, y: p.y+46, class: "label"}, node.label);
  });
  view.terminals.forEach(terminal => {
    const p = positions.get(terminal);
    const missing = (view.missing || []).includes(terminal);
    shape("rect", {x: p.x, y: p.y, width: 245, height: 60, rx: 25, class: missing ? "missing" : "terminal"});
    shape("text", {x: p.x+10, y: p.y+35}, missing ? `Missing: ${terminal}` : terminal);
  });
  byId("graph").replaceChildren(svg);
  byId("budget").textContent = `Step budget: ${view.budget} — longest admitted path, counting nodes and excluding terminals.`;
  byId("cases").replaceChildren();
  view.cases.forEach(c => text(byId("cases"), "li", isRoles() ? `${c.name}: ${JSON.stringify(c)}` : c.request_id
    ? `${c.request_id}: ${c.category} / ${c.urgency} — ${c.description}` : `${c.name}: score ${c.score}`));
  byId("scope").textContent = typeof view.scope === "string" ? view.scope : JSON.stringify(view.scope || "Unvalidated draft; no case scope yet.");
  byId("infeasible").replaceChildren();
  (view.infeasible_routes || []).forEach(route => text(byId("infeasible"), "li", typeof route === "string" ? route : JSON.stringify(route)));
}
function renderResult(result) {
  const container = byId("result");
  container.replaceChildren();
  text(container, "h3", result.passed ? (result.snapshot ? "PASS — captured input only" : "PASS — listed cases only") : "FAIL — conformance not established");
  if (result.snapshot) text(container, "p", `${result.source} · Snapshot: ${result.snapshot}`);
  text(container, "p", `Cases: ${result.cases.join(", ")}. Completed: ${result.completed_cases.join(", ") || "none"}.`);
  const findings = text(container, "ul", "");
  result.findings.forEach(f => text(findings, "li", `${f.code} · ${f.path}: ${f.message}`));
  (result.outputs || []).forEach(output => {
    const row = text(container, "article", "");
    row.dataset.case = output.name;
    text(row, "h4", `${output.name} · candidate result`);
    text(row, "p", [...output.route.map(edge => edge[0]), output.terminal].join(" → "));
    text(row, "pre", output.route.map(edge => `${edge[0]} — ${edge[1]} → ${edge[2]}`).join("\n"));
    if (output.state.brief !== undefined) text(row, "pre", JSON.stringify(output.state, null, 2));
    if (output.state.summary !== undefined) {
      text(row, "p", `Team: ${output.state.team ?? "unassigned"}; priority: ${output.state.priority ?? "unassigned"}`);
      text(row, "p", output.state.summary || "No handling summary produced");
    }
    text(row, "p", `Terminal: ${output.terminal}; steps spent: ${output.used_steps}`);
  });
  text(container, "h4", "Evidence paths");
  result.evidence.forEach(e => {
    text(container, "p", e.name);
    text(container, "pre", `Reference: ${e.reference_log}\nCandidate: ${e.candidate_log}`);
  });
}
async function refresh() {
  const current = ++revision;
  designReady = false;
  clearSource();
  clearDraftCapture();
  byId("check").disabled = true;
  if (isDraftCapture()) return;
  byId("result").replaceChildren();
  graph(draftView());
  byId("status").textContent = "Design changed; previous check invalidated. Loading design…";
  try {
    const view = await api("/api/design", answers());
    if (current !== revision) return;
    if (canRun()) suppliedCases = view.cases;
    if (isRoles()) {
      roleCatalog = view.catalog;
      editRoles();
      byId("role-policy").textContent = view.policy;
      byId("role-operations").textContent = `Executable fixture operation contracts:\n${JSON.stringify(view.operations, null, 2)}`;
      byId("role-provenance").textContent = JSON.stringify(view.catalog.provenance);
    }
    graph(view);
    designReady = true;
    executionButtons();
    byId("status").textContent = "Current design ready; not checked.";
  } catch (error) {
    if (current === revision) byId("status").textContent = `Design failed: ${error.message}`;
  }
}
function invalidateRun() {
  ++runRevision;
  byId("run-result").replaceChildren();
  byId("run-status").textContent = "Not run for current workflow and input; previous run invalidated.";
  byId("run").disabled = !designReady || !canRun() || !inputReady();
}
byId("role-input").addEventListener("change", () => {
  editNodes();
  refresh();
});
byId("capture").addEventListener("click", async () => {
  if (!usesSource() || !sourceAvailable) return;
  clearSource();
  const current = captureRevision;
  byId("status").textContent = "Captured-input check invalidated; not checked.";
  byId("source-status").textContent = "Capturing…";
  try {
    const result = await api("/api/source/capture", {});
    if (current !== captureRevision) return;
    snapshot = result.snapshot;
    byId("source-preview").textContent = `${result.source}\nSnapshot: ${snapshot}\n${JSON.stringify(result.input, null, 2)}`;
    byId("source-status").textContent = "Captured input ready to inspect; changes require recapture.";
    executionButtons();
  } catch (error) {
    if (current !== captureRevision) return;
    byId("source-status").textContent = `Capture failed — ${error.message}`;
  }
});
fetch("/api/source").then(async response => {
  if (!response.ok) throw new Error("Source availability failed");
  const result = await response.json();
  sourceAvailable = result.available;
  byId("source-availability").textContent = sourceAvailable ? `${result.source} available (read-only).` : "Source not configured. Synthetic fixtures remain available.";
  byId("capture").disabled = !sourceAvailable;
}).catch(() => {
  byId("source-availability").textContent = "Source availability failed. Synthetic fixtures remain available.";
});
function clearDraftCapture() {
  ++draftCaptureRevision;
  byId("draft-preview").replaceChildren();
  byId("draft-status").textContent = "No captured input; previous capture invalidated.";
}
byId("draft-capture-button").addEventListener("click", async () => {
  if (!isDraftCapture() || !draftsAvailable) return;
  clearDraftCapture();
  const current = draftCaptureRevision;
  byId("draft-status").textContent = "Capturing…";
  try {
    const result = await api("/api/drafts/capture", {});
    if (current !== draftCaptureRevision) return;
    const container = byId("draft-preview");
    text(container, "h3", "Selection inventory");
    for (const entry of result.entries) {
      text(container, "p", `${entry.name}: ${entry.status} — ${entry.reason}${entry.date_created ? ` (${entry.date_created})` : ""}`);
    }
    if (!result.succeeded) {
      for (const finding of result.findings) text(container, "p", `${finding.path}: ${finding.message}`);
      byId("draft-status").textContent = "Capture blocked; no input selected or saved.";
      return;
    }
    text(container, "h3", `${result.selected.name} · ${result.selected.date_created}`);
    text(container, "p", `Snapshot: ${result.snapshot} · Source digest: ${result.selected.digest}`);
    text(container, "pre", result.selected.text);
    text(container, "h3", "Captured role defaults (not authenticated or executed)");
    for (const model of result.models) text(container, "p", `${model.role}: ${model.provider} / ${model.model}`);
    text(container, "h3", "Captured authority — explicit files only, links are not followed");
    for (const item of result.guidance) {
      const details = text(container, "details", "");
      text(details, "summary", item.name);
      text(details, "p", `${item.path} · ${item.digest}`);
      text(details, "pre", item.text);
    }
    text(container, "p", `Instruction version: ${result.instruction_version}`);
    text(container, "pre", `Private capture evidence: ${result.evidence.join("\n")}`);
    byId("draft-status").textContent = "Captured input ready to inspect. Source, guidance or model changes require explicit recapture. Not run or reviewed.";
  } catch (error) {
    if (current !== draftCaptureRevision) return;
    byId("draft-status").textContent = `Capture failed — ${error.message}`;
  }
});
fetch("/api/drafts").then(async response => {
  if (!response.ok) throw new Error("Draft availability failed");
  const result = await response.json();
  draftsAvailable = result.available;
  byId("draft-availability").textContent = draftsAvailable
    ? "LinkedIn draft capture available (read-only)."
    : "Draft capture not configured. Start with an operator --draft-config manifest.";
  byId("draft-capture-button").disabled = !draftsAvailable;
}).catch(() => {
  byId("draft-availability").textContent = "Draft availability failed. Capture is unavailable.";
});
byId("custom-request").addEventListener("input", invalidateRun);
byId("custom-request").addEventListener("change", invalidateRun);
byId("custom-request").addEventListener("submit", async event => {
  event.preventDefault();
  if (!designReady || !canRun() || byId("run").disabled) return;
  const current = ++runRevision;
  const request = isRoles() ? {fixture: byId("role-fixture").value} : {request_id: byId("request-id").value,
    category: byId("request-category").value, urgency: byId("request-urgency").value,
    description: byId("request-description").value};
  byId("run").disabled = true;
  byId("run-result").replaceChildren();
  byId("run-status").textContent = "Running offline…";
  try {
    const result = await api(usesSource() ? "/api/source/run" : "/api/run",
      usesSource() ? {design: answers(), snapshot} : {design: answers(), request});
    if (current !== runRevision) return;
    const container = byId("run-result"), output = result.output;
    text(container, "h3", result.succeeded ? "Run completed" : "Run failed");
    if (result.snapshot) text(container, "p", `${result.source} · Snapshot: ${result.snapshot}. Successful execution is not conformance.`);
    text(container, "h4", "Submitted input");
    text(container, "pre", JSON.stringify(result.input, null, 2));
    text(container, "p", [...output.route.map(edge => edge[0]), output.terminal].join(" → "));
    text(container, "pre", output.route.map(edge => `${edge[0]} — ${edge[1]} → ${edge[2]}`).join("\n"));
    if (isRoles()) {
      text(container, "h4", "Offline handoff and mechanical result — not a real review");
      text(container, "pre", JSON.stringify(output.state, null, 2));
    } else {
      text(container, "p", `Team: ${output.state.team ?? "unassigned"}; priority: ${output.state.priority ?? "unassigned"}`);
      text(container, "p", output.state.summary || "No handling summary produced");
    }
    text(container, "p", `Terminal: ${output.terminal}; steps spent: ${output.used_steps}`);
    text(container, "pre", `Run evidence: ${result.evidence}`);
    byId("run-status").textContent = result.succeeded
      ? "Run finished; supplied-case conformance evidence unchanged." : "Run failed; no successful run established.";
  } catch (error) {
    if (current !== runRevision) return;
    text(byId("run-result"), "h3", `Run failed — ${error.message}`);
    byId("run-status").textContent = "Run failed; no successful run established.";
  } finally {
    if (current === runRevision) byId("run").disabled = !designReady || !canRun() || !inputReady();
  }
});
["producer", "output", "consumer"].forEach(key => byId(`role-${key}`).addEventListener("change", () => {
  draft[key] = byId(`role-${key}`).value;
  if (key === "producer") draft.output = roleCatalog.roles.find(r => r.id === draft.producer).produces[0];
  editRoles();
  refresh();
}));
byId("mode").addEventListener("change", () => {
  draft = structuredClone(byId("mode").value === "roles" ? roleDefault : byId("mode").value === "triage" ? triageDefault : scoreDefault);
  suppliedCases = [];
  nextId = 1;
  editNodes();
  refresh();
});
byId("entry").addEventListener("change", () => { draft.entry = byId("entry").value; refresh(); });
Object.entries({team: "assign_team", priority: "assign_priority", summary: "summarize", category: "category", urgency: "urgency"})
  .forEach(([kind, operation]) => byId(`add-${kind}`).addEventListener("click", () => addNode(operation)));
byId("add-adjust").addEventListener("click", () => addNode("adjust"));
byId("add-compare").addEventListener("click", () => addNode("compare"));
editNodes();
byId("questions").addEventListener("submit", async event => {
  event.preventDefault();
  if (!designReady || byId("check").disabled) return;
  const current = ++checkRevision;
  byId("check").disabled = true;
  byId("result").replaceChildren();
  byId("status").textContent = "Generating and checking offline…";
  try {
    const result = await api(usesSource() ? "/api/source/check" : "/api/check",
      usesSource() ? {design: answers(), snapshot} : answers());
    if (current !== checkRevision) return;
    renderResult(result);
    byId("status").textContent = "Check finished for current design.";
  } catch (error) {
    if (current === checkRevision) {
      text(byId("result"), "h3", `FAIL — ${error.message}`);
      byId("status").textContent = "Check failed; no passing evidence.";
    }
  } finally {
    if (current === checkRevision) byId("check").disabled = !designReady || !inputReady();
  }
});
refresh();
