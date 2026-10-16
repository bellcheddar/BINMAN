const pptxgen = require("pptxgenjs");
const fs = require("fs");

// Depot, the palette BINMAN's own interface uses: concrete, ink and sodium amber.
const THEME = {
  name: "Depot",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "15171A",   // ink
    lt1: "FFFFFF",
    dk2: "61655F",   // muted
    lt2: "E9EAE5",   // concrete
    accent1: "A64708", // sodium amber
    accent2: "2C6D60", // green, a result that held
    accent3: "1C244B", // navy
    accent4: "A33A2A", // red, a result that did not
    accent5: "79610D",
    accent6: "3A3E37",
    hlink: "A64708",
    folHlink: "61655F",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.3 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Marc C. Deller";
pres.title = "BINMAN: how it works";
pres.subject = "An atlas of molecular glues already in the PDB";

const C = pres.SchemeColor;
const W = 13.3, H = 7.5, M = 0.55;

/* ---------------------------------------------------------------- layouts */

pres.defineSlideMaster({
  title: "DARK",
  background: { color: THEME.colors.dk1 },
  objects: [
    { text: { text: "BINMAN", options: {
      x: M, y: H - 0.5, w: 3, h: 0.3, fontSize: 10, color: THEME.colors.dk2,
      charSpacing: 2, isTextBox: true, margin: 0 } } },
  ],
});

pres.defineSlideMaster({
  title: "LIGHT",
  background: { color: "FFFFFF" },
  objects: [
    { text: { text: "BINMAN  ·  binman.mdeller.com", options: {
      x: M, y: H - 0.46, w: 5, h: 0.3, fontSize: 9.5, color: THEME.colors.dk2,
      charSpacing: 1, isTextBox: true, margin: 0 } } },
  ],
  slideNumber: { x: W - 0.85, y: H - 0.46, w: 0.3, h: 0.3, fontSize: 9.5,
                 color: THEME.colors.dk2, align: "right" },
});

/* ------------------------------------------------------------- components */

// The motif: a filled rounded square carrying a stage number or a module letter.
function chip(slide, label, x, y, color) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w: 0.52, h: 0.52, rectRadius: 0.1,
    fill: { color: color || THEME.colors.accent1 }, line: { color: color || THEME.colors.accent1 },
    objectName: `chip-${label}`,
  });
  slide.addText(label, {
    x, y, w: 0.52, h: 0.52, align: "center", valign: "middle",
    fontSize: 18, bold: true, color: "FFFFFF", isTextBox: true, margin: 0,
  });
}

function heading(slide, number, text, color) {
  chip(slide, number, M, 0.54, color);
  slide.addText(text, {
    x: M + 0.72, y: 0.50, w: W - M * 2 - 0.72, h: 0.6,
    fontSize: 32, bold: true, color: C.text1, fontFace: THEME.headFontFace,
    isTextBox: true, margin: 0, valign: "middle",
  });
}

function strapline(slide, text, y) {
  slide.addText(text, {
    x: M, y: y === undefined ? 1.24 : y, w: W - M * 2, h: 0.42,
    fontSize: 14.5, italic: true, color: THEME.colors.accent1,
    isTextBox: true, margin: 0, valign: "middle",
  });
}

// A tinted card. No edge stripes: a background tint and a heading only.
function card(slide, opts) {
  const { x, y, w, h, title, lines, fill, titleColor, name } = opts;
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.04,
    fill: { color: fill || THEME.colors.lt2 }, line: { color: fill || THEME.colors.lt2 },
    objectName: name || "card",
  });
  if (title) {
    slide.addText(title, {
      x: x + 0.26, y: y + 0.18, w: w - 0.52, h: 0.26,
      fontSize: 11, bold: true, color: titleColor || THEME.colors.accent1,
      charSpacing: 1.4, isTextBox: true, margin: 0,
    });
  }
  const runs = lines.map((l, i) => ({
    text: typeof l === "string" ? l : l.text,
    options: Object.assign(
      { bullet: false, breakLine: i < lines.length - 1, paraSpaceAfter: 5 },
      typeof l === "string" ? {} : (l.options || {})
    ),
  }));
  slide.addText(runs, {
    x: x + 0.26, y: y + (title ? 0.52 : 0.2), w: w - 0.52, h: h - (title ? 0.72 : 0.4),
    fontSize: 12.5, color: C.text1, isTextBox: true, margin: 0, valign: "top",
  });
}

function stat(slide, value, label, x, y, w, color) {
  slide.addText(value, {
    x, y, w, h: 0.56, fontSize: 30, bold: true, color: color || THEME.colors.accent1,
    fontFace: THEME.headFontFace, isTextBox: true, margin: 0, valign: "middle",
  });
  slide.addText(label, {
    x, y: y + 0.54, w, h: 0.5, fontSize: 10.5, color: THEME.colors.dk2,
    isTextBox: true, margin: 0, valign: "top",
  });
}

function prose(slide, runs, x, y, w, h, size) {
  slide.addText(runs, {
    x, y, w, h, fontSize: size || 13.5, color: C.text1,
    isTextBox: true, margin: 0, valign: "top", lineSpacingMultiple: 1.18,
  });
}

const B = (t) => ({ text: t, options: { bold: true } });
const T = (t) => ({ text: t });
const BR = { text: "", options: { breakLine: true } };

/* ----------------------------------------------------------- 1 · overview */

pres.addSection({ title: "Overview" });
let s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Overview" });

s.addText("BINMAN", {
  x: M, y: 0.52, w: 6, h: 0.62, fontSize: 40, bold: true, color: C.text1,
  fontFace: THEME.headFontFace, isTextBox: true, margin: 0, valign: "middle",
});
s.addText("Blind-spot INventory of Molecular Adhesives and Neosubstrates", {
  x: M, y: 1.10, w: 8.5, h: 0.3, fontSize: 13, color: THEME.colors.accent1,
  italic: true, isTextBox: true, margin: 0,
});
s.addText([
  T("Marc C. Deller, D.Phil."), BR,
  T("binman.mdeller.com"), BR,
  T("github.com/bellcheddar/BINMAN"),
], {
  x: W - M - 3.4, y: 0.54, w: 3.4, h: 0.9, fontSize: 11, color: THEME.colors.dk2,
  align: "right", isTextBox: true, margin: 0,
});

prose(s, [
  T("Molecular glues have been sitting in the PDB for thirty years, deposited by crystallographers who were solving something else and had no reason to label the ligand as one. BINMAN finds them by "),
  B("geometry rather than annotation"),
  T(": every non-polymer entity that buries meaningful surface against two or more protein chains at once. "),
  B("130,391"), T(" entries catalogued, "), B("285,996"), T(" bridges measured, "),
  B("15,804"), T(" that no curated glue database lists."),
], M, 1.42, W - M * 2, 1.02, 13.5);

s.addImage({ path: "/tmp/binman_deck/workflow.png", x: M, y: 2.50, w: W - M * 2, h: 3.90 });

s.addText("Four stages, left to right, then the four modules that read the result. The trained layer underneath is one small language model that does the text work and none of the arithmetic.", {
  x: M, y: 6.54, w: W - M * 2, h: 0.34, fontSize: 11, color: THEME.colors.dk2,
  italic: true, isTextBox: true, margin: 0,
});
s.addNotes("BINMAN is an empirical atlas. Nothing here is predicted structure: every bridge is measured in a deposited crystal or cryo-EM structure. The four stages run left to right and each writes a manifest, so the whole thing is resumable.");

/* -------------------------------------------------------------- 2 · stages */

pres.addSection({ title: "How it is built" });

// Stage 1
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How it is built" });
heading(s, "1", "Acquisition");
strapline(s, "You cannot search the PDB for “molecular glue”. There is no such field.");

prose(s, [
  B("The science."), T(" A glue is only recognisable once you have measured it, so the catalogue cannot be filtered by annotation. The only honest starting set is every entry that "), T("could"), T(" hold one: at least two polymer chains for a ligand to bridge, and at least one non-polymer entity to do the bridging."), BR, BR,
  B("How the code does it."), T(" "), { text: "pipeline/catalogue.py", options: { fontFace: "Courier New", fontSize: 11.5 } },
  T(" asks the RCSB Search API that question and pages through the answer. Each entry is sorted into one of four tiers by how likely it is to matter, then "),
  { text: "pipeline/rcsb.py", options: { fontFace: "Courier New", fontSize: 11.5 } },
  T(" downloads its biological assembly and caches it on disk, so the download happens once and never again."),
], M, 1.78, 7.5, 2.45);

card(s, {
  x: M, y: 4.36, w: 7.5, h: 1.55, title: "WHY A NON-CODER SHOULD CARE",
  lines: ["Every stage appends one line per item to a manifest file saying what happened to it. Kill the run halfway and it resumes from the manifest rather than starting again. It also means nothing fails silently: a failure is a recorded row, not an absence."],
});

card(s, {
  x: 8.45, y: 1.84, w: W - M - 8.45, h: 2.30, title: "SOFTWARE",
  lines: [
    { text: "httpx", options: { bold: true } },
    "HTTP with connection pooling",
    { text: "tenacity", options: { bold: true } },
    "retry with backoff, so a flaky API does not lose a run",
    { text: "RCSB Search + File APIs", options: { bold: true } },
    "the public PDB services",
  ],
});

stat(s, "130,391", "entries catalogued", 8.45, 4.34, 2.1);
stat(s, "0", "failed", 10.9, 4.34, 1.8, THEME.colors.accent2);
card(s, {
  x: 8.45, y: 5.36, w: W - M - 8.45, h: 1.16, title: "TIERS",
  lines: ["tier 1 · 3,871      tier 2 · 34,222", "tier 3 · 17,375    tier 4 · 74,923"],
});
s.addNotes("Tier 1 is the curated glue set, tier 4 is single-entity entries kept as the negative class for the triage model. Nothing is thrown away.");

// Stage 2
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How it is built" });
heading(s, "2", "Geometry");
strapline(s, "A glue is a geometric fact, not a label. So measure the fact.");

prose(s, [
  B("The science."), T(" A ligand that glues two proteins together buries surface against both of them at once. That is measurable and it needs no opinion: "),
  B("ΔSASA = SASA(ligand) + SASA(chain) − SASA(the two together)"),
  T(", computed separately against each chain."), BR, BR,
  B("Bridging balance"), T(" is the smaller buried area over the larger. Near 1.0 the ligand sits squarely between the two chains. Near 0 it is bound to one and brushing the other."), BR, BR,
  B("How the code does it."), T(" gemmi parses the assembly into chains and ligand instances, FreeSASA does the surface arithmetic, PLIP types the contacts at both half-interfaces. Symmetry copies are excluded, so a crystal contact cannot pose as a complex."),
], M, 1.78, 7.5, 3.5);

card(s, {
  x: M, y: 5.22, w: 7.5, h: 1.30, title: "THE RULE THAT KEEPS IT HONEST",
  lines: ["Crystallisation furniture — PEG, buffers, cryoprotectants — is classified, not deleted, so the counts reconcile. Every cutoff lives in config/thresholds.toml and never in the Python."],
});

card(s, {
  x: 8.45, y: 1.84, w: W - M - 8.45, h: 2.30, title: "SOFTWARE",
  lines: [
    { text: "gemmi", options: { bold: true } },
    "mmCIF and assembly parsing",
    { text: "FreeSASA", options: { bold: true } },
    "solvent-accessible surface, Lee-Richards",
    { text: "PLIP", options: { bold: true } },
    "interaction typing at each half-interface",
  ],
});
stat(s, "285,996", "bridges measured", 8.45, 4.34, 2.4);
stat(s, "19", "entries failed", 8.45, 5.44, 2.4, THEME.colors.accent4);
stat(s, "27,605", "glue candidates", 10.95, 4.34, 1.83, THEME.colors.accent2);
stat(s, "30,149", "distinct ligands\nclassified", 10.88, 5.44, 1.9);
s.addNotes("The 19 failures are recorded with their reason. Spec rule: a failure is data, not an exception.");

// Stage 3
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How it is built" });
heading(s, "3", "Scan and triage");
strapline(s, "Finding the glue is a third of the problem.");

prose(s, [
  B("The science."), T(" A degrader needs three things the glue itself does not supply: a "),
  B("degron"), T(" on the target that the ligase can read, a "), B("ligase"),
  T(" you can actually put a ligand on, and a "), B("lysine"),
  T(" the E2 can reach once the complex forms. Each is scored on its own and against its own published dataset."),
], M, 1.78, W - M * 2, 1.0);

const row = [
  {
    t: "DEGRON SCAN", x: M,
    lines: ["AlphaFold models from AFDB, DSSP for secondary structure, then the geometry of a β-hairpin with an exposed glycine at the tip — the shape CRBN reads.",
            { text: "21,717 candidates over 8,983 proteins", options: { bold: true } },
            { text: "7,452 C2H2 zinc fingers, scored one finger at a time", options: { bold: true } }],
  },
  {
    t: "E3 TRIAGE", x: M + 4.15,
    lines: ["fpocket finds and scores the druggable pocket on every human E3, combined with structural coverage, expression selectivity and family.",
            { text: "650 ligases ranked", options: { bold: true } },
            { text: "638 carry a pocket score", options: { bold: true } }],
  },
  {
    t: "DEGRADABILITY", x: M + 8.3,
    lines: ["Surface lysine accessibility and the Cβ–Cβ distance from the chosen binding site, against a reach window fitted on real ternary complexes.",
            { text: "1,650 lysines scored", options: { bold: true } },
            { text: "window fitted on 43 complexes", options: { bold: true } }],
  },
];
row.forEach((r) => card(s, { x: r.x, y: 2.76, w: 3.85, h: 2.44, title: r.t, lines: r.lines }));

card(s, {
  x: M, y: 5.44, w: W - M * 2, h: 0.78, fill: THEME.colors.lt2,
  lines: [{ text: "570 degron scans and 12 ligases failed. Both counts are on the About page, because a stage that hides its failures is a stage nobody can audit.", options: { italic: true } }],
});
s.addNotes("Each of these three becomes one of the four modules later. The fourth, Glue Atlas, comes straight out of stage 2.");

// Stage 4
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How it is built" });
heading(s, "4", "Model");
strapline(s, "The model does the text work and never produces a number.");

prose(s, [
  B("The science."), T(" An atlas is useless if the only way in is SQL. But a language model that invents a binding affinity is worse than no model, so BINMAN's has one hard constraint: "),
  B("every number on every page is computed in Python"), T(". The model only ever writes a "), T("query"), T("; the database answers it."), BR, BR,
  B("How it was trained."), T(" Qwen2.5-3B-Instruct at 4-bit, one LoRA adapter of rank 8 over 32 layers, trained with MLX on an Apple M2 Ultra. The training corpus is generated "),
  B("from the atlas itself"), T(" and then validated by the app's own query parser: anything the parser rejected was dropped, so the corpus carries zero label noise by construction."),
], M, 1.78, 7.5, 3.1);

card(s, {
  x: M, y: 5.00, w: 7.5, h: 1.42, title: "ONE ADAPTER, THREE HEADS",
  lines: [
    { text: "A · query — your question becomes a query object, which the parser then checks", options: {} },
    { text: "B · triage — evidence class on 27,590 bridge rows at build time", options: {} },
    { text: "C · abstain — answerable or not, and what is missing when it is not", options: {} },
  ],
});

card(s, {
  x: 8.45, y: 1.84, w: W - M - 8.45, h: 1.85, title: "SOFTWARE",
  lines: [
    { text: "mlx-lm", options: { bold: true } },
    "LoRA fine-tuning on Apple silicon",
    { text: "PEFT + HF Spaces", options: { bold: true } },
    "served on ZeroGPU",
  ],
});
stat(s, "0.9336", "Task B macro F1,\nheld-out components", 8.45, 3.90, 2.3, THEME.colors.accent2);
card(s, {
  x: 8.45, y: 4.86, w: W - M - 8.45, h: 1.58, title: "TODAY",
  lines: [{ text: "Task C specificity 0.0000 → 1.0000. The abstain head had learned that the answer is always no, because every training row was a refusal. Balancing the corpus fixed it.", options: {} }],
});
s.addNotes("The round that fixed the abstain head finished this morning: 15,806 iterations, four hours on the Studio. Specificity is now 1.0 on twelve questions the atlas demonstrably answers.");

/* ------------------------------------------------------------- 6 · modules */

pres.addSection({ title: "What it answers" });

// Glue Atlas
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What it answers" });
heading(s, "A", "Glue Atlas", THEME.colors.accent3);
strapline(s, "Which deposited ligands already bridge two proteins, and which chemotypes nobody has written up.");

stat(s, "285,996", "bridges", M, 1.76, 2.4);
stat(s, "15,804", "listed by no glue database", M + 2.6, 1.76, 2.6);
stat(s, "82", "novel series", M + 5.5, 1.76, 2.0, THEME.colors.accent2);
stat(s, "0.8781", "recall vs 320 curated glues\n(floor 0.85)", M + 8.0, 1.76, 2.8, THEME.colors.accent2);

prose(s, [
  B("The finding that matters most."), T(" Clustered on the protein pair they bridge rather than on their chemistry, the novel bridges resolve into "),
  B("82 protein pairs carrying three or more distinct ligands each"),
  T(" — a medicinal chemistry series somebody is already running, visible in the PDB and absent from every curated database. The largest is 14-3-3σ with p65: 34 ligands over 34 entries."), BR, BR,
  T("As a control it recovered the "), B("RAS(ON) tri-complex glues"),
  T(" unprompted, and a real cereblon degrader series on the Helios zinc fingers that no database lists."),
], M, 2.94, 7.5, 2.36);

card(s, {
  x: M, y: 5.38, w: 7.5, h: 1.58, title: "EVERY SERIES CARRIES TWO MEASUREMENTS, NOT A VERDICT",
  lines: [
    { text: "Ligand share — how much of the interface the ligand buries, against how much the two chains bury on each other.", options: {} },
    { text: "Interface retained — what survives in a structure holding both proteins and none of that series' ligands.", options: {} },
  ],
});

card(s, {
  x: 8.45, y: 3.0, w: W - M - 8.45, h: 2.62, title: "WORKED EXAMPLE",
  lines: [
    { text: "9OHL · ligand A1CBE", options: { bold: true } },
    "METTL5, an rRNA methyltransferase, and TRMT112, the subunit it needs to be active. One small molecule between them, 1.29 Å, deposited June 2025, called a glue by nobody.",
    { text: "442 and 581 Å² against the two chains", options: { bold: true } },
    { text: "balance 0.761 · 79% of the ligand buried", options: { bold: true } },
  ],
});
s.addNotes("Each series row carries two measurements rather than a verdict: ligand share, and how much of the interface survives in a structure without that chemistry.");

// Degron Scan
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What it answers" });
heading(s, "B", "Degron Scan", THEME.colors.accent3);
strapline(s, "Which human proteins carry the shape cereblon reads?");

prose(s, [
  B("The science."), T(" CRBN neosubstrate recognition is a β-hairpin presenting a glycine at its tip. The scan looks for that geometry across the AlphaFold human proteome, then asks whether geometry actually predicts degradation."), BR, BR,
  B("It does not, and sequence does."), T(" On a gene-disjoint split, the sequence model scores "),
  B("AUC 0.6334"), T(" against geometry's "), B("0.5564"), T(". Combining them adds 0.0014, which is inside the split-to-split noise. That is reported, not buried."), BR, BR,
  B("The grammar transfers across chemistry."), T(" Trained on pomalidomide alone, the model is above chance on "),
  B("24 of 29 analogues"), T(" of a published screen, gene-disjoint, mean AUC "), B("0.779"), T(", permutation p = 0.0005."),
], M, 1.76, 7.5, 3.5);

card(s, {
  x: 8.45, y: 1.76, w: W - M - 8.45, h: 1.9, title: "SOFTWARE",
  lines: [
    { text: "AlphaFold DB", options: { bold: true } }, "predicted structures, with pLDDT as a confidence filter",
    { text: "DSSP", options: { bold: true } }, "secondary structure assignment",
  ],
});
stat(s, "21,717", "degron candidates", 8.45, 3.9, 2.3);
stat(s, "7,452", "zinc fingers scored", 10.95, 3.9, 1.83);

card(s, {
  x: 8.45, y: 5.0, w: W - M - 8.45, h: 1.32, fill: "F6E3D3", title: "WHERE IT MISSES",
  lines: [{ text: "Sensitivity 0.6562 against a 0.70 floor, specificity 0.3528 against 0.60. Both miss, both are diagnosed in FINDINGS.md.", options: {} }],
});
s.addNotes("The scan fires on 65% of matched negatives because a C2H2 zinc finger IS a short hairpin with an exposed turn. That is the diagnosis, and it is why sequence beats geometry.");

// E3 Triage
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What it answers" });
heading(s, "C", "E3 Triage", THEME.colors.accent3);
strapline(s, "There are about 650 human E3 ligases and the field uses four.");

prose(s, [
  B("The science."), T(" Cereblon and VHL dominate because they were ligandable first, not because they are the best. The question a new company has to answer early is which of the other 646 are worth a ligand campaign."), BR, BR,
  B("How the code answers it."), T(" fpocket runs over every human E3 structure and scores the best pocket for druggability and volume. That is combined with how well the ligase is structurally covered, how selectively it is expressed across tissues, and its family, into a single rank with every component visible."),
], M, 1.76, 7.5, 2.6);

card(s, {
  x: M, y: 4.5, w: 7.5, h: 1.82, title: "THE FIVE EXPLOITATION CLASSES",
  lines: [
    { text: "clinically validated · chemically validated · covalent handle only · ligandable unproven · orphan", options: { bold: true } },
    "The classification is derived from published ligand evidence, not assigned by opinion, and it is what the ranking is sorted within.",
  ],
});

card(s, {
  x: 8.45, y: 1.76, w: W - M - 8.45, h: 1.52, title: "SOFTWARE",
  lines: [
    { text: "fpocket", options: { bold: true } }, "pocket detection and druggability scoring",
  ],
});
stat(s, "650", "ligases ranked", 8.45, 3.5, 2.2);
stat(s, "638", "with a pocket score", 10.95, 3.5, 1.83);
card(s, {
  x: 8.45, y: 4.6, w: W - M - 8.45, h: 1.72, title: "TOP OF THE RANKING",
  lines: [
    { text: "DCAF15 · rank 1", options: { bold: true } },
    "pocket score 0.988, chemically validated",
    { text: "DCAF8L1 · rank 2", options: { bold: true } },
    "pocket score 0.860, ligandable unproven",
  ],
});
s.addNotes("The ranking is of the repertoire, not of fit to a particular target. Pairing a ligase with a substrate is what the Lens graph does.");

// Degradability
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What it answers" });
heading(s, "D", "Degradability", THEME.colors.accent3);
strapline(s, "A ternary complex is not degradation. The E2 still has to reach a lysine.");

prose(s, [
  B("The science."), T(" Once the glue has brought ligase and target together, ubiquitin has to be transferred onto a lysine on the target. Whether a usable lysine exists, and whether it sits within reach of the E2, is the last thing that can kill a programme and the first thing nobody checks."), BR, BR,
  B("How the code answers it."), T(" Surface lysines are scored on NZ relative accessibility and on Cβ–Cβ distance from the chosen binding site, against a reach window fitted on 43 real induced ternary complexes rather than on an assumption."),
], M, 1.76, 7.5, 2.7);

card(s, {
  x: M, y: 4.62, w: 7.5, h: 1.7, fill: "F6E3D3", title: "THE RESULT A GLUE COMPANY MOST NEEDS",
  lines: [
    { text: "Lysine exposure does not predict ubiquitylation.", options: { bold: true } },
    "Scored against 309,297 lysines that were assayed and found unmodified — not lysines nobody had annotated — exposure reads 0.502. Chance. Do not build a selection criterion on it.",
  ],
});

card(s, {
  x: 8.45, y: 1.76, w: W - M - 8.45, h: 2.3, title: "WHY IT FAILS, MEASURED",
  lines: [
    "Reach from the ligand site scores 0.42 to 0.48, because the ligand site is where a substrate is recruited and not where ubiquitin is transferred.",
    "The two published labellings disagree on 41% of lysines, which is most of the apparent signal in the easier version of this test.",
  ],
});
stat(s, "0.502", "exposure AUC\nagainst assayed negatives", 8.45, 4.3, 2.6, THEME.colors.accent4);
stat(s, "43", "ternary complexes\nin the fit", 11.1, 4.3, 1.68);
s.addNotes("This is the negative result I would most want a collaborator to know before designing a target-selection funnel.");

/* -------------------------------------------------- 10 · what did not work */

pres.addSection({ title: "What did not work" });
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What did not work" });
heading(s, "!", "What did not work", THEME.colors.accent4);
strapline(s, "Four things the project tried, measured, and could not make work. All four are in the repository.");

const failures = [
  {
    t: "GEOMETRY ALONE DOES NOT PREDICT DEGRADATION",
    lines: ["The specified geometry score is anti-predictive on the assayed set, and a quarter of it was never persisted to the database. Sequence carries the signal. Combining the two adds 0.0014, inside the noise between splits."],
  },
  {
    t: "COUNTING APO STRUCTURES CANNOT SEPARATE INDUCED FROM PRE-EXISTING",
    lines: ["Three framings tried, each defeated by a cofactor: haemoglobin α+β has no ligand-free structure at all, because haem is a ligand, so the most obligate pair in the set looked induced. Recorded as not done rather than approximated."],
  },
  {
    t: "LIGAND SHARE IS A MEASUREMENT, NOT A CLASSIFIER",
    lines: ["A genuine CRBN degrader and a colchicine-site passenger both read 0.47. And on one structure it misleads outright: DNA gyrase read 0.97 on 30 Å² of chain contact, and the same two chains bury 3,284 Å² in another entry."],
  },
  {
    t: "ONE VALIDATION METRIC CANNOT PASS",
    lines: ["Seven of fifteen realistically phrased questions are scored against numeric thresholds the question never states, so the ceiling is 0.533 against a floor of 0.80. The floor was not moved: a floor chosen to be reachable is not a check."],
  },
];
failures.forEach((f, i) => {
  const x = M + (i % 2) * 6.33;
  const y = 1.84 + Math.floor(i / 2) * 2.02;
  card(s, { x, y, w: 5.90, h: 1.80, title: f.t, lines: f.lines,
            fill: THEME.colors.lt2, titleColor: THEME.colors.accent4, name: `fail-${i}` });
});

s.addText("Two training approaches were also abandoned: DPO collapsed the policy twice, and asking the abstain head before the query head refused all twelve of BINMAN’s own worked examples.", {
  x: M, y: 6.10, w: W - M * 2, h: 0.4, fontSize: 11.5, italic: true,
  color: THEME.colors.dk2, isTextBox: true, margin: 0,
});
s.addNotes("DECISIONS.md carries 92 entries, each with the alternatives considered and the condition under which it should be reversed. The failures are not footnotes: they are the part a collaborator can act on.");

/* ------------------------------------------------------------- 11 · wrap-up */

pres.addSection({ title: "Working together" });
s = pres.addSlide({ masterName: "DARK", sectionTitle: "Working together" });

s.addText("Where this could go", {
  x: M, y: 0.52, w: 9, h: 0.68, fontSize: 34, bold: true, color: "FFFFFF",
  fontFace: THEME.headFontFace, isTextBox: true, margin: 0, valign: "middle",
});
s.addText("Everything below is already built, measured and public.", {
  x: M, y: 1.2, w: 9, h: 0.34, fontSize: 14, italic: true,
  color: THEME.colors.accent1, isTextBox: true, margin: 0,
});

const closing = [
  { t: "WHAT YOU CAN USE TODAY", lines: [
    "The whole atlas is one SQLite file, 195 MB, that opens in any tool you already have.",
    "A live interface at binman.mdeller.com, the code on GitHub, the adapter on Hugging Face.",
  ] },
  { t: "WHERE TO START READING", lines: [
    "README — what it is and what it found.",
    "FINDINGS.md — every number with its method and its n, including the ones that miss.",
    "DECISIONS.md — 92 entries, each with how to reverse it.",
  ] },
  { t: "THE OBVIOUS NEXT MOVES", lines: [
    "Pick a series from the 82 and put it in front of a crystallographer.",
    "Pair ligases to targets, which the ranking deliberately does not do.",
    "Superpose glue-free structures to settle induced versus pre-existing properly.",
  ] },
];
closing.forEach((c, i) => {
  const x = M + i * 4.15;
  s.addShape(pres.ShapeType.roundRect, {
    x, y: 1.78, w: 3.85, h: 2.18, rectRadius: 0.04,
    fill: { color: "20242A" }, line: { color: "20242A" }, objectName: `close-${i}`,
  });
  s.addText(c.t, {
    x: x + 0.26, y: 1.96, w: 3.33, h: 0.5, fontSize: 11, bold: true,
    color: THEME.colors.accent1, charSpacing: 1.4, isTextBox: true, margin: 0,
  });
  s.addText(c.lines.map((l, j) => ({
    text: l, options: { bullet: false, breakLine: j < c.lines.length - 1, paraSpaceAfter: 7 },
  })), {
    x: x + 0.26, y: 2.50, w: 3.33, h: 1.38, fontSize: 12, color: "D8DAD4",
    isTextBox: true, margin: 0, valign: "top",
  });
});

s.addText("The two rules the whole project is built on", {
  x: M, y: 4.32, w: 11, h: 0.32, fontSize: 11, bold: true, color: THEME.colors.accent1,
  charSpacing: 1.4, isTextBox: true, margin: 0,
});
s.addText([
  B("1 · "), T("Every module is validated against independently curated published datasets, never against controls written for this project."), BR,
  B("2 · "), T("The language model never computes, estimates or reports a number. Every figure you have seen was computed deterministically in Python."),
], {
  x: M, y: 4.70, w: 12.2, h: 1.18, fontSize: 13, color: "E9EAE5",
  isTextBox: true, margin: 0, lineSpacingMultiple: 1.2,
});

s.addText("Marc C. Deller, D.Phil.  ·  marc@marcdeller.com  ·  binman.mdeller.com  ·  github.com/bellcheddar/BINMAN", {
  x: M, y: 6.40, w: 12, h: 0.34, fontSize: 11.5, color: "9AA096",
  isTextBox: true, margin: 0,
});
s.addNotes("Offer: a half-day walkthrough of the code with the atlas open, so the numbers can be checked live rather than taken on trust.");

pres.writeFile({ fileName: "/tmp/binman_deck/BINMAN-how-it-works.pptx" }).then(async () => {
  const { applyTheme } = require("/Users/dellboy/.claude/skills/synced/23e24ebf-dbf5-47f1-965c-06fa65267e7b_29ef5fdb-4564-4200-89d5-648deef9692b/pptx/scripts/apply_theme.js");
  await applyTheme("/tmp/binman_deck/BINMAN-how-it-works.pptx", THEME);
  console.log("written and themed");
});
