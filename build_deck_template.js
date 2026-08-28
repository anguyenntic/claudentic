/*
 * panel-rust-analysis skill_version: 2.10 -- must match SKILL.md's
 * skill_version, the repo copy, and the panel-rust-analysis line in
 * PROJECT_CANON.md. If it is out of sync with any of those, this file has
 * reverted to a stale snapshot: run from the repo clone instead of this
 * copy (see SKILL.md's VERSION CHECK section) rather than trusting it.
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
const PROJECT = "AN26_0409";
const SETS = ["9B", "9D", "10B", "10D"]; // per-set slide order
const TIMEPOINT = "24h";
// Specimen noun. "Panel" for Q-panels, "Coupon" for round/machined coupons.
// Used for image captions, grouped-slide titles and summary column headers.
// Do NOT derive this from substrate -- steel coupons and cast iron panels
// both exist. Comes from the intake questions (see SKILL.md "Intake").
const SPECIMEN = "Panel";
// Test method, used in the output filename. "B117" is salt fog; a humidity
// cabinet run is "D1748", cyclic damp heat "IEC60068". Was hardcoded to
// B117 before 2.7, which silently mislabeled every non-salt-fog batch.
const TEST_METHOD = "B117";
// Optional short italic description under each set's column header on
// grouped slides (e.g. a formulation summary). Leave {} to omit -- but
// NEVER invent or infer this text; only fill it in with exact wording the
// user gave you for that batch. If only some sets have one, the row still
// reserves vertical space for every set in the group so columns stay
// row-aligned (see hasDescriptions below).
const DESCRIPTIONS = {};
// Optional test-conditions slide, added FIRST (before the grouped slides).
// Ordered [label, value] pairs from the intake questions -- exposure, test
// method and parameters, substrate, specimen geometry, preparation. Leave
// [] to omit the slide entirely. Same rule as DESCRIPTIONS: the person's
// own wording only, never inferred or expanded. This is NOT the title
// slide that house style excludes -- it carries the run's conditions,
// which are otherwise recorded nowhere in the deck and are unrecoverable
// from the images later (added at skill_version 2.7).
const METHODS = [];
// Panel layout for the grouped slides (added at skill_version 2.9):
//   "columns" -- canonical: one column per set, replicates stacked down it.
//                Correct for n<=3 replicates; unchanged from 2.7.
//   "blocks"  -- each SET is a horizontal block of its replicates, blocks
//                arranged BLOCKS_PER_ROW across. Use when replicates per set
//                exceed what a column can hold (n=5 collapses a column to
//                0.72in rows). Puts every replicate on one slide AND renders
//                them larger, because it spends the slide's slack axis
//                (width) instead of its tight one.
// Optional significance-testing slide per timepoint (added 2.10). Set true
// ONLY when the person asked for it (SKILL.md Intake question 8) and
// stats_analysis.py has written stats.json. Never add it unasked: it
// invites reading a p-value as a verdict on a coating, and at n=3 vs n=5
// a non-significant result usually means underpowered, not equivalent.
const STATS = false;
const LAYOUT = "columns";
const BLOCKS_PER_ROW = 2;
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
// Canonical row height, reverse-engineered from reference deck XML. This
// is now a FLOOR rather than a fixed value (2.7): a batch with fewer rows
// than the 3-replicate case leaves most of the slide empty, and a
// single-coupon batch rendered its specimens tiny in a sea of white.
// buildGroupedSlide grows the row height to fill whichever of the
// available width or height binds first, but never shrinks below this --
// so any batch that already filled the slide (e.g. 3 panels per column)
// is laid out byte-identically to before.
const IMG_H = 1.6;
// Bottom limit for the image grid; leaves clearance for the footer.
const GRID_BOTTOM = SLIDE_H - 0.55;
const ROW_GAP = 0.08;
const COL_GAP = 0.35;

function buildGroupedSlide(title, sets, kind) {
  const slide = pres.addSlide();
  slide.background = { color: "FFFFFF" };
  addTitle(slide, title);

  // Column width is computed PER SET from that set's own straightened-panel
  // aspect ratio, not from a single shared width -- panels are not all the
  // same shape (e.g. square coupons vs rectangular Q-panels can appear in
  // the same batch). IMG_H stays fixed across all columns for row
  // alignment; IMG_W varies per column so every panel keeps its true
  // aspect ratio instead of being stretched/squeezed to match column 1's
  // shape. Confirmed bug on a real batch: a fixed shared width computed
  // from a 0.6-aspect rectangular panel was silently squeezing genuinely
  // square (1.0-aspect, physical 3x3in) panels in other columns.
  const aspects = sets.map((lab) => {
    const f = `${lab}_t_${TIMEPOINT}/panel1_${kind === "overlay" ? "straight" : kind}.png`;
    const d = sizeOf(f);
    return d.width / d.height;
  });
  const availW = SLIDE_W - 1.0;
  // Description row under each set's column header reserves vertical space
  // for every column in the group whenever ANY set in this batch has one,
  // so columns stay row-aligned even where a given set's description is
  // blank.
  const hasDescriptions = Object.keys(DESCRIPTIONS).length > 0;
  const SET_LABEL_Y_BASE = 1.05;
  const ROW1_Y_BASE = hasDescriptions ? 1.68 : 1.42;
  let SET_LABEL_Y = SET_LABEL_Y_BASE;
  let ROW1_Y = ROW1_Y_BASE;

  // Panel count is derived PER SET from full_results.json rather than
  // hardcoded to 3 (fixed at skill_version 2.7). Batches do not always run
  // 3 replicates -- single-coupon sets and uneven replicate counts are both
  // real. Rows are laid out for the largest set in the chunk so columns stay
  // row-aligned; shorter columns simply end early.
  const nPanels = Math.max(...sets.map((l) => results[l].pct.length));

  // Row height grows to fill the slide, bounded by BOTH axes and floored
  // at the canonical IMG_H. Width bound: summed per-column widths (each
  // imgH * that column's own aspect) plus gaps must fit. Height bound:
  // nPanels rows of image + caption + gap must clear the footer. Because
  // it is a floor, any batch that already filled the slide (3 replicates
  // per column) lays out exactly as before -- only sparse batches grow.
  const PER_ROW_CHROME = 0.03 + 0.22 + ROW_GAP;
  const sumAspect = aspects.reduce((a, b) => a + b, 0);
  const widthFit = (availW - (sets.length - 1) * COL_GAP) / sumAspect;
  const heightFit = (GRID_BOTTOM - ROW1_Y) / nPanels - PER_ROW_CHROME;
  // IMG_H is a floor only where it FITS. Applying it after the height bound
  // (as 2.7-2.8 did) puts a 5-replicate column at 5 x 1.93 = 9.6in on a
  // 7.5in slide -- the grid simply runs off the bottom. It never surfaced
  // before because every earlier batch had n<=3. Fixed at 2.9; for n>=4
  // prefer LAYOUT = "blocks", which keeps the panels large instead of
  // shrinking rows to fit.
  const imgH = heightFit >= IMG_H ? Math.max(IMG_H, Math.min(widthFit, heightFit))
                                  : Math.min(widthFit, heightFit);

  const colWidths = aspects.map((a) => imgH * a);
  const GRID_W = colWidths.reduce((a, b) => a + b, 0) + (sets.length - 1) * COL_GAP;
  if (GRID_W > availW + 1e-6) {
    throw new Error(`Grouped slide grid (${GRID_W.toFixed(2)}in) exceeds available width (${availW.toFixed(2)}in) for ${sets.length} columns -- split into smaller chunks (e.g. by condition) rather than shrinking columns to fit.`);
  }
  const X0 = (SLIDE_W - GRID_W) / 2;
  const colX = [];
  {
    let x = X0;
    for (const w of colWidths) { colX.push(x); x += w + COL_GAP; }
  }

  // When the grid doesn't fill the slide (few rows, or width-bound growth),
  // centre the whole block -- column label, description and images together
  // -- instead of leaving it stranded at the top over a band of white.
  // Shifting the label with the images keeps the header attached to its
  // column. Slack is ~0 for a full 3-replicate batch, so those are
  // unchanged (2.7).
  {
    const gridH = nPanels * (imgH + PER_ROW_CHROME) - ROW_GAP;
    const slack = (GRID_BOTTOM - ROW1_Y_BASE) - gridH;
    if (slack > 0.05) {
      const shift = slack / 2;
      SET_LABEL_Y += shift;
      ROW1_Y += shift;
    }
  }

  const rowYs = [];
  const capYs = [];
  let y = ROW1_Y;
  for (let p = 0; p < nPanels; p++) {
    rowYs.push(y);
    const capY = y + imgH + 0.03;
    capYs.push(capY);
    y = capY + 0.22 + ROW_GAP; // caption height (0.22) + inter-row gap
  }

  sets.forEach((lab, i) => {
    const x = colX[i];
    const w = colWidths[i];
    const data = results[lab];

    slide.addText(lab, {
      x: x, y: SET_LABEL_Y, w: w, h: 0.28,
      fontSize: 15, bold: true, color: DARK, align: "center", fontFace: FONT, margin: 0,
    });
    if (hasDescriptions && DESCRIPTIONS[lab]) {
      // Tucked close under the set label and set at 9pt (was 0.3in below
      // at 6pt, which floated and read as a footnote rather than as part
      // of the column header). Bumped at 2.7 on request.
      slide.addText(DESCRIPTIONS[lab], {
        x: x, y: SET_LABEL_Y + 0.26, w: w, h: 0.3,
        fontSize: 9, italic: true, color: DARK, align: "center", fontFace: FONT, margin: 0,
      });
    }

    for (let p = 0; p < data.pct.length; p++) {
      const fname = `${lab}_t_${TIMEPOINT}/panel${p + 1}_${kind}.png`;
      slide.addImage({ path: fname, x: x, y: rowYs[p], w: w, h: imgH });
      const caption = kind === "straight" ? `${SPECIMEN} ${p + 1}` : `${SPECIMEN} ${p + 1} \u2014 ${data.pct[p].toFixed(1)}%`;
      slide.addText(caption, {
        x: x, y: capYs[p], w: w, h: 0.22,
        fontSize: kind === "overlay" ? 8 : 9.5,
        color: kind === "overlay" ? RED : GRAY, bold: kind === "overlay",
        align: "center", fontFace: FONT, margin: 0,
      });
    }

    if (i < sets.length - 1) {
      slide.addShape(pres.ShapeType.line, {
        x: x + w + COL_GAP / 2, y: SET_LABEL_Y, w: 0, h: capYs[capYs.length - 1] + 0.22 - SET_LABEL_Y,
        line: { color: LIGHT_LINE, width: 0.75 },
      });
    }
  });

  addFooter(slide);
}


// ---------- Block grouped slide (LAYOUT = "blocks", added at 2.9) ----------
// Column-per-set stacks replicates vertically, so n=5 needs five rows and the
// row height collapses. Laying each SET out as a horizontal block of its
// replicates and arranging the blocks BLOCKS_PER_ROW across uses the wide
// axis and yields LARGER panels than either shrinking rows or splitting
// replicates across continuation slides (measured on AN26_0502: 1.7in vs
// 1.4in). House style is otherwise identical -- same font, palette, 15pt bold
// set header, 9pt italic description, 9.5pt GRAY / 8pt RED bold captions, and
// the same 0.75pt divider between blocks.
const BLOCK_GAP_X = 0.4, BLOCK_GAP_Y = 0.22, PANEL_GAP = 0.12;
const HDR_H = 0.30, DESC_H = 0.26, CAP_H = 0.25;

function buildBlockSlide(title, sets, kind) {
  const slide = pres.addSlide();
  slide.background = { color: "FFFFFF" };
  addTitle(slide, title);

  const hasDescriptions = Object.keys(DESCRIPTIONS).length > 0;
  const chrome = HDR_H + (hasDescriptions ? DESC_H : 0) + CAP_H;
  const availW = SLIDE_W - 1.0;
  const TOP = 1.05;
  const availH = GRID_BOTTOM - TOP;
  const blockRows = Math.ceil(sets.length / BLOCKS_PER_ROW);
  const maxPanels = Math.max(...sets.map((l) => results[l].pct.length));

  const aspects = sets.map((lab) => {
    const d = sizeOf(`${lab}_t_${TIMEPOINT}/panel1_${kind === "overlay" ? "straight" : kind}.png`);
    return d.width / d.height;
  });
  const maxAspect = Math.max(...aspects);

  const hFit = (availH - blockRows * chrome - (blockRows - 1) * BLOCK_GAP_Y) / blockRows;
  const blockW = (availW - (BLOCKS_PER_ROW - 1) * BLOCK_GAP_X) / BLOCKS_PER_ROW;
  const wFit = ((blockW - (maxPanels - 1) * PANEL_GAP) / maxPanels) / maxAspect;
  const imgH = Math.min(hFit, wFit);
  if (imgH <= 0) throw new Error("block layout has no room -- lower BLOCKS_PER_ROW or split the sets across slides");

  const gridH = blockRows * (imgH + chrome) + (blockRows - 1) * BLOCK_GAP_Y;
  const y0 = TOP + Math.max(0, (availH - gridH) / 2);

  // Block width follows EACH set's own panel aspect. Sizing every block off
  // the widest set pushes wider blocks past the slide margin -- the same bug
  // class as the 2.4 per-column width fix, in the other axis.
  const bwOf = (j) => maxPanels * (imgH * aspects[j]) + (maxPanels - 1) * PANEL_GAP;

  sets.forEach((lab, i) => {
    const data = results[lab];
    const w = imgH * aspects[i];
    const n = data.pct.length;
    const usedW = n * w + (n - 1) * PANEL_GAP;
    const bw = bwOf(i);
    const rowIdx = Math.floor(i / BLOCKS_PER_ROW);
    const colIdx = i % BLOCKS_PER_ROW;
    const first = rowIdx * BLOCKS_PER_ROW;
    const blocksThisRow = Math.min(BLOCKS_PER_ROW, sets.length - first);
    let rowW = (blocksThisRow - 1) * BLOCK_GAP_X;
    for (let j = first; j < first + blocksThisRow; j++) rowW += bwOf(j);
    let bx = (SLIDE_W - rowW) / 2;
    for (let j = first; j < i; j++) bx += bwOf(j) + BLOCK_GAP_X;
    const by = y0 + rowIdx * (imgH + chrome + BLOCK_GAP_Y);

    slide.addText(lab, {
      x: bx, y: by, w: bw, h: HDR_H,
      fontSize: 15, bold: true, color: DARK, align: "center", fontFace: FONT, margin: 0,
    });
    if (hasDescriptions && DESCRIPTIONS[lab]) {
      slide.addText(DESCRIPTIONS[lab], {
        x: bx, y: by + 0.26, w: bw, h: DESC_H,
        fontSize: 9, italic: true, color: DARK, align: "center", fontFace: FONT, margin: 0,
      });
    }

    const imgY = by + HDR_H + (hasDescriptions ? DESC_H : 0);
    const px0 = bx + (bw - usedW) / 2;   // centre a short row (e.g. n=3 control)
    for (let p = 0; p < n; p++) {
      const x = px0 + p * (w + PANEL_GAP);
      slide.addImage({ path: `${lab}_t_${TIMEPOINT}/panel${p + 1}_${kind}.png`, x: x, y: imgY, w: w, h: imgH });
      const caption = kind === "straight" ? `${SPECIMEN} ${p + 1}` : `${SPECIMEN} ${p + 1} \u2014 ${data.pct[p].toFixed(1)}%`;
      slide.addText(caption, {
        x: x - PANEL_GAP / 2, y: imgY + imgH + 0.03, w: w + PANEL_GAP, h: 0.22,
        fontSize: kind === "overlay" ? 8 : 9.5,
        color: kind === "overlay" ? RED : GRAY, bold: kind === "overlay",
        align: "center", fontFace: FONT, margin: 0,
      });
    }
    if (colIdx < blocksThisRow - 1) {
      slide.addShape(pres.ShapeType.line, {
        x: bx + bw + BLOCK_GAP_X / 2, y: by, w: 0, h: imgH + chrome,
        line: { color: LIGHT_LINE, width: 0.75 },
      });
    }
  });

  addFooter(slide);
}

// Split into chunks if too many columns would overflow the slide width.
// Widths vary per set (see buildGroupedSlide), so this greedily accumulates
// columns using each set's own aspect ratio until the next one wouldn't
// fit, rather than assuming a uniform column width.
function chunkForWidth(sets) {
  const availW = SLIDE_W - 1.0;
  const widthOf = (lab) => {
    const f = `${lab}_t_${TIMEPOINT}/panel1_straight.png`;
    const d = sizeOf(f);
    return IMG_H * (d.width / d.height);
  };
  const chunks = [];
  let current = [];
  let currentW = 0;
  for (const lab of sets) {
    const w = widthOf(lab);
    const addedW = current.length === 0 ? w : w + COL_GAP;
    if (current.length > 0 && currentW + addedW > availW) {
      chunks.push(current);
      current = [lab];
      currentW = w;
    } else {
      current.push(lab);
      currentW += addedW;
    }
  }
  if (current.length > 0) chunks.push(current);
  return chunks;
}


// ---------- Test conditions slide (optional, added FIRST) ----------
function buildMethodsSlide(rows) {
  const slide = pres.addSlide();
  slide.background = { color: "FFFFFF" };
  addTitle(slide, "Test Conditions");
  slide.addShape(pres.ShapeType.line, {
    x: 0.5, y: 0.92, w: SLIDE_W - 1.0, h: 0, line: { color: LIGHT_LINE, width: 1 },
  });
  const table = rows.map(([k, v]) => [
    { text: k, options: { bold: true, color: DARK, fontFace: FONT, align: "left", valign: "middle" } },
    { text: v, options: { color: GRAY, fontFace: FONT, align: "left", valign: "middle" } },
  ]);
  slide.addTable(table, {
    x: 1.0, y: 1.3, w: SLIDE_W - 2.0,
    colW: [3.0, SLIDE_W - 5.0],
    fontSize: 13, fontFace: FONT,
    border: { type: "solid", color: LIGHT_LINE, pt: 1 },
    valign: "middle", autoPage: false,
  });
  addFooter(slide);
}

if (METHODS.length > 0) buildMethodsSlide(METHODS);

if (LAYOUT === "blocks") {
  buildBlockSlide(`All Sets \u2014 ${TIMEPOINT} \u2014 Straightened ${SPECIMEN}s`, SETS, "straight");
  buildBlockSlide(`All Sets \u2014 ${TIMEPOINT} \u2014 Rust Overlay`, SETS, "overlay");
} else {
  for (const chunk of chunkForWidth(SETS)) {
    const rangeLabel = chunk.length > 1 ? `${chunk[0]}\u2013${chunk[chunk.length - 1]}` : chunk[0];
    buildGroupedSlide(`All Sets \u2014 ${rangeLabel} \u2014 ${TIMEPOINT} \u2014 Straightened ${SPECIMEN}s`, chunk, "straight");
    buildGroupedSlide(`All Sets \u2014 ${rangeLabel} \u2014 ${TIMEPOINT} \u2014 Rust Overlay`, chunk, "overlay");
  }
}


// ---------- Statistics slide (optional, added at 2.10) ----------
// Reads stats.json from stats_analysis.py: pairwise Welch t-tests,
// Holm-corrected within the timepoint, with Hedges' g. Placed immediately
// after the summary table for that timepoint.
//
// The caveat line at the bottom is NOT decoration -- with n=3 controls and
// n=5 coated sets this test is badly underpowered, and a reader who sees
// "not significant" without it will read equivalence that the data does
// not support. Keep it on the slide.
function buildStatsSlide(tp) {
  const all = JSON.parse(fs.readFileSync("stats.json", "utf8"));
  const rows0 = all.timepoints[tp];
  if (!rows0 || rows0.length === 0) return;
  const slide = pres.addSlide();
  slide.background = { color: "FFFFFF" };
  addTitle(slide, `Significance Testing \u2014 ${tp}`);
  slide.addShape(pres.ShapeType.line, {
    x: 0.5, y: 0.92, w: SLIDE_W - 1.0, h: 0, line: { color: LIGHT_LINE, width: 1 },
  });

  const head = ["Comparison", "Mean A", "Mean B", "Difference", "p (adj)", "Hedges' g", "Result"]
    .map((h) => ({ text: h, options: { bold: true, fill: { color: "F3F4F6" }, color: DARK, fontFace: FONT } }));
  const rows = [head];
  for (const r of rows0) {
    const diff = (r.mean_a - r.mean_b);
    let verdict, vcolor;
    if (r.note) { verdict = "not meaningful"; vcolor = GRAY; }
    else if (r.p_adj === null) { verdict = "no test"; vcolor = GRAY; }
    else if (r.significant) { verdict = "significant"; vcolor = RED; }
    else { verdict = "not shown"; vcolor = GRAY; }
    rows.push([
      { text: `${r.a} vs ${r.b}`, options: { bold: true, color: DARK, fontFace: FONT } },
      { text: `${r.mean_a.toFixed(1)}%`, options: { color: GRAY, fontFace: FONT } },
      { text: `${r.mean_b.toFixed(1)}%`, options: { color: GRAY, fontFace: FONT } },
      { text: `${diff >= 0 ? "+" : ""}${diff.toFixed(1)} pp`, options: { color: GRAY, fontFace: FONT } },
      { text: r.p_adj === null ? "\u2014" : (r.p_adj < 0.0001 ? "<0.0001" : r.p_adj.toFixed(4)),
        options: { color: GRAY, fontFace: FONT } },
      { text: (r.g === null || isNaN(r.g)) ? "\u2014" : `${r.g >= 0 ? "+" : ""}${r.g.toFixed(1)}`,
        options: { color: GRAY, fontFace: FONT } },
      { text: verdict, options: { color: vcolor, bold: verdict === "significant", fontFace: FONT } },
    ]);
  }
  slide.addTable(rows, {
    x: 0.7, y: 1.25, w: SLIDE_W - 1.4, h: Math.min(4.6, 0.45 + 0.42 * rows.length),
    fontSize: 12, fontFace: FONT, color: GRAY,
    border: { type: "solid", color: LIGHT_LINE, pt: 1 },
    align: "center", valign: "middle", autoPage: false,
  });
  slide.addText(
    `${all.test}, \u03b1 = ${all.alpha}. "Not shown" means the difference was not demonstrated at this sample size \u2014 `
    + `NOT that the sets perform the same. With n=3 controls and n=5 coated sets this test has low power. `
    + `Hedges' g is the size of the difference; p is the confidence it is not noise. Read both. `
    + `Replicates are panels within one chamber run, so run-to-run variation is not captured.`,
    { x: 0.5, y: SLIDE_H - 1.15, w: SLIDE_W - 1.0, h: 0.6, fontSize: 9, italic: true, color: GRAY, fontFace: FONT }
  );
  addFooter(slide);
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

  const nPanels = Math.max(...sets.map((l) => results[l].pct.length));
  // Std Dev / RSD are meaningless at n=1. When no set in the batch has
  // replicates, suppress both columns rather than printing a column of
  // 0.0% that reads as perfect precision (skill_version 2.7).
  const anyReplicates = sets.some((l) => results[l].pct.length > 1);
  const headerRow = [
    { text: "Set", options: { bold: true, fill: { color: "F3F4F6" }, color: DARK, fontFace: FONT } },
  ];
  for (let p = 1; p <= nPanels; p++) {
    headerRow.push({ text: `${SPECIMEN} ${p}`, options: { bold: true, fill: { color: "F3F4F6" }, color: DARK, fontFace: FONT } });
  }
  if (anyReplicates) {
    for (const h of ["Average", "Std Dev", "RSD"]) {
      headerRow.push({ text: h, options: { bold: true, fill: { color: "F3F4F6" }, color: DARK, fontFace: FONT } });
    }
  }

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
      const cell = p < vals.length ? `${vals[p].toFixed(1)}%` : "\u2014";
      row.push({ text: cell, options: { color: GRAY, fontFace: FONT } });
    }
    if (anyReplicates) {
      row.push({ text: `${avg.toFixed(1)}%`, options: { bold: true, color: DARK, fontFace: FONT } });
      row.push({ text: vals.length > 1 ? `${sd.toFixed(1)}%` : "\u2014", options: { color: GRAY, fontFace: FONT } });
      row.push({ text: vals.length > 1 ? `${rsd.toFixed(1)}%` : "\u2014", options: { color: GRAY, fontFace: FONT } });
    }
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
  // Overlay description must follow the METHOD actually used -- it was
  // hardcoded to the steel style before 2.7 and silently mislabeled every
  // cast-iron deck, which is exactly the kind of caption that gets
  // believed later. See pipeline.py OVERLAY_COLOR / OVERLAY_COLOR_CI.
  // One overlay style for every method since 2.10 (pipeline.py
  // OVERLAY_COLOR). Decks built before 2.10 used flat red on steel and are
  // not visually comparable with these.
  const overlayNote = "Overlay: soft red (255,85,85) at 45%, blended.";
  slide.addText(
    `${methodNote} ${overlayNote}`,
    { x: 0.5, y: SLIDE_H - 0.95, w: SLIDE_W - 1.0, h: 0.4, fontSize: 9, italic: true, color: GRAY, fontFace: FONT }
  );
  addFooter(slide);
}

buildSummarySlide(SETS);
if (STATS) buildStatsSlide(TIMEPOINT);

pres.writeFile({ fileName: `${PROJECT}_${SETS[0]}-${SETS[SETS.length - 1]}_${TIMEPOINT}${TEST_METHOD}.pptx` }).then(() => {
  console.log("done");
});
