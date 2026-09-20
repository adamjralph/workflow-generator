"use strict";
const byId = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="request-token"]').content;
let revision = 0;
let designReady = false;
let nextId = 1;
const draft = {nodes: [
  {id: "receive", operation: "receive", done: "threshold"},
  {id: "threshold", operation: "compare", threshold: 50, below: "ACCEPTED", at_or_above: "REVIEW"}
]};
const answers = () => structuredClone(draft);
function editNodes() {
  const container = byId("nodes");
  container.replaceChildren();
  const destinations = [...draft.nodes.map(n => n.id), "ACCEPTED", "REVIEW"];
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
    } else {
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
  byId("add-adjust").disabled = draft.nodes.length >= 6;
  byId("add-compare").disabled = draft.nodes.length >= 6 || draft.nodes.filter(n => n.operation === "compare").length >= 2;
}
function addNode(operation) {
  const id = `${operation}_${nextId++}`;
  draft.nodes.push(operation === "adjust"
    ? {id, operation, adjustment: 10, done: "ACCEPTED"}
    : {id, operation, threshold: 50, below: "ACCEPTED", at_or_above: "REVIEW"});
  editNodes();
  refresh();
}
function draftView() {
  const edges = draft.nodes.flatMap(n => (n.operation === "compare" ? ["below", "at_or_above"] : ["done"])
    .map(outcome => ({source: n.id, outcome, target: n[outcome]})));
  const missing = edges.map(e => e.target).filter(id => !draft.nodes.some(n => n.id === id) && !["ACCEPTED", "REVIEW"].includes(id));
  return {nodes: draft.nodes.map(n => ({...n, kind: n.operation === "compare" ? "Decision" : "Transform", label: n.operation})),
    edges, terminals: ["ACCEPTED", "REVIEW", ...new Set(missing)], missing, cases: [], budget: "unvalidated"};
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
  byId("budget").textContent = `Step budget: ${view.budget} — longest executable path, counting nodes and excluding terminals.`;
  byId("cases").replaceChildren();
  view.cases.forEach(c => text(byId("cases"), "li", `${c.name}: score ${c.score}`));
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
  text(container, "h4", "Evidence paths");
  result.evidence.forEach(e => {
    text(container, "p", e.name);
    text(container, "pre", `Reference: ${e.reference_log}\nCandidate: ${e.candidate_log}`);
  });
}
async function refresh() {
  const current = ++revision;
  designReady = false;
  byId("check").disabled = true;
  byId("result").replaceChildren();
  graph(draftView());
  byId("status").textContent = "Design changed; previous check invalidated. Loading design…";
  try {
    const view = await api("/api/design", answers());
    if (current !== revision) return;
    graph(view);
    designReady = true;
    byId("check").disabled = false;
    byId("status").textContent = "Current design ready; not checked.";
  } catch (error) {
    if (current === revision) byId("status").textContent = `Design failed: ${error.message}`;
  }
}
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
