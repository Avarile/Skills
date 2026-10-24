const D = __DATA__;
const stage = document.querySelector(".dc-stage");
const svg = stage.querySelector("svg");
const readout = document.querySelector("[data-readout]");
const status = document.querySelector("[data-status]");
const still = matchMedia("(prefers-reduced-motion: reduce)");
const $ = (s) => svg.querySelector(s);
const $$ = (s) => [...svg.querySelectorAll(s)];

// Rail slots: a panel riding over a chunk of rail is drawn in the slot that follows that chunk.
const slots = {};
for (const g of $$("[data-slot]")) (slots[g.dataset.slot] ??= []).push({ g, a: +g.dataset.a, b: +g.dataset.b });
for (const list of Object.values(slots)) list.sort((x, y) => x.a - y.a);
const logs = { x: $('[data-log="x"]'), y: $('[data-log="y"]') };
const logLines = { x: [], y: [] };
for (const id of ["x", "y"]) logLines[id] = [...logs[id].querySelectorAll("text")].map((t) => t.textContent);
const leds = { x: $$('[data-led^="x"]'), y: $$('[data-led^="y"]') };
const beacon = $('[data-part="beacon"]');
const pmCard = $('[data-part="pm-card"]');
const crmCard = $('[data-part="crm-card"]');
const eye = $('[data-part="ag-eye"]');
const fingers = $$("[data-finger]");
const agStatus = $('[data-part="ag-status"]');
const agStep = $('[data-part="ag-step"]');

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const smooth = (a, b, x) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
const linkOf = (from, to) => {
  const link = D.links.find((l) => (l.a === from && l.b === to) || (l.a === to && l.b === from));
  return { id: link.id, reverse: link.a !== from };
};
const faceFor = (node) => (node === "crm" ? "x" : "y");

const state = {
  step: 0,
  pending: 0,
  wait: 0.8,
  packets: [],
  records: 0,
  label: D.steps[0].label,
  touring: !still.matches,
  run: 0,
  // eased poses
  card: { col: 1, row: 0, at: [0, 0, 0], to: [0, 0, 0], lift: 0, fade: 1, fadeTo: 1 },
  crm: { at: 0, to: 0, hold: 0 },
  grip: { at: 0, to: 0, hold: 0 },
  eye: 0,
  beacon: 0,
  ledClock: 0,
};

function say() {
  const text = `${state.label} · ${state.records} records synced`;
  if (readout.textContent !== text) readout.textContent = text;
}

function pushLog(face, text) {
  const lines = logLines[face];
  lines.push(text);
  while (lines.length > 12) lines.shift();
  const texts = [...logs[face].querySelectorAll("text")];
  const shown = lines.slice(-texts.length);
  texts.forEach((t, i) => {
    const line = shown[i] ?? "";
    const [head, ...rest] = line.split(" ");
    t.firstChild.textContent = head;
    t.lastChild.textContent = " " + rest.join(" ");
    t.toggleAttribute("data-new", i === texts.length - 1);
  });
  logs[face].dataset.t = "0";
  logs[face].setAttribute("transform", `translate(0 1.86)`);
}

function blink(face, count = 3) {
  const list = leds[face];
  for (let i = 0; i < count; i++) {
    const led = list[(Math.random() * list.length) | 0];
    led.setAttribute("data-on", "");
    led.dataset.until = String(performance.now() + 180 + Math.random() * 260);
  }
}

function arrive(hop) {
  state.records += hop.records;
  say();
  const sign = hop.from === "dc" ? "->" : "<-";
  if (hop.to === "dc" || hop.from === "dc") {
    const other = hop.to === "dc" ? hop.from : hop.to;
    pushLog(faceFor(other), `${sign}${other} ${hop.log}`);
    blink(faceFor(other), 4);
    state.beacon = 1;
  }
  if (hop.to === "pm") {
    if (hop.from === "ag") moveCard(2, 2);
    else if (state.card.col !== 1) resetCard();
  }
  if (hop.to === "crm") (state.crm.to = 1), (state.crm.hold = 1.6);
  if (hop.to === "ag") {
    state.eye = 1;
    state.grip.to = 1;
    state.grip.hold = 1.2;
    agStatus.firstChild.textContent = "run";
    agStatus.lastChild.textContent = ` ${hop.from}->ag ${hop.records} rec`;
    agStep.textContent = hop.from === "dc" ? "step 3/7 read ctx" : "step 1/7 plan";
  }
  if (hop.from === "ag") {
    agStatus.firstChild.textContent = "act";
    agStatus.lastChild.textContent = ` ag->${hop.to} ${hop.records} rec`;
    agStep.textContent = "step 6/7 write";
  }
}

function send(hop, run) {
  const { id, reverse } = linkOf(hop.from, hop.to);
  const total = D.routes[id].total;
  if (hop.from === "ag") (state.grip.to = 1), (state.grip.hold = 0.8), (state.eye = 1);
  if (hop.from === "crm") (state.crm.to = 1), (state.crm.hold = 1.2);
  launch(id, reverse, hop, run, false);
}

function startStep(index, run = state.run) {
  const step = D.steps[index];
  state.step = index;
  state.label = step.label;
  state.pending = step.hops.length;
  say();
  status.textContent = `${step.label}: ${step.hops.map((h) => `${h.from} to ${h.to}, ${h.records} records`).join("; ")}.`;
  if (still.matches) {
    step.hops.forEach((hop) => arrive(hop));
    state.pending = 0;
    return;
  }
  step.hops.forEach((hop) => send(hop, run));
}

function moveCard(col, row) {
  state.card.col = col;
  state.card.row = row;
  state.card.to = [0, D.cols[col] - D.cols[1], D.cardZ[[0, 1, 2].indexOf(row) >= 0 ? row : 0] - D.cardZ[0]];
}
function resetCard() {
  state.card.fadeTo = 0;
  state.card.resetting = true;
}

function startChain(node) {
  const index = { crm: 0, pm: 1, dc: 2, ag: 3 }[node] ?? 0;
  state.run++;
  state.packets.forEach((p) => (p.run = -1));
  queue.length = 0;
  state.wait = 0;
  if (index <= 1 && state.card.col !== 1) resetCard();
  startStep(index);
}

// ── Data panels: thin glass sheets of code that ride the rails ───────────────
const NS = "http://www.w3.org/2000/svg";
const PN = D.panel;
const V = D.view;
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const mul = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const pt = (p) => iso(p, D.P);
const poly = (list) => "M" + list.map((p) => pt(p).map((v) => v.toFixed(2)).join(" ")).join("L") + "Z";
const toneOf = (n) => {
  const score = dot(n, D.light);
  let tone = 0;
  while (tone < D.bands.length && score >= D.bands[tone]) tone++;
  return Math.min(3, tone);
};
const rails = {};
for (const [id, r] of Object.entries(D.routes)) {
  const cum = [0];
  for (let i = 1; i < r.points.length; i++) cum.push(cum[i - 1] + Math.hypot(...[0, 1, 2].map((k) => r.points[i][k] - r.points[i - 1][k])));
  rails[id] = { ...r, cum };
}
function along(rail, s) {
  const { points, cum } = rail;
  let i = 1;
  while (i < cum.length - 1 && cum[i] < s) i++;
  const t = clamp((s - cum[i - 1]) / (cum[i] - cum[i - 1] || 1), 0, 1);
  const a = points[i - 1];
  const b = points[i];
  const d = [b[0] - a[0], b[1] - a[1], 0];
  const l = Math.hypot(d[0], d[1]) || 1;
  return { p: [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t], d: [d[0] / l, d[1] / l, 0] };
}
const PITCH = 2.1;
const FONT = 1.55;
const CHARS = 19;
function wrap(text) {
  const out = [];
  let line = "";
  for (const word of text.split(" ")) {
    if (line && (line + " " + word).length > CHARS) (out.push(line), (line = ""));
    line = line ? line + " " + word : word;
  }
  if (line) out.push(line);
  return out;
}
let panelIds = 0;
function makePanel() {
  const id = `dc-pn-${panelIds++}`;
  const w = PN.w / 2;
  const g = document.createElementNS(NS, "g");
  g.setAttribute("class", "dc-panel");
  g.innerHTML =
    `<path class="dc-car" data-car="0"/><path class="dc-car" data-car="1"/><path class="dc-car dc-car-top"/>` +
    `<path class="dc-edge" data-edge="top"/><path class="dc-edge" data-edge="side"/>` +
    `<g data-face><clipPath id="${id}-grow"><rect x="${-w - 1}" width="${PN.w + 2}" y="0" height="0"/></clipPath>` +
    `<clipPath id="${id}-win"><rect x="${-w + 1.1}" y="${-PN.h + 1.2}" width="${PN.w - 2.2}" height="${PN.h - 2.4}" rx="0.5"/></clipPath>` +
    `<g clip-path="url(#${id}-grow)"><rect class="dc-glass" x="${-w}" y="${-PN.h}" width="${PN.w}" height="${PN.h}" rx="0.8"/>` +
    `<g clip-path="url(#${id}-win)"><g data-code></g></g>` +
    `<rect class="dc-sheen" x="${-w}" y="${-PN.h}" width="${PN.w}" height="${PN.h * 0.38}" rx="0.8"/>` +
    `<rect class="dc-frame" x="${-w}" y="${-PN.h}" width="${PN.w}" height="${PN.h}" rx="0.8"/></g></g>`;
  return { g, face: g.querySelector("[data-face]"), growRect: g.querySelector(`#${id}-grow rect`), code: g.querySelector("[data-code]"), cars: [...g.querySelectorAll("[data-car]")], top: g.querySelector(".dc-car-top"), edgeTop: g.querySelector('[data-edge="top"]'), edgeSide: g.querySelector('[data-edge="side"]'), busy: false };
}
const pool = Array.from({ length: 18 }, makePanel);

function fill(panel, hop, ambient) {
  const lines = ambient
    ? Array.from({ length: 6 }, (_, i, list = D.code[hop.from]) => list[(((Math.random() * list.length) | 0) + i * 3) % list.length])
    : [`${hop.from} -> ${hop.to}`, `${hop.records} rec`, ...wrap(hop.log)];
  const all = [...lines, "", ...lines, ""];
  const x = -PN.w / 2 + 1.5;
  panel.code.innerHTML = all.map((line, i) => {
    const [head, ...rest] = line.split(" ");
    return `<text class="dc-code" x="${x}" y="${(-PN.h + 1.4 + FONT + i * PITCH).toFixed(2)}" font-size="${FONT}"><tspan class="dc-kw">${head}</tspan> ${rest.join(" ")}</text>`;
  }).join("");
  panel.loop = (lines.length + 1) * PITCH;
}

// Each rail is single-track: one panel on it at a time. A chain's panel waits its turn; a trickle skips.
const queue = [];
const railBusy = (id) => state.packets.some((p) => p.id === id);
function launch(id, reverse, hop, run, ambient) {
  if (railBusy(id)) return ambient ? null : (queue.push([id, reverse, hop, run]), null);
  const panel = pool.find((p) => !p.busy);
  if (!panel) return ambient ? null : (queue.push([id, reverse, hop, run]), null);
  const rail = rails[id];
  panel.busy = true;
  Object.assign(panel, { id, reverse, hop, run, ambient, rail, s: rail.ends[0], t: 0, grow: 0, phase: "rise", scroll: Math.random() * 10, arrived: false });
  panel.g.toggleAttribute("data-story", !ambient);
  fill(panel, hop, ambient);
  state.packets.push(panel);
  return panel;
}

// Single change records trickle along every link between chains, on smaller-print panels.
const trickleAt = Object.fromEntries(D.links.map((l, i) => [l.id, 0.4 + i * 0.7]));
function trickle(dt) {
  if (!state.touring && !state.chain) return;
  const chainRails = state.pending > 0 ? D.steps[state.step].hops.map((h) => linkOf(h.from, h.to).id) : [];
  for (const link of D.links) {
    trickleAt[link.id] -= dt;
    if (trickleAt[link.id] > 0 || chainRails.includes(link.id)) continue;
    trickleAt[link.id] = D.trickle.every * (0.55 + Math.random() * 0.9);
    const reverse = Math.random() < 0.5;
    launch(link.id, reverse, { from: reverse ? link.b : link.a, to: reverse ? link.a : link.b, records: D.trickle.records }, -1, true);
  }
}

function place(panel) {
  const rail = panel.rail;
  const sAbs = panel.reverse ? rail.total - panel.s : panel.s;
  const { p, d } = along(rail, sAbs);
  // the face looks at the viewer and reads left to right on screen
  let u = d;
  if (axisVector(D.P, u)[0] < 0) u = mul(u, -1);
  let m = [-u[1], u[0], 0];
  if (dot(m, V) < 0) m = mul(m, -1);
  const z0 = PN.z0;
  const h = PN.h * panel.grow;
  const hw = PN.w / 2;
  const ht = PN.t / 2;
  const base = [p[0], p[1], z0];
  // carriage: a small block hovering over the rail
  const cl = PN.car.l / 2;
  const cw = PN.car.w / 2;
  const c0 = PN.car.z0;
  const corner = (a, b, z) => [p[0] + u[0] * a + m[0] * b, p[1] + u[1] * a + m[1] * b, z];
  const end = dot(u, V) > 0 ? 1 : -1;
  panel.cars[0].setAttribute("d", poly([corner(-cl, cw, c0), corner(cl, cw, c0), corner(cl, cw, z0), corner(-cl, cw, z0)]));
  panel.cars[0].dataset.shade = toneOf(m);
  panel.cars[1].setAttribute("d", poly([corner(end * cl, -cw, c0), corner(end * cl, cw, c0), corner(end * cl, cw, z0), corner(end * cl, -cw, z0)]));
  panel.cars[1].dataset.shade = toneOf(mul(u, end));
  panel.top.setAttribute("d", poly([corner(-cl, -cw, z0), corner(cl, -cw, z0), corner(cl, cw, z0), corner(-cl, cw, z0)]));
  // the glass sheet's thickness: its top edge and the end that faces the viewer
  const zt = z0 + h;
  panel.edgeTop.setAttribute("d", h > 0.05 ? poly([corner(-hw, -ht, zt), corner(hw, -ht, zt), corner(hw, ht, zt), corner(-hw, ht, zt)]) : "");
  panel.edgeSide.setAttribute("d", h > 0.05 ? poly([corner(end * hw, -ht, z0), corner(end * hw, ht, z0), corner(end * hw, ht, zt), corner(end * hw, -ht, zt)]) : "");
  // the face, in its own plane
  const o = pt([base[0] + m[0] * ht, base[1] + m[1] * ht, z0]);
  const ax = axisVector(D.P, u);
  const dz = axisVector(D.P, [0, 0, -1]);
  panel.face.setAttribute("transform", `matrix(${ax[0].toFixed(4)} ${ax[1].toFixed(4)} ${dz[0].toFixed(4)} ${dz[1].toFixed(4)} ${o[0].toFixed(2)} ${o[1].toFixed(2)})`);
  panel.growRect.setAttribute("y", (-h).toFixed(2));
  panel.growRect.setAttribute("height", h.toFixed(2));
  panel.code.setAttribute("transform", `translate(0 ${(-(panel.scroll % panel.loop)).toFixed(2)})`);
  // draw it in the slot of the rail chunk under it
  const list = slots[panel.id];
  let slot = list[0];
  for (const c of list) if (c.a <= sAbs) slot = c;
  if (panel.g.parentNode !== slot.g) slot.g.appendChild(panel.g);
}

const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
function drawPackets(dt) {
  for (let i = 0; i < queue.length; i++) {
    const [id] = queue[i];
    if (railBusy(id)) continue;
    const [, reverse, hop, run] = queue.splice(i--, 1)[0];
    launch(id, reverse, hop, run, false);
  }
  state.packets = state.packets.filter((panel) => {
    const [s0, s1] = panel.rail.ends;
    const travel = (s1 - s0) / D.speed + 0.6;
    panel.scroll += dt * (panel.ambient ? 2.4 : 1.6);
    if (panel.phase === "rise") {
      panel.grow = Math.min(1, panel.grow + dt / 0.4);
      panel.g.style.opacity = Math.min(1, panel.grow * 3).toFixed(3);
      if (panel.grow >= 1) panel.phase = "run";
    } else if (panel.phase === "run") {
      panel.t = Math.min(1, panel.t + dt / travel);
      panel.s = s0 + (s1 - s0) * ease(panel.t);
      if (panel.t >= 1) panel.phase = "sink";
    } else {
      if (!panel.arrived) {
        panel.arrived = true;
        if (panel.ambient) {
          state.records += panel.hop.records;
          say();
          if (panel.hop.to === "dc" || panel.hop.from === "dc") blink(faceFor(panel.hop.to === "dc" ? panel.hop.from : panel.hop.to), 1);
        } else {
          arrive(panel.hop);
          if (panel.run === state.run) state.pending--;
        }
      }
      panel.grow = Math.max(0, panel.grow - dt / 0.4);
      panel.g.style.opacity = Math.min(1, panel.grow * 3).toFixed(3);
    }
    place(panel);
    if (panel.phase === "sink" && panel.grow <= 0) {
      panel.busy = false;
      panel.g.remove();
      return false;
    }
    return true;
  });
  return state.packets.length > 0 || queue.length > 0;
}

const follow = (cur, to, dt, tau) => (still.matches ? to : cur + (to - cur) * (1 - Math.exp(-dt / tau)));

function drawPoses(dt, now) {
  let busy = false;
  // planning card: lift off the board, travel, set back down
  const card = state.card;
  if (card.resetting) {
    card.fade = follow(card.fade, card.fadeTo, dt, 0.18);
    if (card.fade < 0.02) {
      card.fade = 0;
      card.col = 1;
      card.row = 0;
      card.to = [0, 0, 0];
      card.at = [0, 0, 0];
      card.fadeTo = 1;
      card.resetting = false;
    }
    busy = true;
  } else if (card.fade < 0.999) {
    card.fade = follow(card.fade, 1, dt, 0.2);
    if (card.fade > 0.998) card.fade = 1;
    busy = true;
  }
  const far = Math.hypot(card.to[1] - card.at[1], card.to[2] - card.at[2]);
  card.lift = follow(card.lift, far > 0.6 ? 2.4 : 0, dt, 0.12);
  const moving = card.lift > 1.6 || far < 0.6;
  if (moving) {
    card.at[1] = follow(card.at[1], card.to[1], dt, 0.28);
    card.at[2] = follow(card.at[2], card.to[2], dt, 0.28);
  }
  if (far > 0.02 || card.lift > 0.02) busy = true;
  else card.lift = 0;
  pmCard.setAttribute("transform", translateAlong(D.P, [card.lift, card.at[1], card.at[2]]));
  pmCard.style.opacity = card.fade < 1 ? card.fade.toFixed(3) : "";

  // rotary file: the record card rides out of the drum and back
  const crm = state.crm;
  if (crm.hold > 0) crm.hold -= dt;
  else crm.to = 0;
  crm.at = follow(crm.at, crm.to, dt, 0.22);
  if (Math.abs(crm.at - crm.to) > 0.002 || crm.hold > 0) busy = true;
  else crm.at = crm.to;
  crmCard.setAttribute("transform", translateAlong(D.P, D.crmLift.map((v) => v * crm.at * 5)));

  // gripper closes while the agent works
  const grip = state.grip;
  if (grip.hold > 0) grip.hold -= dt;
  else grip.to = 0;
  grip.at = follow(grip.at, grip.to, dt, 0.12);
  if (Math.abs(grip.at - grip.to) > 0.002 || grip.hold > 0) busy = true;
  else grip.at = grip.to;
  fingers.forEach((f) => f.setAttribute("transform", translateAlong(D.P, D.armD.map((v) => -v * Number(f.dataset.finger) * grip.at * 1.1))));

  state.eye = Math.max(0, state.eye - dt * 0.6);
  eye.toggleAttribute("data-on", state.eye > 0.05);
  state.beacon = Math.max(0, state.beacon - dt * 2.2);
  beacon.toggleAttribute("data-on", state.beacon > 0.05);
  if (state.eye > 0 || state.beacon > 0) busy = true;
  if (state.eye <= 0.05 && agStatus.firstChild.textContent !== "idle" && !state.packets.some((p) => p.hop.to === "ag" || p.hop.from === "ag")) {
    agStatus.firstChild.textContent = "idle";
    agStatus.lastChild.textContent = " queue 0";
    agStep.textContent = "step -/-";
  }

  // log panels scroll their new line into view
  for (const face of ["x", "y"]) {
    const g = logs[face];
    if (g.dataset.t === undefined) continue;
    const t = Math.min(1, Number(g.dataset.t) + dt / 0.45);
    g.dataset.t = String(t);
    const e = 1 - Math.pow(1 - t, 3);
    g.setAttribute("transform", `translate(0 ${(1.86 * (1 - e)).toFixed(3)})`);
    if (t >= 1) {
      delete g.dataset.t;
      g.removeAttribute("transform");
    } else busy = true;
  }

  // LEDs: the ones a record lit go out; a few idle ones flicker
  state.ledClock += dt;
  if (state.ledClock > 0.35 && state.touring) {
    state.ledClock = 0;
    blink(Math.random() < 0.5 ? "x" : "y", 1);
  }
  for (const face of ["x", "y"]) for (const led of leds[face]) if (led.dataset.until && now > Number(led.dataset.until)) (led.removeAttribute("data-on"), delete led.dataset.until);
  return busy;
}

let frame = 0;
let last = 0;
let visible = false;
let idleTimer = 0;
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
  last = now;
  trickle(dt);
  const flowing = drawPackets(dt);
  const n = D.steps.length;
  if (state.pending <= 0) {
    state.wait -= dt;
    if (state.wait <= 0) {
      if (state.touring) startStep((state.step + 1) % n);
      else if (state.chain && state.step < n - 1) startStep(state.step + 1);
      else state.chain = false;
      state.wait = state.step === n - 1 ? 2.2 : 0.7;
    }
  }
  const posing = drawPoses(dt, now);
  const busy = flowing || posing || state.touring || state.pending > 0 || state.chain;
  frame = visible && busy ? requestAnimationFrame(tick) : 0;
}
function run() {
  if (!frame && visible) {
    last = 0;
    frame = requestAnimationFrame(tick);
  }
}

function takeOver(node) {
  state.touring = false;
  state.chain = true;
  startChain(node);
  state.wait = state.step === D.steps.length - 1 ? 2.2 : 0.7;
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    if (still.matches) return;
    state.touring = true;
    state.chain = false;
    run();
  }, 14000);
  run();
}

new IntersectionObserver(
  (entries) => {
    visible = entries[entries.length - 1].isIntersecting;
    stage.classList.toggle("dc-still", !visible);
    if (visible) run();
  },
  { rootMargin: "120px 0px" },
).observe(stage);

svg.addEventListener("click", (event) => {
  const item = event.target.closest("[data-name]");
  if (!item) return;
  const prefix = item.dataset.name.split(".")[0].split(":")[0];
  const node = { pod: "dc", pm: "pm", crm: "crm", ag: "ag" }[prefix];
  if (!node) return;
  takeOver(node);
  stage.focus({ preventScroll: true });
});
stage.addEventListener("keydown", (event) => {
  const node = { 1: "crm", 2: "pm", 3: "ag", 4: "dc" }[event.key];
  if (!node) return;
  event.preventDefault();
  takeOver(node);
});

if (still.matches) {
  state.touring = false;
  for (let i = 0; i < D.steps.length; i++) startStep(i);
  state.label = "everything in sync";
  say();
} else {
  state.wait = 0.6;
  state.pending = 0;
  state.step = D.steps.length - 1;
}
say();
