// The traffic model behind the figure: four systems, six links, and the chain of
// events a won deal sets off. Every packet the page draws, every line the data
// centre logs and every number in the readout comes from here.

export const NODES = {
  dc: "Data centre",
  pm: "Project management",
  crm: "CRM",
  ag: "Agentic platform",
};

// Each link is one physical cable, named "a-b" in drawing order.
export const LINKS = [
  { id: "pm-dc", a: "pm", b: "dc", carries: "projects and tasks" },
  { id: "crm-dc", a: "crm", b: "dc", carries: "contacts, deals and notes" },
  { id: "ag-dc", a: "ag", b: "dc", carries: "context in, results out" },
  { id: "pm-ag", a: "pm", b: "ag", carries: "assignments and status" },
  { id: "crm-ag", a: "crm", b: "ag", carries: "notes and follow-ups" },
  { id: "pm-crm", a: "pm", b: "crm", carries: "won deals into projects" },
];

export const linkOf = (from, to) => {
  const link = LINKS.find((l) => (l.a === from && l.b === to) || (l.a === to && l.b === from));
  return { id: link.id, reverse: link.a !== from };
};

// Data panels ride the rails at this many world units per second.
export const SPEED = 85;

// The chain a won deal sets off. Each step's hops leave together; the next step
// starts once every hop of this one has arrived.
export const STEPS = [
  {
    at: "crm",
    label: "deal won",
    hops: [
      { from: "crm", to: "dc", records: 3, log: "UPSERT crm.deals #4821 stage=won 48000" },
      { from: "crm", to: "pm", records: 1, log: "POST /projects deal=4821 'Acme rollout'" },
    ],
  },
  {
    at: "pm",
    label: "project opened",
    hops: [
      { from: "pm", to: "dc", records: 6, log: "INSERT pm.tasks x6 project=P-112" },
      { from: "pm", to: "ag", records: 1, log: "ASSIGN T-881 kickoff brief -> agent" },
    ],
  },
  {
    at: "dc",
    label: "agent reads context",
    hops: [{ from: "dc", to: "ag", records: 24, log: "SELECT history acct=acme -> 24 rows" }],
  },
  {
    at: "ag",
    label: "agent acts",
    hops: [
      { from: "ag", to: "crm", records: 1, log: "NOTE contact#311 kickoff Tue 10:00" },
      { from: "ag", to: "pm", records: 1, log: "PATCH T-881 status=done" },
      { from: "ag", to: "dc", records: 2, log: "INSERT ag.runs #5520 tokens=8412" },
    ],
  },
  {
    at: "pm",
    label: "everything in sync",
    hops: [
      { from: "pm", to: "dc", records: 1, log: "UPDATE pm.tasks T-881 done" },
      { from: "crm", to: "dc", records: 1, log: "INSERT crm.notes #9930" },
    ],
  },
];

// Between chains every link keeps trickling single change records (CDC rows),
// one packet every `every` seconds on average, in either direction.
export const TRICKLE = { every: 4.2, records: 1 };

// Clicking a system starts the chain at the first step that system begins.
export const startFor = (node) => Math.max(0, STEPS.findIndex((step) => step.at === node));

export const recordsPerLoop = STEPS.reduce((sum, step) => sum + step.hops.reduce((s, hop) => s + hop.records, 0), 0);

// Ambient log text for the data centre's panels, by system.
export const CODE = {
  dc: [
    "wal flush lsn=0/3A9F1C8",
    "replica lag 4ms ok",
    "vacuum crm.deals 0 dead",
    "index pm_tasks_due rebuilt",
    "snapshot s3://dc/0421 ok",
    "checksum 9f1c..e2 verified",
    "conn pool 38/120",
    "SELECT count(*) FROM events",
  ],
  crm: [
    "UPSERT contacts id=311",
    "deal 4821 stage -> won",
    "sync email thread 7792",
    "merge dup contact 902",
    "pipeline q3 value 1.2M",
    "INSERT crm.notes #9929",
    "owner=avery region=apac",
    "webhook deal.updated 200",
  ],
  pm: [
    "INSERT pm.tasks T-879",
    "cycle 42 burn 61%",
    "T-874 blocked_by T-870",
    "PATCH T-866 status=done",
    "module 'billing' 9/14",
    "due 2026-10-28 T-881",
    "estimate pts=5 T-882",
    "board sync 3 columns",
  ],
  ag: [
    "agent.run(ctx) step 3/7",
    "tool crm.find_contact ok",
    "plan: brief -> book -> log",
    "embed 24 docs 1536d",
    "tool pm.update_task 200",
    "tokens in 6120 out 2292",
    "eval guard pass",
    "queue depth 2",
  ],
};
