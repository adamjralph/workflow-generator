"use strict";
const byId = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="request-token"]').content;
let revision = 0;
let designReady = false;
const answers = () => ({threshold: Number(byId("threshold").value),
  below: byId("below").value, at_or_above: byId("at_or_above").value});
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
  svg.setAttribute("viewBox", `0 0 1050 ${height}`);
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
  view.terminals.forEach((terminal, i) => positions.set(terminal, {x: 790, y: 40 + i * 105}));
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
    shape("rect", {x: p.x, y: p.y, width: 245, height: 60, rx: 25, class: "terminal"});
    shape("text", {x: p.x+10, y: p.y+35}, terminal);
  });
  byId("graph").replaceChildren(svg);
  byId("budget").textContent = `Step budget: ${view.budget}. All declared terminals are shown, including safety terminals.`;
  byId("cases").replaceChildren();
  view.cases.forEach(c => text(byId("cases"), "li", `${c.name}: score ${c.score} → ${c.expected_terminal}`));
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
  byId("graph").replaceChildren();
  byId("cases").replaceChildren();
  byId("budget").textContent = "";
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
byId("questions").addEventListener("change", refresh);
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
