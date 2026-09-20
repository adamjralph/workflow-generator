"use strict";
const byId = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="request-token"]').content;
let revision = 0;
let runRevision = 0;
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
let draft = structuredClone(scoreDefault);
let suppliedCases = [];
const isTriage = () => draft.mode === "triage";
const terminals = () => isTriage() ? ["COMPLETED"] : ["ACCEPTED", "REVIEW"];
const routeLabels = n => n.operation === "compare" ? ["below", "at_or_above"]
  : n.operation === "category" ? ["billing", "technical", "general"]
  : n.operation === "urgency" ? ["normal", "urgent"] : ["done"];
const isDecision = n => ["compare", "category", "urgency"].includes(n.operation);
const answers = () => structuredClone(draft);
function editNodes() {
  const container = byId("nodes");
  container.replaceChildren();
  const destinations = [...draft.nodes.map(n => n.id), ...terminals()];
  byId("custom").hidden = !isTriage();
  byId("triage-entry").hidden = !isTriage();
  byId("triage-catalog").hidden = !isTriage();
  byId("add-adjust").hidden = isTriage();
  byId("add-compare").hidden = isTriage();
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
  view.cases.forEach(c => text(byId("cases"), "li", c.request_id
    ? `${c.request_id}: ${c.category} / ${c.urgency} — ${c.description}` : `${c.name}: score ${c.score}`));
  byId("scope").textContent = typeof view.scope === "string" ? view.scope : JSON.stringify(view.scope || "Unvalidated draft; no case scope yet.");
  byId("infeasible").replaceChildren();
  (view.infeasible_routes || []).forEach(route => text(byId("infeasible"), "li", typeof route === "string" ? route : JSON.stringify(route)));
}
function renderResult(result) {
  const container = byId("result");
  container.replaceChildren();
  text(container, "h3", result.passed ? "PASS — listed cases only" : "FAIL — conformance not established");
  text(container, "p", `Cases: ${result.cases.join(", ")}. Completed: ${result.completed_cases.join(", ") || "none"}.`);
  const findings = text(container, "ul", "");
  result.findings.forEach(f => text(findings, "li", `${f.code} · ${f.path}: ${f.message}`));
  (result.outputs || []).forEach(output => {
    const row = text(container, "article", "");
    row.dataset.case = output.name;
    text(row, "h4", `${output.name} · candidate result`);
    text(row, "p", [...output.route.map(edge => edge[0]), output.terminal].join(" → "));
    text(row, "pre", output.route.map(edge => `${edge[0]} — ${edge[1]} → ${edge[2]}`).join("\n"));
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
  invalidateRun();
  byId("check").disabled = true;
  byId("result").replaceChildren();
  graph(draftView());
  byId("status").textContent = "Design changed; previous check invalidated. Loading design…";
  try {
    const view = await api("/api/design", answers());
    if (current !== revision) return;
    if (isTriage()) suppliedCases = view.cases;
    graph(view);
    designReady = true;
    byId("run").disabled = !isTriage();
    byId("check").disabled = false;
    byId("status").textContent = "Current design ready; not checked.";
  } catch (error) {
    if (current === revision) byId("status").textContent = `Design failed: ${error.message}`;
  }
}
function invalidateRun() {
  ++runRevision;
  byId("run-result").replaceChildren();
  byId("run-status").textContent = "Not run for current workflow and input; previous run invalidated.";
  byId("run").disabled = !designReady || !isTriage();
}
byId("custom-request").addEventListener("input", invalidateRun);
byId("custom-request").addEventListener("change", invalidateRun);
byId("custom-request").addEventListener("submit", async event => {
  event.preventDefault();
  if (!designReady || !isTriage() || byId("run").disabled) return;
  const current = ++runRevision;
  const request = {request_id: byId("request-id").value,
    category: byId("request-category").value, urgency: byId("request-urgency").value,
    description: byId("request-description").value};
  byId("run").disabled = true;
  byId("run-result").replaceChildren();
  byId("run-status").textContent = "Running offline…";
  try {
    const result = await api("/api/run", {design: answers(), request});
    if (current !== runRevision) return;
    const container = byId("run-result"), output = result.output;
    text(container, "h3", result.succeeded ? "Run completed" : "Run failed");
    text(container, "h4", "Submitted input");
    text(container, "pre", JSON.stringify(result.input, null, 2));
    text(container, "p", [...output.route.map(edge => edge[0]), output.terminal].join(" → "));
    text(container, "pre", output.route.map(edge => `${edge[0]} — ${edge[1]} → ${edge[2]}`).join("\n"));
    text(container, "p", `Team: ${output.state.team ?? "unassigned"}; priority: ${output.state.priority ?? "unassigned"}`);
    text(container, "p", output.state.summary || "No handling summary produced");
    text(container, "p", `Terminal: ${output.terminal}; steps spent: ${output.used_steps}`);
    text(container, "pre", `Run evidence: ${result.evidence}`);
    byId("run-status").textContent = result.succeeded
      ? "Run finished; supplied-case conformance evidence unchanged." : "Run failed; no successful run established.";
  } catch (error) {
    if (current !== runRevision) return;
    text(byId("run-result"), "h3", `Run failed — ${error.message}`);
    byId("run-status").textContent = "Run failed; no successful run established.";
  } finally {
    if (current === runRevision) byId("run").disabled = !designReady || !isTriage();
  }
});
byId("mode").addEventListener("change", () => {
  draft = structuredClone(byId("mode").value === "triage" ? triageDefault : scoreDefault);
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
  const current = revision;
  byId("check").disabled = true;
  byId("result").replaceChildren();
  byId("status").textContent = "Generating and checking offline…";
  try {
    const result = await api("/api/check", answers());
    if (current !== revision) return;
    renderResult(result);
    byId("status").textContent = "Check finished for current design.";
  } catch (error) {
    if (current === revision) {
      text(byId("result"), "h3", `FAIL — ${error.message}`);
      byId("status").textContent = "Check failed; no passing evidence.";
    }
  } finally {
    if (current === revision) byId("check").disabled = false;
  }
});
refresh();
