/*
 * panel-rust-analysis skill_version: 2.3 -- must match SKILL.md's
 * skill_version and the version recorded in memory. If this number looks
 * out of sync with either, this file has likely reverted to a stale
 * snapshot -- see SKILL.md's persistence-warning section before trusting
 * anything below.
 *
 * Canonical build-deck template for panel-rust-analysis.
 *
 * House style established across AN26_0703 / AN26_0110 / AN26_0109 batches.
 * This file has reverted to a stale version at least FOUR times across past
 * sessions despite being "fixed" and reportedly verified each time. If
 * you're about to build a deck, `cat` this file first rather than trusting
 * memory or a summary of a past conversation -- and if it looks stale
 * (Georgia font, per-set slides present, no summary slide, no divider
 * lines, IMG_H other than 1.6), STOP and re-consult conversation history
 * before proceeding, because that means this file reverted again.
 *
 * If you establish a new style change with the user, write it into THIS
 * file, then verify with ALL of: (1) a fresh `view` of the file, (2) an
 * independent-directory copy (`cp -r` to /tmp, with a couple seconds'
 * delay) + `diff` against your staged version, (3) ideally a rendered
 * test slide checked visually. A same-session re-read is not sufficient
 * evidence -- this exact file has passed same-session verification and
 * still reverted by the next session multiple times.
 *
 * Structure (as of skill_version 2.2): grouped slides only (all sets as
 * columns on one slide -- one for straightened, one per overlay version in
 * use), followed by a required summary-table slide, added last. Per-set
 * slides (one straightened + one overlay slide per individual set) were
 * removed at 2.2 -- they duplicated the exact same full-resolution source
 * images already shown on the grouped slides, roughly doubling file size
 * for no unique content (confirmed byte-identical embeds). NO title slide.
 * The rust % table is reported in the chat reply too, in addition to the
 * deck's summary slide -- not instead of it.
 *
 * Exact grouped-slide geometry (IMG_H=1.6in, ROW_GAP=0.08in) was reverse-
 * engineered from a reference deck's raw XML (EMU values converted to
 * inches) in a prior session -- if it ever looks off again, re-verify
 * against actual deck XML rather than eyeballing it or trusting a verbal
 * description in a chat summary.
 *
 * Image handling: `addImage` embeds the source PNG's raw bytes as-is --
 * pptxgenjs does not resample or re-encode on embed, so display size (w/h
 * on the slide) never affects the stored pixel data. Source panel PNGs
 * (straightened + overlay) must stay RGBA with real alpha transparency
 * (mounting hole and rounded corners as true transparency, not a
 * white/flattened fill) -- do not flatten to JPEG or composite onto a
 * white background to save space; with per-set slides removed, storage is
 * no longer tight enough to justify that quality tradeoff.
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

// ---- EDIT THESE FOR THE CURRENT BATCH ----
const PROJECT = "AN26_0110";
const SETS = ["9B", "9D", "10B", "10D"]; // per-set slide order
const TIMEPOINT = "24h";
// Optional short italic description under each set's column header on
// grouped slides (e.g. a formulation summary). Leave {} to omit -- but
// NEVER invent or infer this text; only fill it in with exact wording the
// user gave you for that batch. If only some sets have one, the row still
// reserves vertical space for every set in the group so columns stay
// row-aligned (see hasDescriptions below).
const DESCRIPTIONS = {};
// -------------------------------------------

const results = JSON.parse(fs.readFileSync("full_results.json", "utf8"));
const imageDims = JSON.parse(fs.readFileSync("image_dims.json", "utf8"));

function sizeOf(filePath) {
  const [width, height] = imageDims[filePath];
  return { width, height };
}

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
const SLIDE_W = 13.333;
const SLIDE_H = 7.5;

const DARK = "1A1A1A";
const GRAY = "555555";
const RED = "C0392B";
const LIGHT_LINE = "DDDDDD";
const FONT = "Calibri";

let pageNum = 1;
function addFooter(slide) {
  slide.addText(`${PROJECT} \u00b7 Rust Analysis \u00b7 ${TIMEPOINT}`, {
    x: 0.5, y: SLIDE_H - 0.42, w: 6, h: 0.3,
    fontSize: 10, color: GRAY, fontFace: FONT, margin: 0,
  });
  slide.addText(String(pageNum), {
    x: SLIDE_W - 1.0, y: SLIDE_H - 0.42, w: 0.5, h: 0.3,
    fontSize: 10, color: GRAY, fontFace: FONT, align: "right", margin: 0,
  });
  pageNum++;
}
function addTitle(slide, title) {
  slide.addText(title, {
    x: 0.5, y: 0.35, w: SLIDE_W - 1.0, h: 0.55,
    fontSize: 26, bold: true, color: DARK, fontFace: FONT, margin: 0,
  });
}

// Per-set slides (one straightened + one overlay slide per set) were
// removed at skill_version 2.2 -- the user asked to stop generating them
// since grouped slides embed the exact same full-resolution source files
// (confirmed byte-identical, see History) at a smaller display size, so
// per-set slides were pure duplication with no unique content, roughly
// doubling deck file size for zero informational gain. Grouped + summary
// slides are now the entire deck. If you're tempted to re-add per-set
// slides, check with the user first -- this was a deliberate storage
// tradeoff, not an oversight.

// ---------- Grouped slides (fixed column grid, added at the end) ----------
// Geometry verified against reference deck XML: IMG_H=1.6in, ROW_GAP=0.08in,
// COL_GAP=0.35in. Caption font sizes: straightened "Panel N" at 9.5pt GRAY;
// overlay "Panel N — XX.X%" at 8pt RED bold -- deliberately smaller so the
// longer string still fits on one line within the narrow column width.
// Don't bump either size back up without re-checking captions still fit on
// one line at whatever IMG_W the current batch's aspect ratio produces.
const IMG_H = 1.6;
const ROW_GAP = 0.08;
const COL_GAP = 0.35;

function buildGroupedSlide(title, sets, kind) {
  const slide = pres.addSlide();
  slide.background = { color: "FFFFFF" };
  addTitle(slide, title);

  const N_COLS = sets.length;
  const firstStraight = `${sets[0]}_t_${TIMEPOINT}/panel1_straight.png`;
  const IMG_W = IMG_H * (sizeOf(firstStraight).width / sizeOf(firstStraight).height);
  const GRID_W = N_COLS * IMG_W + (N_COLS - 1) * COL_GAP;
  const availW = SLIDE_W - 1.0;
  if (GRID_W > availW) {
    throw new Error(`Grouped slide grid (${GRID_W.toFixed(2)}in) exceeds available width (${availW.toFixed(2)}in) for ${sets.length} columns -- split into smaller chunks (e.g. by condition) rather than shrinking columns to fit.`);
  }
  const X0 = (SLIDE_W - GRID_W) / 2;

  // Description row under each set's column header reserves vertical space
  // for every column in the group whenever ANY set in this batch has one,
  // so columns stay row-aligned even where a given set's description is
  // blank.
  const hasDescriptions = Object.keys(DESCRIPTIONS).length > 0;
  const SET_LABEL_Y = 1.05;
  const ROW1_Y = hasDescriptions ? 1.75 : 1.42;

  const nPanels = 3;
  const rowYs = [];
  const capYs = [];
  let y = ROW1_Y;
  for (let p = 0; p < nPanels; p++) {
    rowYs.push(y);
    const capY = y + IMG_H + 0.03;
    capYs.push(capY);
    y = capY + 0.22 + ROW_GAP; // caption height (0.22) + inter-row gap
  }

  sets.forEach((lab, i) => {
    const x = X0 + i * (IMG_W + COL_GAP);
    const data = results[lab];

    slide.addText(lab, {
      x: x, y: SET_LABEL_Y, w: IMG_W, h: 0.28,
      fontSize: 15, bold: true, color: DARK, align: "center", fontFace: FONT, margin: 0,
    });
    if (hasDescriptions && DESCRIPTIONS[lab]) {
      slide.addText(DESCRIPTIONS[lab], {
        x: x, y: SET_LABEL_Y + 0.3, w: IMG_W, h: 0.4,
        fontSize: 6, italic: true, color: DARK, align: "center", fontFace: FONT, margin: 0,
      });
    }

    for (let p = 0; p < nPanels; p++) {
      const fname = `${lab}_t_${TIMEPOINT}/panel${p + 1}_${kind}.png`;
      slide.addImage({ path: fname, x: x, y: rowYs[p], w: IMG_W, h: IMG_H });
      const caption = kind === "straight" ? `Panel ${p + 1}` : `Panel ${p + 1} \u2014 ${data.pct[p].toFixed(1)}%`;
      slide.addText(caption, {
        x: x, y: capYs[p], w: IMG_W, h: 0.22,
        fontSize: kind === "overlay" ? 8 : 9.5,
        color: kind === "overlay" ? RED : GRAY, bold: kind === "overlay",
        align: "center", fontFace: FONT, margin: 0,
      });
    }

    if (i < sets.length - 1) {
      slide.addShape(pres.ShapeType.line, {
        x: x + IMG_W + COL_GAP / 2, y: SET_LABEL_Y, w: 0, h: capYs[capYs.length - 1] + 0.22 - SET_LABEL_Y,
        line: { color: LIGHT_LINE, width: 0.75 },
      });
    }
  });

  addFooter(slide);
}

// Split into chunks if too many columns would overflow the slide width
function chunkForWidth(sets) {
  const firstStraight = `${sets[0]}_t_${TIMEPOINT}/panel1_straight.png`;
  const IMG_W = IMG_H * (sizeOf(firstStraight).width / sizeOf(firstStraight).height);
  const availW = SLIDE_W - 1.0;
  const maxCols = Math.max(1, Math.floor((availW + COL_GAP) / (IMG_W + COL_GAP)));
  const chunks = [];
  for (let i = 0; i < sets.length; i += maxCols) chunks.push(sets.slice(i, i + maxCols));
  return chunks;
}

for (const chunk of chunkForWidth(SETS)) {
  const rangeLabel = chunk.length > 1 ? `${chunk[0]}\u2013${chunk[chunk.length - 1]}` : chunk[0];
  buildGroupedSlide(`All Sets \u2014 ${rangeLabel} \u2014 ${TIMEPOINT} \u2014 Straightened Panels`, chunk, "straight");
  buildGroupedSlide(`All Sets \u2014 ${rangeLabel} \u2014 ${TIMEPOINT} \u2014 Rust Overlay`, chunk, "overlay");
}

// ---------- Summary statistics slide (required, added last) ----------
// Rust % per panel per set, plus Average/Std Dev/RSD per set. Canonical
// palette/font, matches the rest of the deck -- this is a real deck slide
// as of skill_version 2.1 (previously chat-only; the user reversed that
// decision and asked for it back in the deck).
function stddev(vals) {
  const m = vals.reduce((a, b) => a + b, 0) / vals.length;
  const variance = vals.reduce((a, b) => a + (b - m) ** 2, 0) / vals.length;
  return Math.sqrt(variance);
}

function buildSummarySlide(sets) {
  const slide = pres.addSlide();
  slide.background = { color: "FFFFFF" };
  addTitle(slide, `Rust Coverage Summary \u2014 ${TIMEPOINT}`);
  slide.addShape(pres.ShapeType.line, {
    x: 0.5, y: 0.92, w: SLIDE_W - 1.0, h: 0, line: { color: LIGHT_LINE, width: 1 },
  });

  const nPanels = 3;
  const headerRow = [
    { text: "Set", options: { bold: true, fill: { color: "F3F4F6" }, color: DARK, fontFace: FONT } },
  ];
  for (let p = 1; p <= nPanels; p++) {
    headerRow.push({ text: `Panel ${p}`, options: { bold: true, fill: { color: "F3F4F6" }, color: DARK, fontFace: FONT } });
  }
  headerRow.push({ text: "Average", options: { bold: true, fill: { color: "F3F4F6" }, color: DARK, fontFace: FONT } });
  headerRow.push({ text: "Std Dev", options: { bold: true, fill: { color: "F3F4F6" }, color: DARK, fontFace: FONT } });
  headerRow.push({ text: "RSD", options: { bold: true, fill: { color: "F3F4F6" }, color: DARK, fontFace: FONT } });

  const rows = [headerRow];
  const methodsUsed = new Set();
  const perSetMethod = [];
  for (const lab of sets) {
    const data = results[lab];
    methodsUsed.add(data.method);
    perSetMethod.push(`${lab}=${data.method}`);
    const vals = data.pct;
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    const sd = stddev(vals);
    const rsd = avg !== 0 ? (sd / avg) * 100 : 0;
    const row = [{ text: lab, options: { bold: true, color: DARK, fontFace: FONT } }];
    for (let p = 0; p < nPanels; p++) {
      row.push({ text: `${vals[p].toFixed(1)}%`, options: { color: GRAY, fontFace: FONT } });
    }
    row.push({ text: `${avg.toFixed(1)}%`, options: { bold: true, color: DARK, fontFace: FONT } });
    row.push({ text: `${sd.toFixed(1)}%`, options: { color: GRAY, fontFace: FONT } });
    row.push({ text: `${rsd.toFixed(1)}%`, options: { color: GRAY, fontFace: FONT } });
    rows.push(row);
  }

  slide.addTable(rows, {
    x: 1.0, y: 1.25, w: SLIDE_W - 2.0, h: Math.min(4.5, 0.5 + 0.45 * rows.length),
    fontSize: 13, fontFace: FONT, color: GRAY,
    border: { type: "solid", color: LIGHT_LINE, pt: 1 },
    align: "center", valign: "middle",
    autoPage: false,
  });

  const methodNote = methodsUsed.size > 1
    ? `Methods: ${perSetMethod.join(", ")}.`
    : `Method: ${[...methodsUsed][0]}.`;
  slide.addText(
    `${methodNote} Overlay: pure red (255,0,0) at 90% opacity.`,
    { x: 0.5, y: SLIDE_H - 0.95, w: SLIDE_W - 1.0, h: 0.4, fontSize: 9, italic: true, color: GRAY, fontFace: FONT }
  );
  addFooter(slide);
}

buildSummarySlide(SETS);

pres.writeFile({ fileName: `${PROJECT}_${SETS[0]}-${SETS[SETS.length - 1]}_${TIMEPOINT}B117.pptx` }).then(() => {
  console.log("done");
});
