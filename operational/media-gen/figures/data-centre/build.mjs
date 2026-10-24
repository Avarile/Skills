import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../../.agents/skills/anatomy/kit/iso-kit.mjs";
import * as G from "../../.agents/skills/anatomy/kit/lathe.mjs";
import { tubePieces, tubeSvg } from "../../.agents/skills/anatomy/kit/tube.mjs";
import * as A from "../../.agents/skills/anatomy/kit/audit.mjs";
import { kitScript } from "../../.agents/skills/anatomy/scripts/inline-kit.mjs";
import { LINKS, STEPS, CODE, SPEED, TRICKLE, recordsPerLoop } from "./model.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const THEME = process.argv.includes("--light") ? "light" : "dark";

const W = 600;
const H = 470;

// ── World plan (units ≈ px; x, y on the bench, z up) ──────────────────────────
const PLATE = { x: -145, y: -145, w: 290, d: 290, r: 14 };
const PLATE_H = 10;
const FOOT_H = 5;

const POD = { x: -75, y: -75, w: 84, d: 84, r: 1.2 };
const FX = POD.x + POD.w; // the +x face
const FY = POD.y + POD.d; // the +y face
const PLINTH_H = 10;
const CORE = k.insetPlan(POD, 6);
const BAY_Z0 = 12;
const BAY_Z1 = 140;
const ROOF_Z = 146;
const ROOF_H = 5;
const U = 6.2;

const CABLE_Z = 3.6;
const R_SPOKE = 1.35;
const R_MESH = 1.0;
// A data panel: a thin glass sheet of code on a carriage that rides over a rail.
const PANEL = { w: 23, h: 27, t: 0.9, z0: 9.8, car: { l: 12, w: 4.4, z0: 6.6 } };

const PMB = { x: -130, y: 50, w: 42, d: 80, r: 2 };
const PMB_H = 12;
const BOARD = { x0: -102, x1: -99, y0: 53, y1: 127, z0: 34, z1: 94 };
const COLS = [115, 90, 65]; // To do, Doing, Done (screen left to right)
const CARD = { w: 19, h: 8.6, t: 0.7 };

const CRB = { x: 78, y: -122, w: 56, d: 44, r: 3 };
const CRB_H = 10;
const AXLE = { y: -100, z: 42 };
const DRUM_R = 5.6;
const CARD_R = 19;
const CARD_X = [92, 122];

const AGB = { x: 62, y: 62, w: 54, d: 46, r: 3 };
const AGB_H = 14;
const ARM = { x: 92, y: 84 };

const P = k.fitProjection(
  [...k.boxCorners(PLATE, -PLATE_H - FOOT_H, 0), ...k.boxCorners(POD, 0, ROOF_Z + ROOF_H + 4)],
  W,
  H,
  { pad: 26, azimuth: 45, elevation: 30 },
);
const V = G.viewOf(P);
const KS = G.scaleOf(P);
const at = (p) => k.iso(p, P);
const S = (paths, style) => k.solidSvg(paths, style);
const Ln = (d, style) => k.lineSvg(d, style);
const Dots = (points, style) => k.dotsSvg(points, style);
const path3 = (points, closed = false) => k.pathOf(points.map(at), closed);
const f2 = (v) => Math.round(v * 100) / 100;
const BANDS = [0, 0.2, 0.42, 0.62]; // the kit's tone bands (lathe.mjs), for panels shaded live
const XF = G.frameOf([0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]);

// Face planes: +y faces map local (x, −z); +x faces map local (−y, −z).
const faceY = (y) => k.sideMatrix([0, y], 0, P, "left");
const faceX = (x) => k.sideMatrix([x, 0], 0, P, "right");
const rr = (u0, z0, u1, z1, r, steps = 4) => k.pathOf(k.roundedPlan({ x: u0, y: -z1, w: u1 - u0, d: z1 - z0, r }, steps), true);

// ── Recorder: every drawn item records its true shape ────────────────────────
const R = A.recorder(P);
const record = R.solid;
function put(name, ref, svg, shapes = [], { bias = 0, ...rest } = {}) {
  return R.put({ name, at: ref, bias, svg, shapes, piece: "bench", ...rest });
}
function box(name, plan, z, h, style = {}, { steps = 3, bevel = 0, extra = "", inner = "", bias = 0, attrs, owner } = {}) {
  const shape = record(A.slab(plan, z, h, { name, owner }, steps));
  const ref = [plan.x + plan.w / 2, plan.y + plan.d / 2, z + h / 2];
  put(name, ref, S(k.slabOf(plan, z, h, P, steps, bevel), { tone: "mid", ...style, inner }) + extra, [shape], { bias, attrs });
  return shape;
}
function prism(name, F, poly, s0, s1, style = {}, { extra = "", inner = "", bias = 0, attrs, owner } = {}) {
  const shape = record(A.prism(F, poly, s0, s1, { name, owner }));
  const cx = poly.reduce((a, p) => a + p[0], 0) / poly.length;
  const cy = poly.reduce((a, p) => a + p[1], 0) / poly.length;
  const centre = G.add3(G.add3(G.add3(F.o, G.mul3(F.a, (s0 + s1) / 2)), G.mul3(F.u, cx)), G.mul3(F.v, cy));
  put(name, centre, S(G.prismOf(F, poly, s0, s1, P), { tone: "mid", ...style, inner }) + extra, [shape], { bias, attrs });
  return shape;
}
function turned(name, F, profile, style = {}, { extra = "", inner = "", bias = 0, owner, attrs, bevel = 0 } = {}) {
  const shape = record(A.solid(F, profile, { name, owner }));
  const mid = (profile[0][0] + profile[profile.length - 1][0]) / 2;
  put(name, G.add3(F.o, G.mul3(F.a, mid)), S(G.solidOf(profile, F, P, { bevel }), { tone: "mid", ...style, inner }) + extra, [shape], { bias, attrs });
  return shape;
}
const disc = (name, F, s0, s1, r, style, options) => turned(name, F, [[s0, r], [s1, r]], style, options);
function cyl(name, cx, cy, r, z, h, style = {}, { extra = "", inner = "", bias = 0, steps = 40, bevel = 0, attrs, owner } = {}) {
  const shape = record(A.cylinder(cx, cy, r, z, h, { name, owner }));
  put(name, [cx, cy, z + h / 2], S(k.cylinder(cx, cy, r, z, h, P, steps, bevel), { tone: "mid", ...style, inner }) + extra, [shape], { bias, attrs });
  return shape;
}

// ── Back layer: plate, feet, halos ───────────────────────────────────────────
const back = [];
back.push(`<path class="iso-halo" d="${k.haloOf(PLATE, -PLATE_H - FOOT_H, PLATE_H, P)}"/>`);
const byDepth = (points) => [...points].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
for (const [x, y] of byDepth(k.corners(PLATE, 24))) {
  back.push(S(k.cylinder(x, y, 7.5, -PLATE_H - FOOT_H, 1.6, P, 32), { tone: "lo" }));
  back.push(S(k.cylinder(x, y, 5.8, -PLATE_H - FOOT_H + 1.6, FOOT_H - 1.6, P, 32), { tone: "mid" }));
}
back.push(S(k.slabOf(PLATE, -PLATE_H, PLATE_H, P, 10, 1.6), { tone: "mid", inner: Ln(k.sideSeam(PLATE, -4, P, 10), { tone: "faint" }) }));
back.push(Ln(k.planOutline(k.insetPlan(PLATE, 5), 0, P, 10), { tone: "lo" }));
const plateScrews = k.corners(PLATE, 10);
back.push(Ln(plateScrews.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
back.push(Dots(plateScrews.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
record(A.slab(PLATE, -PLATE_H, PLATE_H, { name: "stand.plate", ground: true }, 10));

// ruler strip along the near-left edge, ticks hanging from its inner edge
{
  const strip = { x: PLATE.x + 6, y: -118, w: 5.4, d: 150, r: 1 };
  back.push(S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const t = k.topTicks(strip.y + 4, strip.y + strip.d - 4, 4, 5, strip.x + strip.w, 0.6, [-1.8, -3.4], P, "y");
  back.push(Ln(t.minor, { tone: "lo" }), Ln(t.major, { tone: "mid" }));
  back.push(Dots([at([strip.x + 2.7, strip.y + 2, 0.6]), at([strip.x + 2.7, strip.y + strip.d - 2, 0.6])], { size: 0.45 }));
  record(A.slab(strip, 0, 0.6, { name: "stand.strip", ground: true }, 3));
}
// label plate between the agent spoke and the near edge
{
  const label = { x: -62, y: 100, w: 44, d: 13, r: 1.2 };
  back.push(S(k.slabOf(label, 0, 0.8, P, 3), { tone: "lo", crease: "none" }));
  back.push(Ln(k.planOutline(k.insetPlan(label, 1.6), 0.8, P, 3), { tone: "faint" }));
  back.push(Ln([30, 22, 26].map((w, i) => k.lineOnTop([label.x + 5, label.y + 3.6 + i * 2.9], [label.x + 5 + w, label.y + 3.6 + i * 2.9], 0.8, P)).join(""), { tone: "lo", free: true }));
  back.push(Dots([at([label.x + label.w - 3.4, label.y + 3.4, 0.8]), at([label.x + label.w - 3.4, label.y + label.d - 3.4, 0.8])], { size: 0.45 }));
  record(A.slab(label, 0, 0.8, { name: "stand.label", ground: true }, 3));
}
for (const [plan, h] of [[POD, 10], [PMB, 10], [CRB, 10], [AGB, 10]]) back.push(`<path class="iso-halo" d="${k.haloOf(k.insetPlan(plan, -2), 0, h, P)}"/>`);

// ── Sockets on faces, collected per host and drawn with it ───────────────────
const PORTS = {};
function port(id, point, normal) {
  PORTS[id] = { point, normal };
  return point;
}
const socketSvg = (point, normal, r) => {
  const [x, y, z] = point;
  const w = r * 2.6;
  if (normal[1] > 0.5) return `<g transform="${faceY(y)}">${Ln(rr(x - w, z - w * 0.8, x + w, z + w * 0.8, 0.8), { tone: "lo" })}</g>` + Dots([at([x - w - 1.4, y, z]), at([x + w + 1.4, y, z])], { size: 0.4, tone: "lo" });
  return `<g transform="${faceX(x)}">${Ln(rr(-y - w, z - w * 0.8, -y + w, z + w * 0.8, 0.8), { tone: "lo" })}</g>` + Dots([at([x, y + w + 1.4, z]), at([x, y - w - 1.4, z])], { size: 0.4, tone: "lo" });
};

// ── The data centre pod ──────────────────────────────────────────────────────
let clipCount = 0;
const clipId = () => `dc-clip-${clipCount++}`;

function codeLines(list, count, seed) {
  const out = [];
  for (let i = 0; i < count; i++) out.push(list[(seed * 3 + i * 5) % list.length]);
  return out;
}
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
function codeText(line, x, y, size) {
  const [head, ...rest] = line.split(" ");
  return `<text class="dc-code" x="${f2(x)}" y="${f2(y)}" font-size="${size}"><tspan class="dc-kw">${esc(head)}</tspan> ${esc(rest.join(" "))}</text>`;
}

// One window of scrolling code, drawn in face coordinates.
function codeWindow(u0, z0, u1, z1, lines, { seed = 0, log = null } = {}) {
  const id = clipId();
  const shape = rr(u0, z0, u1, z1, 0.7);
  const size = 1.32;
  const pitch = 1.86;
  const rows = Math.max(1, Math.floor((z1 - z0 - 0.6) / pitch));
  const x = u0 + 1.1;
  const top = -z1 + 0.5 + size;
  let content;
  if (log) {
    content = `<g data-log="${log}">${Array.from({ length: rows + 1 }, (_, i) => codeText(lines[i % lines.length], x, f2(top + (i - 1) * pitch), size)).join("")}</g>`;
  } else {
    const all = [...lines, ...lines];
    const dur = 2.2 * lines.length * (1 + (seed % 5) * 0.18);
    content = `<g class="dc-scroll" style="--dy:${f2(-lines.length * pitch)}px;--dur:${f2(dur)}s;--delay:${f2(-(seed * 1.7) % dur)}s">${all.map((line, i) => codeText(line, x, f2(top + i * pitch), size)).join("")}</g>`;
  }
  return `<clipPath id="${id}"><path d="${shape}"/></clipPath><path class="dc-glass" d="${shape}"/><g clip-path="url(#${id})">${content}<path class="dc-sheen" d="${rr(u0, z1 - (z1 - z0) * 0.42, u1, z1, 0.7)}"/></g>${Ln(shape, { tone: "lo" })}`;
}

const BAY_PATTERN = [2, 1, 1, 2, 1, 1, 2, 1, 2, 1, 1, 2, 1];
const BAY_SYSTEMS = ["dc", "crm", "pm", "dc", "ag", "crm", "dc", "pm", "ag", "dc", "crm", "pm", "ag"];
function bays(face) {
  const out = [];
  let z = BAY_Z0;
  BAY_PATTERN.forEach((units, index) => {
    const h = units * U;
    if (z + h > BAY_Z1 + 0.01) return;
    out.push({ z0: z, z1: z + h, units, sys: BAY_SYSTEMS[index], index });
    z += h + 0.7;
  });
  return out;
}

function pod() {
  const plinthPorts = [
    port("dc:pm", [-55, FY, CABLE_Z], [0, 1, 0]),
    port("dc:ag", [-12, FY, CABLE_Z], [0, 1, 0]),
    port("dc:crm", [FX, -55, CABLE_Z], [1, 0, 0]),
  ];
  const spare = [[[-33, FY, CABLE_Z], [0, 1, 0]], [[FX, -33, CABLE_Z], [1, 0, 0]], [[FX, -12, CABLE_Z], [1, 0, 0]]];
  const sockets = plinthPorts.map((p, i) => socketSvg(p, [[0, 1, 0], [0, 1, 0], [1, 0, 0]][i], R_SPOKE)).join("") + spare.map(([p, n]) => socketSvg(p, n, R_SPOKE)).join("");
  const nameplate = `<g transform="${faceY(FY)}">${Ln(rr(-71, 2.6, -59, 7.4, 0.5), { tone: "faint" })}</g>` + k.faceTextSvg(k.sideMatrix([-65, FY], 4.2, P, "left"), "DC-01", { size: 2.4, tone: "mid", anchor: "middle" });
  box("pod.plinth", POD, 0, PLINTH_H, { tone: "lo" }, { steps: 3, bevel: 0.6, extra: sockets + nameplate });
  spare.forEach(([p, n], i) => {
    const F = G.frameAlong(p, n);
    disc(`pod.cap${i}`, F, 0, 1.2, R_SPOKE * 1.8, { tone: "mid" });
  });

  box("pod.core", CORE, PLINTH_H, ROOF_Z - PLINTH_H, { tone: "lo" }, { steps: 2 });

  // corner posts with rack-unit holes
  const posts = [
    { x: FX - 6, y: FY - 6 },
    { x: POD.x, y: FY - 6 },
    { x: FX - 6, y: POD.y },
  ];
  posts.forEach((p, i) => {
    const plan = { x: p.x, y: p.y, w: 6, d: 6, r: 0.5 };
    const holes = [];
    for (let z = BAY_Z0 + 1.6; z < BAY_Z1; z += U / 3) {
      if (i !== 2) holes.push(at([p.x + 3, FY, z]));
      if (i !== 1) holes.push(at([FX, p.y + 3, z]));
    }
    box(`pod.post${i}`, plan, PLINTH_H, ROOF_Z - PLINTH_H, { tone: "mid" }, { steps: 2, bevel: 0.3, extra: Dots(holes, { size: 0.32, tone: "lo" }) });
  });

  // server bays: thin glass panels with code scrolling through them
  const faces = [
    { id: "y", plan: (z0, z1) => ({ x: POD.x + 6, y: CORE.y + CORE.d, w: POD.w - 12, d: FY - 0.6 - (CORE.y + CORE.d), r: 0.3 }), front: FY - 0.6, u0: POD.x + 6, u1: FX - 6, matrix: faceY, pt: (u, z) => [u, FY - 0.6, z] },
    { id: "x", plan: (z0, z1) => ({ x: CORE.x + CORE.w, y: POD.y + 6, w: FX - 0.6 - (CORE.x + CORE.w), d: POD.d - 12, r: 0.3 }), front: FX - 0.6, u0: -(FY - 6), u1: -(POD.y + 6), matrix: faceX, pt: (u, z) => [FX - 0.6, -u, z] },
  ];
  const BAY_LIST = bays();
  faces.forEach((face) => {
    BAY_LIST.forEach((bay, b) => {
      const { z0, z1, units, sys } = bay;
      const u0 = face.u0 + 0.4;
      const u1 = face.u1 - 0.4;
      const seed = b * 7 + (face.id === "x" ? 3 : 0);
      const isLog = b === BAY_LIST.length - 1;
      const lines = isLog ? ["-- ingest log --", ...codeLines(CODE.dc, 6, seed)] : codeLines(CODE[sys], 8, seed);
      const win = codeWindow(u0 + 8.4, z0 + 1.1, u1 - 4.2, z1 - 1.1, lines, { seed, log: isLog ? face.id : null });
      const ledZ = units > 1 ? [z1 - 2.6, z1 - 5.2] : [(z0 + z1) / 2];
      const leds = ledZ.map((z, i) => `<circle class="dc-led" data-led="${face.id}${b}${i}" cx="${f2(u0 + 5.2 + (units > 1 ? 0 : i * 1.6))}" cy="${f2(-z)}" r="0.55"/>`).join("");
      const handles = units > 1 ? Ln(rr(u0 + 3.6, z0 + 2, u0 + 4.6, z0 + 5.2, 0.5, 2), { tone: "lo" }) : "";
      const grip = units > 1 ? Ln(rr(u1 - 3.2, z0 + 2.2, u1 - 2.2, z1 - 2.2, 0.5, 2), { tone: "lo" }) : "";
      const svgFace = `<g transform="${face.matrix(face.front)}">${win}${leds}${handles}${grip}</g>`;
      const screws = Dots([face.pt(u0 + 1.6, (z0 + z1) / 2), face.pt(u1 - 1.2, (z0 + z1) / 2)].map(at), { size: 0.42, tone: "mid" });
      box(`pod.bay.${face.id}${b}`, face.plan(z0, z1), z0, z1 - z0, { tone: "mid" }, { steps: 2, bevel: 0.25, extra: svgFace + screws, attrs: ` data-bay="${face.id}${b}"` });
    });
    // blanking panel with vent slots above the top bay
    const topZ = BAY_LIST[BAY_LIST.length - 1].z1 + 0.7;
    if (ROOF_Z - topZ > 2.5) {
      const slots = Array.from({ length: 12 }, (_, i) => rr(face.u0 + 6 + i * 5.2, topZ + 1.2, face.u0 + 8.4 + i * 5.2, ROOF_Z - 1.2, 0.6, 2)).join("");
      box(`pod.blank.${face.id}`, face.plan(topZ, ROOF_Z), topZ, ROOF_Z - topZ, { tone: "mid" }, { steps: 2, extra: `<g transform="${face.matrix(face.front)}">${Ln(slots, { tone: "faint" })}</g>` });
    }
  });

  // roof with two fans, a cable brush and a beacon
  const fans = [[-52, -30], [-16, -52]];
  const roofLines = [];
  fans.forEach(([x, y]) => {
    roofLines.push(k.ring(x, y, 13, ROOF_Z + ROOF_H, P, 64), k.ring(x, y, 9.5, ROOF_Z + ROOF_H, P, 56), k.ring(x, y, 6, ROOF_Z + ROOF_H, P, 40));
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2 + 0.3;
      roofLines.push(k.lineOnTop([x + Math.cos(a) * 3, y + Math.sin(a) * 3], [x + Math.cos(a) * 13, y + Math.sin(a) * 13], ROOF_Z + ROOF_H, P));
    }
  });
  const brush = { x: -66, y: -4, w: 40, d: 5, r: 2.5 };
  const roofExtra =
    Ln(roofLines.join(""), { tone: "lo" }) +
    Ln(k.planOutline(brush, ROOF_Z + ROOF_H, P, 4) + k.planOutline(k.insetPlan(POD, 3.5), ROOF_Z + ROOF_H, P, 3), { tone: "faint" }) +
    Ln(Array.from({ length: 13 }, (_, i) => k.lineOnTop([brush.x + 3 + i * 2.8, brush.y + 0.8], [brush.x + 3 + i * 2.8, brush.y + brush.d - 0.8], ROOF_Z + ROOF_H, P)).join(""), { tone: "lo" }) +
    Dots(k.corners(POD, 2.4).map(([x, y]) => at([x, y, ROOF_Z + ROOF_H])), { size: 0.5 });
  box("pod.roof", POD, ROOF_Z, ROOF_H, { tone: "mid" }, { steps: 3, bevel: 1, extra: roofExtra });
  fans.forEach(([x, y], i) => cyl(`pod.fan${i}.hub`, x, y, 3, ROOF_Z + ROOF_H, 1.4, { tone: "mid" }, { steps: 24 }));
  cyl("pod.beacon.base", 0, 0, 2.6, ROOF_Z + ROOF_H, 1.2, { tone: "mid" }, { steps: 24 });
  cyl("pod.beacon", 0, 0, 1.8, ROOF_Z + ROOF_H + 1.2, 3, { tone: "hi" }, { steps: 24, attrs: ` data-part="beacon"` });
  return BAY_LIST.length;
}

// ── Project management: a T-card planning board ──────────────────────────────
const PM_CARDS = [
  { col: 0, row: 0 },
  { col: 0, row: 1 },
  { col: 0, row: 2 },
  { col: 1, row: 0, active: true },
  { col: 1, row: 1 },
  { col: 2, row: 0 },
  { col: 2, row: 1 },
];
const cardZ = (row) => BOARD.z1 - 9 - CARD.h - row * (CARD.h + 2.4);
function pmStation() {
  const ports = [
    port("pm:dc", [PMB.x + PMB.w, 68, CABLE_Z], [1, 0, 0]),
    port("pm:crm", [PMB.x + PMB.w, 58, CABLE_Z], [1, 0, 0]),
    port("pm:ag", [-109, PMB.y + PMB.d, CABLE_Z], [0, 1, 0]),
  ];
  const sockets = ports.map((p, i) => socketSvg(p, i === 2 ? [0, 1, 0] : [1, 0, 0], i === 0 ? R_SPOKE : R_MESH)).join("");
  const plate = { x: PMB.x + 4, y: PMB.y + PMB.d - 22, w: 14, d: 18, r: 1 };
  const topLines =
    Ln(k.planOutline(plate, PMB_H, P, 3), { tone: "faint" }) +
    Ln([10, 7, 9].map((w, i) => k.lineOnTop([plate.x + 3 + i * 3, plate.y + 2.5], [plate.x + 3 + i * 3, plate.y + 2.5 + w], PMB_H, P)).join(""), { tone: "lo", free: true });
  box("pm.base", PMB, 0, PMB_H, { tone: "mid" }, { steps: 4, bevel: 0.8, extra: sockets + topLines, inner: Ln(k.sideSeam(PMB, 3, P, 4), { tone: "faint" }) });

  for (const y of [56, 120]) {
    const plan = { x: BOARD.x0 - 4, y, w: 4, d: 4, r: 0.6 };
    box(`pm.post${y}`, plan, PMB_H + 2.4, BOARD.z1 + 4 - PMB_H - 2.4, { tone: "mid" }, { steps: 3, bevel: 0.3 });
    cyl(`pm.post${y}.cap`, BOARD.x0 - 2, y + 2, 2.6, BOARD.z1 + 4, 1.4, { tone: "mid" }, { steps: 20 });
    box(`pm.post${y}.shoe`, { x: BOARD.x0 - 6, y: y - 2, w: 8, d: 8, r: 1 }, PMB_H, 2.4, { tone: "lo" }, { steps: 3 });
  }

  // the board, its column rules and header icons
  const bplan = { x: BOARD.x0, y: BOARD.y0, w: BOARD.x1 - BOARD.x0, d: BOARD.y1 - BOARD.y0, r: 0.8 };
  const rules = [77.5, 102.5].map((y) => k.segment([BOARD.x1, y, BOARD.z0], [BOARD.x1, y, BOARD.z1 - 8], P)).join("");
  const frame = `<g transform="${faceX(BOARD.x1)}">${Ln(rr(-BOARD.y1 + 1.6, BOARD.z0 + 1.6, -BOARD.y0 - 1.6, BOARD.z1 - 1.6, 0.6), { tone: "faint" })}</g>`;
  box("pm.board", bplan, BOARD.z0, BOARD.z1 - BOARD.z0, { tone: "hi" }, { steps: 3, bevel: 0.5, extra: frame + Ln(rules, { tone: "lo" }) });
  const rail = { x: BOARD.x1, y: BOARD.y0 + 2, w: 1, d: BOARD.y1 - BOARD.y0 - 4, r: 0.3 };
  const icons = COLS.map((y, i) => {
    const c = [-y, BOARD.z1 - 4.6];
    if (i === 0) return `<circle class="iso-line" data-tone="mid" cx="${-y - 6}" cy="${-c[1]}" r="1.5"/>`;
    if (i === 1) return `<circle class="iso-line" data-tone="mid" cx="${-y - 6}" cy="${-c[1]}" r="1.5"/><path class="dc-ink" d="M${-y - 6} ${-c[1] - 1.5}A1.5 1.5 0 0 1 ${-y - 6} ${-c[1] + 1.5}Z"/>`;
    return `<path class="iso-line" data-tone="hi" data-free="" d="M${-y - 7.4} ${-c[1]}L${-y - 6.2} ${-c[1] + 1.2}L${-y - 4.4} ${-c[1] - 1.4}"/>`;
  }).join("");
  const headRules = COLS.map((y) => `<path class="iso-line" data-tone="lo" data-free="" d="M${-y - 3} ${-(BOARD.z1 - 4.6)}H${-y + 6}"/>`).join("");
  box("pm.rail", rail, BOARD.z1 - 8, 6.6, { tone: "mid" }, { steps: 2, extra: `<g transform="${faceX(BOARD.x1 + 1)}">${icons}${headRules}</g>` });

  // cards
  PM_CARDS.forEach((card, i) => {
    const y = COLS[card.col] - CARD.w / 2;
    const z = cardZ(card.row);
    const plan = { x: BOARD.x1, y, w: CARD.t, d: CARD.w, r: 0.3 };
    const fx = BOARD.x1 + CARD.t;
    const lines = `<g transform="${faceX(fx)}"><path class="iso-line" data-tone="lo" data-free="" d="M${-y - CARD.w + 2.4} ${-(z + CARD.h - 2.4)}H${-y - 5}M${-y - CARD.w + 2.4} ${-(z + CARD.h - 4.6)}H${-y - 8}"/><circle class="dc-ink" cx="${-y - 2.6}" cy="${-(z + 2.4)}" r="1.1"/></g>`;
    const pin = Dots([at([fx, y + CARD.w / 2, z + CARD.h - 1.2])], { size: 0.55, tone: "hi" });
    if (card.active) {
      const shape = record(A.slab(plan, z, CARD.h, { name: "pm.card.active" }, 2));
      R.put({ name: "pm.card.active", at: [BOARD.x1 + 0.3, y + CARD.w / 2, z + CARD.h / 2], bias: 0.4, piece: "bench", shapes: [shape], svg: `<g data-part="pm-card">${S(k.slabOf(plan, z, CARD.h, P, 2, 0.2), { tone: "hi", lit: true })}${lines}${pin}</g>` });
    } else {
      box(`pm.card${i}`, plan, z, CARD.h, { tone: "hi" }, { steps: 2, bevel: 0.2, extra: lines + pin, bias: 0.2 });
    }
  });

  // marker tray with two markers and an eraser
  const tray = { x: BOARD.x1, y: 57, w: 5, d: 66, r: 0.8 };
  box("pm.tray", tray, BOARD.z0 - 3, 3, { tone: "mid" }, { steps: 3, bevel: 0.3, inner: Ln(k.sideSeam(tray, BOARD.z0 - 1.6, P, 3), { tone: "faint" }) });
  [[68, 12], [84, 13]].forEach(([y, len], i) => {
    const F = G.frameAlong([BOARD.x1 + 2.5, y, BOARD.z0 + 1.1], [0, 1, 0]);
    turned(`pm.marker${i}`, F, [[0, 0.6], [1.2, 1.1, 1], [len - 3, 1.1], [len - 3, 1.25], [len, 1.25]], { tone: i ? "hi" : "mid" });
  });
  box("pm.eraser", { x: BOARD.x1 + 0.6, y: 103, w: 3.8, d: 12, r: 0.8 }, BOARD.z0, 3.2, { tone: "lo" }, { steps: 3, bevel: 0.3 });
}

// ── CRM: a rotary card file ──────────────────────────────────────────────────
const CRM_CARDS = 44;
const ACTIVE_CARD = 4;
function crmStation() {
  const ports = [
    port("crm:dc", [90, CRB.y + CRB.d, CABLE_Z], [0, 1, 0]),
    port("crm:ag", [CRB.x + CRB.w, -98, CABLE_Z], [1, 0, 0]),
    port("crm:pm", [CRB.x, -104, CABLE_Z], [-1, 0, 0]),
  ];
  const sockets = socketSvg(ports[0], [0, 1, 0], R_SPOKE) + socketSvg(ports[1], [1, 0, 0], R_MESH);
  const well = { x: CRB.x + 6, y: CRB.y + 5, w: CRB.w - 12, d: CRB.d - 10, r: 2 };
  box("crm.base", CRB, 0, CRB_H, { tone: "mid" }, { steps: 4, bevel: 0.8, extra: sockets + Ln(k.planOutline(well, CRB_H, P, 4), { tone: "faint" }), inner: Ln(k.sideSeam(CRB, 3, P, 4), { tone: "faint" }) });

  // side plates
  const sideRing = [];
  for (let i = 0; i <= 12; i++) {
    const a = (i / 12) * Math.PI;
    sideRing.push([AXLE.y + Math.cos(a) * 9, AXLE.z + Math.sin(a) * 9]);
  }
  const sidePoly = [[AXLE.y - 13, CRB_H], [AXLE.y + 13, CRB_H], ...sideRing];
  for (const [x0, x1, nm] of [[85, 88.4, "far"], [125.6, 129, "near"]]) {
    const extra = nm === "near" ? Dots([at([x1, AXLE.y - 9, CRB_H + 3]), at([x1, AXLE.y + 9, CRB_H + 3])], { size: 0.45 }) : "";
    prism(`crm.side.${nm}`, XF, sidePoly, x0, x1, { tone: "mid" }, { extra });
  }
  // drum and hubs
  const AF = G.frameOf([0, AXLE.y, AXLE.z], [1, 0, 0], [0, 1, 0], [0, 0, 1]);
  disc("crm.drum", AF, 91.2, 122.8, DRUM_R, { tone: "lo" });
  disc("crm.hub.far", AF, 88.4, 91.2, DRUM_R + 2.4, { tone: "mid" }, { bias: 0.2 });
  disc("crm.hub.near", AF, 122.8, 125.6, DRUM_R + 2.4, { tone: "mid" }, { bias: 0.2 });
  // knob on the near plate
  const KF = G.frameAlong([129, AXLE.y, AXLE.z], [1, 0, 0]);
  disc("crm.knob.neck", KF, 0, 1.6, 2.4, { tone: "mid" });
  disc("crm.knob", KF, 1.6, 5.6, 5, { tone: "hi" }, { extra: k.fadedSvg(G.ribsOf(KF, 1.6, 5.6, 5, 36, P, { fade: [0.1, 0.55], seams: true }), { tone: "lo" }) });

  // the cards, fanned round the drum
  for (let i = 0; i < CRM_CARDS; i++) {
    const th = (i / CRM_CARDS) * Math.PI * 2 + 0.11;
    const e = [Math.sin(th), Math.cos(th)];
    const t = [Math.cos(th), -Math.sin(th)];
    const half = 0.24;
    const r0 = DRUM_R;
    const r1 = CARD_R;
    const c = (r, s) => [e[0] * r + t[0] * s, e[1] * r + t[1] * s];
    const poly = [c(r0, -half), c(r1, -half), c(r1, half), c(r0, half)];
    const F = G.frameOf([0, AXLE.y, AXLE.z], [1, 0, 0], [0, 1, 0], [0, 0, 1]);
    const tab = i % 3 === 1;
    const name = i === ACTIVE_CARD ? "crm.card.active" : `crm.card${i}`;
    const tabX = 94 + ((i * 7) % 20);
    const shapes = [record(A.prism(F, poly, CARD_X[0], CARD_X[1], { name }))];
    let svg = S(G.prismOf(F, poly, CARD_X[0], CARD_X[1], P), { tone: "hi", lit: i === ACTIVE_CARD });
    const normal = [0, t[0], t[1]];
    if (G.dot3(normal, V) > 0.25) {
      const onFace = (x, r) => [x, AXLE.y + e[0] * r + t[0] * half, AXLE.z + e[1] * r + t[1] * half];
      svg += Ln([[r1 - 2.2, 6], [r1 - 4, 12]].map(([r, cut]) => path3([onFace(CARD_X[0] + 3, r), onFace(CARD_X[1] - cut, r)])).join(""), { tone: "lo", free: true });
    }
    if (tab) {
      const tpoly = [c(r1, -half), c(r1 + 2.2, -half), c(r1 + 2.2, half), c(r1, half)];
      shapes.push(record(A.prism(F, tpoly, tabX, tabX + 6, { name: `${name}.tab` })));
      svg += S(G.prismOf(F, tpoly, tabX, tabX + 6, P), { tone: "mid" });
    }
    const centre = [107, AXLE.y + e[0] * (r0 + r1) / 2, AXLE.z + e[1] * (r0 + r1) / 2];
    R.put({ name, at: centre, piece: "bench", shapes, svg: i === ACTIVE_CARD ? `<g data-part="crm-card">${svg}</g>` : svg, lift: e });
  }
}

// ── Agentic platform: a controller with a three-joint arm ────────────────────
const J = G.unit3([1, 1, 0]);
const D = G.unit3([-1, 1, 0]);
const Z = [0, 0, 1];
const SH = [ARM.x, ARM.y, AGB_H + 4 + 12 + 8.4];
const inPlane = (o, d, z) => G.add3(G.add3(o, G.mul3(D, d)), G.mul3(Z, z));
const EL = inPlane(SH, 36 * Math.cos((66 * Math.PI) / 180), 36 * Math.sin((66 * Math.PI) / 180));
const WR = inPlane(EL, 31 * Math.cos((-68 * Math.PI) / 180), 31 * Math.sin((-68 * Math.PI) / 180));
function agStation() {
  const ports = [
    port("ag:pm", [90, AGB.y + AGB.d, CABLE_Z], [0, 1, 0]),
    port("ag:crm", [AGB.x + AGB.w, 92, CABLE_Z], [1, 0, 0]),
    port("ag:dc", [AGB.x, 84, CABLE_Z], [-1, 0, 0]),
  ];
  const sockets = socketSvg(ports[0], [0, 1, 0], R_MESH) + socketSvg(ports[1], [1, 0, 0], R_MESH);
  const fy = AGB.y + AGB.d;
  const fx = AGB.x + AGB.w;
  // status screen on the +y face, vents on the +x face
  const scr = { u0: 97, u1: 113, z0: 5, z1: 11.4 };
  const id = clipId();
  const scrPath = rr(scr.u0, scr.z0, scr.u1, scr.z1, 0.6);
  const screen = `<g transform="${faceY(fy)}"><clipPath id="${id}"><path d="${scrPath}"/></clipPath><path class="dc-glass" d="${scrPath}"/><g clip-path="url(#${id})"><text class="dc-code" data-part="ag-status" x="${scr.u0 + 0.9}" y="${-(scr.z1 - 2.2)}" font-size="1.32"><tspan class="dc-kw">idle</tspan> queue 0</text><text class="dc-code" data-part="ag-step" x="${scr.u0 + 0.9}" y="${-(scr.z1 - 4.2)}" font-size="1.32">step -/-</text></g>${Ln(scrPath, { tone: "lo" })}</g>`;
  const leds = Dots([68, 71, 74].map((x) => at([x, fy, 10.4])), { size: 0.55, tone: "lo" });
  const vents = `<g transform="${faceX(fx)}">${Ln(Array.from({ length: 6 }, (_, i) => rr(-104 + i * 3.4, 6.4, -102.6 + i * 3.4, 11.4, 0.6, 2)).join("") + Array.from({ length: 4 }, (_, i) => rr(-80 + i * 3.4, 6.4, -78.6 + i * 3.4, 11.4, 0.6, 2)).join(""), { tone: "faint" })}</g>`;
  box("ag.base", AGB, 0, AGB_H, { tone: "mid" }, { steps: 4, bevel: 0.8, extra: sockets + screen + leds + vents, inner: Ln(k.sideSeam(AGB, 3, P, 4), { tone: "faint" }), attrs: ` data-part="ag-base"` });

  // emergency stop on the top, front-right corner
  cyl("ag.estop.collar", 108, 100, 4.2, AGB_H, 1.6, { tone: "lo" }, { steps: 28 });
  const EF = G.frameAlong([108, 100, AGB_H + 1.6], [0, 0, 1]);
  turned("ag.estop", EF, [[0, 2.2], [1.6, 2.2], [1.6, 3.6], [2.6, 3.6, 1], [3.4, 2.8, 1], [3.7, 0]], { tone: "hi" });
  // engraved plate on the top
  const tp = { x: 66, y: 66, w: 14, d: 10, r: 1 };
  const topExtra = Ln(k.planOutline(tp, AGB_H, P, 3), { tone: "faint" }) + Ln([8, 6].map((w, i) => k.lineOnTop([tp.x + 3, tp.y + 3.4 + i * 3], [tp.x + 3 + w, tp.y + 3.4 + i * 3], AGB_H, P)).join(""), { tone: "lo", free: true });
  put("ag.topplate", [tp.x + 7, tp.y + 5, AGB_H], topExtra, [record(A.slab(tp, AGB_H, 0.1, { name: "ag.topplate" }, 3))], { bias: 0.05 });

  // inbox tray of task cards under the gripper
  const tipAt = G.add3(WR, [0, 0, -9.6 - 15.6]);
  const inbox = { x: tipAt[0] - 8, y: tipAt[1] - 6.5, w: 16, d: 13, r: 1.2 };
  box("ag.inbox", inbox, AGB_H, 1.2, { tone: "lo" }, { steps: 3 });
  for (const [side, y] of [[0, inbox.y], [1, inbox.y + inbox.d - 1]]) box(`ag.inbox.wall${side}`, { x: inbox.x, y, w: inbox.w, d: 1, r: 0.3 }, AGB_H + 1.2, 2.2, { tone: "mid" }, { steps: 2 });
  [0, 1, 2].forEach((i) => box(`ag.inbox.card${i}`, { x: inbox.x + 1.6, y: inbox.y + 1.6 + i * 0.1, w: inbox.w - 3.2, d: inbox.d - 3.2, r: 0.4 }, AGB_H + 1.2 + i * 0.5, 0.5, { tone: "hi" }, { steps: 2, extra: i === 2 ? Ln([9, 6].map((w, j) => k.lineOnTop([inbox.x + 3.4, inbox.y + 4 + j * 2.4], [inbox.x + 3.4 + w, inbox.y + 4 + j * 2.4], AGB_H + 2.7, P)).join(""), { tone: "lo", free: true }) : "" }));

  // turntable, waist and shoulder
  const TF = G.frameAlong([ARM.x, ARM.y, AGB_H], [0, 0, 1]);
  const ticks = k.radialTicks(ARM.x, ARM.y, 15, 60, 5, AGB_H + 4, [1, 2], P);
  turned("ag.turntable", TF, [[0, 16], [2.6, 16], [2.6, 15.2], [4, 15.2]], { tone: "mid" }, { extra: Ln(ticks.minor, { tone: "lo" }) + Ln(ticks.major, { tone: "mid" }) });
  turned("ag.waist", G.frameAlong([ARM.x, ARM.y, AGB_H + 4], [0, 0, 1]), [[0, 10], [3, 10], [3, 9.2], [9, 9.2], [9, 8.4], [12, 8.4]], { tone: "hi" }, { inner: Ln(k.sideArc(ARM.x, ARM.y, 9.2, AGB_H + 4 + 6, P, 40), { tone: "faint" }) });

  // links: stadium plates in the arm plane, joints as discs along J
  const AF = (o) => G.frameOf(o, J, D, Z);
  const rel = (p, o) => [G.dot3(G.sub3(p, o), D), G.dot3(G.sub3(p, o), Z)];
  const link = (name, a, b, ra, rb, half, tone) => {
    const poly = G.hullOf([...Array.from({ length: 24 }, (_, i) => [Math.cos((i / 24) * Math.PI * 2) * ra, Math.sin((i / 24) * Math.PI * 2) * ra]), ...Array.from({ length: 24 }, (_, i) => { const [d, z] = rel(b, a); return [d + Math.cos((i / 24) * Math.PI * 2) * rb, z + Math.sin((i / 24) * Math.PI * 2) * rb]; })]);
    prism(name, AF(a), poly, -half, half, { tone }, { owner: "arm" });
  };
  const cap = (c, s, r) => {
    const F = G.frameAlong(c, J);
    return Ln(G.circleOf(F, s, r * 0.62, P), { tone: "lo" }) + Dots(G.dotsOf(F, s, r * 0.8, 6, P, { all: true, phase: 0.3 }), { size: 0.42, tone: "mid" }) + Dots([at(G.add3(c, G.mul3(J, s)))], { size: 0.7, tone: "hi" });
  };
  // each joint is a pair of caps on the faces of the links it joins, so no link runs through a cap
  const joint = (name, c, inner, outer, r) => {
    disc(`${name}.back`, G.frameAlong(c, J), -outer, -inner, r, { tone: "mid" }, { owner: "arm" });
    disc(name, G.frameAlong(c, J), inner, outer, r, { tone: "mid" }, { owner: "arm", extra: cap(c, outer, r) });
  };
  joint("ag.shoulder", SH, 4, 6.4, 8.4);
  link("ag.upper", SH, EL, 6, 4.8, 4, "hi");
  joint("ag.elbow", EL, 4, 5.4, 6.4);
  link("ag.fore", EL, WR, 4.8, 3.8, 3.3, "hi");
  joint("ag.wrist", WR, 3.3, 4.4, 4.6);
  // eye on the forearm, facing the viewer
  const eyeAt = G.add3(G.lerp3(EL, WR, 0.42), G.mul3(J, 3.3));
  disc("ag.eye.ring", G.frameAlong(eyeAt, J), 0, 0.8, 2.6, { tone: "mid" }, { owner: "arm", bias: 0.4 });
  disc("ag.eye", G.frameAlong(G.add3(eyeAt, G.mul3(J, 0.8)), J), 0, 0.8, 1.7, { tone: "hi" }, { owner: "arm", bias: 0.5, attrs: ` data-part="ag-eye"` });
  // wrist flange, gripper palm and two fingers
  const DF = G.frameAlong(WR, [0, 0, -1]);
  turned("ag.flange", DF, [[3.8, 3.2], [8.4, 3.2], [8.4, 4.4], [9.6, 4.4]], { tone: "mid" }, { owner: "arm" });
  const palmTop = G.add3(WR, G.mul3(Z, -9.6));
  prism("ag.palm", AF(palmTop), [[-6.4, 0], [6.4, 0], [6.4, -5.6], [-6.4, -5.6]], -3.6, 3.6, { tone: "mid" }, { owner: "arm", extra: Dots([-4.2, 4.2].map((d) => at(G.add3(inPlane(palmTop, d, -2.8), G.mul3(J, 3.6)))), { size: 0.45 }) });
  const fingerPoly = (side) => [[side * 3.6, -5.6], [side * 5.4, -5.6], [side * 5.4, -15], [side * 4.4, -15.6], [side * 3.6, -14.6]];
  for (const side of [-1, 1]) {
    const shape = record(A.prism(AF(palmTop), fingerPoly(side), -2.6, 2.6, { name: `ag.finger${side}`, owner: "arm" }));
    R.put({ name: `ag.finger${side}`, at: inPlane(palmTop, side * 4.5, -10), bias: 0.2, piece: "bench", shapes: [shape], svg: `<g data-finger="${side}">${S(G.prismOf(AF(palmTop), fingerPoly(side), -2.6, 2.6, P), { tone: "hi" })}</g>` });
  }
}

// ── Cables ──────────────────────────────────────────────────────────────────
const ROUTES = {};
const SHELL = 2.6;
const BOOT = 3.4;
function cable(name, from, to, via, r, { clamps = [], tone = "mid", bend = 10 } = {}) {
  const a = PORTS[from];
  const b = PORTS[to];
  const points = [a.point, G.add3(a.point, G.mul3(a.normal, 8)), ...via, G.add3(b.point, G.mul3(b.normal, 8)), b.point];
  const route = G.fillet(points, bend, 10, { P, tube: r });
  const total = G.pathLength(route);
  const clampAt = clamps.map((f) => f * total);
  const gaps = [[0, SHELL + BOOT], ...clampAt.map((s) => [s - 1, s + 1]), [total - SHELL - BOOT, total]];
  R.route(name, route, r, { gaps, limp: true, rims: [r * 1.9, r * 1.9], piece: "bench", touch: clampAt.map((_, i) => `${name}.clamp${i}*`) });
  const pieces = tubePieces(route, r, P, { maxLength: 7, spacing: Math.max(0.6, Math.min(1.6, r)), gaps });
  pieces.forEach((piece, index) => {
    put(`${name}:${index}`, piece.mid, tubeSvg(piece, { tone }), [A.tube(piece.points, piece.radii)], { bias: 0.02 });
  });
  // Ghost panels: a panel's true shape at every rail chunk it can ride over. The depth solver
  // orders them with everything else; the live page draws a panel in its ghost's slot.
  const ends = [SHELL + BOOT + PANEL.w / 2 + 2, total - SHELL - BOOT - PANEL.w / 2 - 2];
  pieces.forEach((piece, index) => {
    const mid = (piece.from + piece.to) / 2;
    if (piece.to < ends[0] || piece.from > ends[1]) return;
    const c = G.pointAlong(route, Math.min(ends[1], Math.max(ends[0], mid)));
    const t = G.tangentAlong(route, mid);
    const u = G.unit3([t[0], t[1], 0]);
    const n = [-u[1], u[0], 0];
    const glass = A.orientedBox([c[0], c[1], PANEL.z0 + PANEL.h / 2], [u, n, Z], [PANEL.w / 2, PANEL.t / 2, PANEL.h / 2], { name: `${name}~${index}` });
    const car = A.orientedBox([c[0], c[1], (PANEL.car.z0 + PANEL.z0) / 2], [u, n, Z], [PANEL.car.l / 2, PANEL.car.w / 2, (PANEL.z0 - PANEL.car.z0) / 2], { name: `${name}~${index}.car` });
    R.put({ name: `${name}~${index}`, at: [c[0], c[1], PANEL.z0 + PANEL.h / 2], piece: "bench", shapes: [glass, car], svg: "", ghost: true, route: name, from: piece.from, to: piece.to });
  });
  [0, 1].forEach((end) => {
    const tip = end ? route[route.length - 1] : route[0];
    const tangent = end ? G.mul3(G.tangentAlong(route, total), -1) : G.tangentAlong(route, 0);
    const F = G.frameAlong(tip, tangent);
    turned(`${name}.shell${end}`, F, [[0, r * 1.9], [SHELL, r * 1.9]], { tone: "mid" }, { owner: name, bias: 0.1 });
    turned(`${name}.boot${end}`, F, [[SHELL, r * 1.55], [SHELL + BOOT, r * 1.12]], { tone: "lo" }, { owner: name, bias: 0.1 });
  });
  clampAt.forEach((s, i) => {
    const c = G.pointAlong(route, s);
    const tangent = G.tangentAlong(route, s);
    const F = G.frameAlong(c, tangent);
    const cr = r + 0.9;
    turned(`${name}.clamp${i}`, F, [[-1, cr], [1, cr]], { tone: "mid" }, { owner: name, bias: 0.1 });
    const side = G.unit3([-tangent[1], tangent[0], 0]);
    const foot = { x: c[0] - 2.2, y: c[1] - 2.2, w: 4.4, d: 4.4, r: 0.6 };
    const fz = c[2] - cr;
    box(`${name}.clamp${i}.foot`, foot, 0, fz + 0.4, { tone: "lo" }, { steps: 2, owner: name, extra: Dots([at(G.add3([c[0], c[1], 0], G.mul3(side, 3.4)))], { size: 0.45 }) });
  });
  ROUTES[name] = { total: f2(total), points: route.map((p) => p.map(f2)), top: f2(CABLE_Z + r), ends: [f2(SHELL + BOOT + PANEL.w / 2 + 2), f2(total - SHELL - BOOT - PANEL.w / 2 - 2)] };
}

// ── Build everything ─────────────────────────────────────────────────────────
const bayCount = pod();
pmStation();
crmStation();
agStation();

const Zc = CABLE_Z;
cable("pm-dc", "pm:dc", "dc:pm", [[-55, 68, Zc]], R_SPOKE, { clamps: [0.5] });
cable("crm-dc", "crm:dc", "dc:crm", [[90, -55, Zc]], R_SPOKE, { clamps: [0.55] });
cable("ag-dc", "ag:dc", "dc:ag", [[-12, 84, Zc]], R_SPOKE, { clamps: [0.3, 0.72] });
cable("pm-ag", "pm:ag", "ag:pm", [[-109, 136, Zc], [90, 136, Zc]], R_MESH, { clamps: [0.22, 0.5, 0.78] });
cable("crm-ag", "crm:ag", "ag:crm", [[136, -98, Zc], [136, 92, Zc]], R_MESH, { clamps: [0.25, 0.55, 0.8] });
cable("pm-crm", "pm:crm", "crm:pm", [[-81, 58, Zc], [-81, -104, Zc]], R_MESH, { clamps: [0.2, 0.45, 0.8] });

const ghostPair = (x, y) => (x.ghost && y.ghost) || A.sameRun(x, y);
A.settle(R, P, { skip: ghostPair });
// The planning card lifts off the board and travels over its neighbours, so it is drawn after every card.
{
  const active = R.items.find((item) => item.name === "pm.card.active");
  const last = Math.max(...R.items.filter((item) => item.name.startsWith("pm.card")).map((item) => item.key));
  if (active.key < last) active.key = last + 0.001;
}
R.items.sort((a, b) => a.key - b.key);
// Each rail chunk is followed by an empty slot; a travelling panel is drawn in the slot of the chunk it rides over.
const groups = R.items.map((item) => (item.ghost ? `<g data-slot="${item.route}" data-a="${f2(item.from)}" data-b="${f2(item.to)}"></g>` : `<g class="it" data-name="${item.name}"${item.attrs ?? ""}>${item.svg}</g>`));

const LABEL =
  "A small data centre on a bench plate: a server pod in the middle, its two visible faces racked with thin glass panels that scroll live code, fans and a beacon on its roof. Around it stand a T-card planning board for project management, a rotary card file for the CRM, and a robot arm on its controller for the agentic platform. Six guide rails join all four to each other, and thin glass data panels, code scrolling on them, ride the rails from system to system.";
const svg = k.figureSvg({ width: W, height: H, label: LABEL, body: [...back, `<g class="dc-items">${groups.join("")}</g>`] });

// ── Live data ───────────────────────────────────────────────────────────────
const DATA = {
  P,
  speed: SPEED,
  routes: ROUTES,
  steps: STEPS,
  links: LINKS,
  cols: COLS,
  cardZ: [0, 1, 2].map(cardZ),
  pmActive: { col: 1, row: 0 },
  crmLift: [0, Math.sin((ACTIVE_CARD / CRM_CARDS) * Math.PI * 2 + 0.11), Math.cos((ACTIVE_CARD / CRM_CARDS) * Math.PI * 2 + 0.11)],
  armD: D,
  bays: bayCount,
  perLoop: recordsPerLoop,
  trickle: TRICKLE,
  panel: PANEL,
  light: G.lightOf(P),
  bands: BANDS,
  view: V,
  code: CODE,
};
const CSS = readFileSync(join(HERE, "data-centre.css"), "utf8");
const LIVE = readFileSync(join(HERE, "live.js"), "utf8").replace("__DATA__", JSON.stringify(DATA));

const body =
  `<style>${CSS}</style>` +
  k.plateHtml({
    fig: "Fig 1",
    title: "Data centre and its systems",
    hint: "Click a system to send its data",
    readout: "deal won · 0 records synced",
    keys: [
      { mark: "lit", label: "A data panel carrying one step of the chain, its records scrolling on the glass" },
      { mark: "raised", label: "Smaller panels: single change records trickling between chains" },
      { mark: "edge", label: "Six guide rails: three spokes to the pod, three links between the systems" },
    ],
    caption: `The data centre sits in the middle and every system keeps its records there, but the systems also trade data directly. Each exchange is a thin glass panel with its records scrolling on it: it rises out of the sender, rides a single-track rail and sinks into the receiver. Follow one won deal: the CRM sends the deal to the pod and a project to the planning board; the board sends its six tasks to the pod and one to the agent; the agent pulls 24 rows of account history from the pod, then sends a note to the CRM, a done card to the board and its run log to the pod. One pass moves ${recordsPerLoop} records. Between chains each rail keeps trickling single change records, and the top panel on each face of the pod logs every chain record as it lands.`,
    body: `<div class="iso-stage dc-stage" tabindex="0" role="group" aria-label="Data centre figure. Press 1 for the CRM, 2 for project management, 3 for the agentic platform, to start the chain of data at that system.">${svg}<span class="dc-sr" role="status" aria-live="polite" data-status></span></div>`,
  });

const page = k.pageHtml({ title: "Data centre", theme: THEME, body, script: kitScript() + LIVE, width: 680 });
const name = THEME === "light" ? "data-centre-light.html" : "data-centre.html";
writeFileSync(join(HERE, name), page);
console.log("wrote", name, `${(page.length / 1024).toFixed(0)} KB`, `${R.items.length} items`, `scale ${KS.toFixed(3)}`);

A.auditOrExit(R, P, {});
