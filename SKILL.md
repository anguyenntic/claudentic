---
name: panel-rust-analysis
description: "Full pipeline for corrosion/rust test specimen photos -- flat panels (Q-panels) AND round or machined coupons, on steel or cast iron: straighten each specimen, orient any mounting hole to the top, classify rust pixels, generate rust-overlay images, and assemble everything into a PowerPoint deck. Use this whenever the user uploads transparent-background (RGBA, pre-background-removed) panel or coupon photos -- each containing 1-3 specimens side by side -- and asks to run the 'usual' analysis, 'panel straighten and rust analysis', a coupon or button rust analysis, 'do it the same as before', or similar. Also use for follow-up requests on an existing batch: reorienting panels, adjusting the rust-classification threshold, building a diagnostic overlay to sanity-check the % against a visual impression, or re-running with a different classifier. If the input images still have their original background (not yet transparent), use the panel-bg-removal skill first."
skill_version: "2.10"
---

## VERSION CHECK -- do this before anything else in this skill

**Do not check the version against memory.** Memory has drifted from the
files independently of the files reverting (confirmed: memory recorded the
2.5 auto-selector as choosing between v1.3 and v1.6 when the file has
always said v1.5 and v1.6), so a memory-vs-file comparison produces two
unreliable readings and no way to tell which is wrong. Both sides also had
to be hand-updated on every change, which is the step that kept getting
skipped.

Check against the **canonical source in the project context** instead.
Two anchors, in this order:

**1. The project canon file.** Every conversation in this project has the
project files listed in context. Look for `PROJECT_CANON.md` (or any file
whose name contains `CANON`) under `/mnt/project/` and read the
`panel-rust-analysis` line. This is visible in every session regardless of
what state the installed skill is in, which is exactly why it is the
anchor.

The canon file may carry a date in its NAME (e.g.
`PROJECT_CANON_2026-08-26.md`) so its currency is visible at a glance in
the project file list without opening it. So glob rather than assuming a
fixed filename:

```bash
ls /mnt/project/ | grep -i canon
cat /mnt/project/*CANON*.md 2>/dev/null | grep -i "panel-rust-analysis"
```

**If more than one CANON file matches, stop and say so.** Uploading a
newly-dated canon without deleting the old one leaves two files
disagreeing about the current version, which is the exact failure this
anchor exists to prevent -- silently reading either one is worse than
reporting the conflict. Prefer the newest date in the filename, but say
plainly that duplicates exist and should be cleaned up. Note that a
`__1_`-style suffix on the filename is the same problem wearing a
disguise: it means the file was uploaded twice.

**2. The repo, which is what actually runs.** The canonical files live at
`github.com/anguyenntic/claudentic` (public). Clone it and read
`skill_version` from its `SKILL.md`:

```bash
cd /home/claude && git clone --depth 1 \
  https://github.com/anguyenntic/claudentic.git canon 2>/dev/null
grep -m1 skill_version canon/SKILL.md
```

### Then act on what you find

- **Installed version == repo version** -- proceed, and run from the repo
  copy anyway (see below). Nothing to report.
- **Installed version < repo version, or the installed files carry no
  `skill_version` marker at all** -- the installed skill has reverted.
  Say so plainly in one line, then **run from the repo copy** and carry
  on. Do not stop, do not ask the person to re-upload before proceeding,
  and do not reconstruct the fixes from conversation history: the repo
  already has them. Mention the re-upload once, at the end, as a
  housekeeping note.
- **Installed version > repo version** -- the person edited the installed
  copy without pushing. Flag it and ask which to trust before running
  anything; this is the one case where you must not guess.
- **No network, and the repo is unreachable** -- fall back to the project
  canon file's version number. If the installed files do not match it,
  say so and stop rather than producing numbers under an unknown method.

### Always run from the repo copy

```bash
cd /home/claude && rm -rf panel-work && mkdir panel-work
cp canon/pipeline.py canon/run_all.py canon/build_deck_template.js panel-work/
```

This is the whole point of the change. The installed copy is a pointer;
the repo is the code. A revert of the installed files then costs a
one-line note instead of a session of archaeology, and it cannot silently
change the classifier out from under a batch.

### When you and the person agree on a real change

Bump `skill_version` in all four files, **push to the repo**, and update
the `panel-rust-analysis` line in `PROJECT_CANON.md`. Re-uploading the
installed skill is optional housekeeping, not a prerequisite -- the repo
is what runs. Verify the push landed by re-cloning to a fresh path and
diffing, per the verification rules below; a push you did not verify is
the same failure mode in a new place.

# Panel Rust Analysis

End-to-end workflow for corrosion-testing panel photos: straighten -> orient
-> classify rust -> overlay -> PowerPoint deck. Developed and validated
against real B117 salt-spray panel batches.

## READ THIS FIRST: this skill has a real, repeated persistence problem

The files in this skill (`pipeline.py`, `build_deck_template.js`,
`run_all.py`, this SKILL.md) have silently reverted to stale earlier
versions across sessions **at least four separate times**, despite each
time being edited, reportedly "verified," and reported to the user as
fixed. Specific things that have reverted and had to be re-fixed more than
once: the v1.3 classifier itself, the deck house style (font/palette/
layout), the `max_panels` parameter, the diagonal-canvas rotation fix, the
180-degree orientation fix, and this file's own documentation of all of
the above.

**As of skill_version 2.6 this is contained rather than solved**: the
workflow runs from the repo clone, not from the installed files, so a
revert of the installed copy no longer changes what code executes. The
rules below still apply to the repo copy -- they are what keeps a bad
edit from being pushed in the first place.

**Consequences of this for how you work in this skill:**

1. **Never trust a chat summary, your own memory, or a prior "I fixed it"
   as ground truth for what's actually in these files right now.** Before
   running anything or telling the user something is fixed, `cat` or
   `view` the actual file.
2. **Verification must be independent of the write, every time**: after
   any edit here, copy the whole skill directory to a fresh path (e.g.
   `/tmp/verify_X`, with a short `sleep` before copying) and `diff` against
   what you staged, or do a fresh Python import from that independent
   path and inspect the live function (`inspect.getsource`/`inspect.
   signature`), not just grep text. A same-session re-read via `view` is
   necessary but has NOT been sufficient historically -- files that passed
   a same-session check still reverted by the next session.
3. **If you're about to build a deck or run the pipeline and something
   looks different from what you remember being agreed** (wrong font,
   wrong classifier default, wrong image size, missing a fix), the most
   likely explanation is that a file reverted -- not that you're
   misremembering. Say so plainly and go re-verify the file rather than
   silently reprocessing with old, uncorrected code, or defending the
   current (possibly stale) file as correct.
4. If you and the user establish ANY new fix or style change, it must be
   written into these actual skill files (not a one-off working-directory
   script) before the conversation ends, verified per (2), and the
   rationale/exact values added to this SKILL.md so future sessions don't
   have to reconstruct it from conversation_search archaeology.

## Intake -- ask before running (added at skill_version 2.7)

Photos usually arrive with no context: a folder of images and "run the
usual analysis." Everything below shapes the output filename, the slide
captions and the deck's description row, and **none of it is inferable
from the pixels**. Guessing produces a deck that is confidently mislabeled
-- which is worse than an unlabeled one, because it looks authoritative.
Before setting up the working directory, check the conversation and
project context for each item, and **ask for whatever is genuinely
missing, in one batched message**:

1. **Exposure duration / timepoint** -- e.g. 24h, 96h. Sets `TIMEPOINT`,
   appears in every slide title, the footer, and the filename.
2. **Test method and parameters** -- salt fog (B117), humidity cabinet
   (D1748), cyclic damp heat (IEC 60068-2-30), temperature/RH, and
   concentration or dilution if a product is applied. Sets `TEST_METHOD`
   in the filename. **Do not default to B117**; before 2.7 it was
   hardcoded and silently mislabeled every humidity-cabinet batch as salt
   fog.
3. **Substrate** -- cast iron, cold-rolled steel, etc. `detect_substrate`
   can usually determine this, so treat the answer as confirmation and say
   what detection found rather than asking cold. Ask outright when
   detection abstains or the batch disagrees.
4. **Specimen type** -- panels or coupons. Sets `SPECIMEN`. Do NOT derive
   it from substrate: steel coupons and cast iron panels both exist.
5. **Whether a trailing `_1`/`_2` (or `.1`/`.2`) marks a REPLICATE or a
   separate condition.** On this project it marks a replicate: `5A_1` and
   `5A_2` are coupons 1 and 2 of condition 5A, not two conditions. Getting
   this wrong is quiet and costly -- each replicate becomes its own
   column, every column reads "Coupon 1", and the summary reports n=1 with
   no Average/Std Dev/RSD for anything. Group replicates with `SET_FILES`
   in `run_all.py`. Confirm rather than assume: a trailing index can
   legitimately mean a separate condition on other projects.
6. **Whether the specimens were photographed WET.** Straight out of the
   cabinet with water still on them, or dried first? This selects the
   classifier (`v1.9` for wet steel) and is not recoverable from the
   pixels -- a dense condensation field and a fine corrosion bloom look
   alike at low saturation. **Key it to the photography, not the
   chamber.** A water-fog run (D1735) usually means wet and a damp-heat
   run usually means less so, but a dried 1735 panel does not want v1.9
   (it would undercount) and a wet IEC panel does. Ask.
7. **Whether they want significance testing** between sets added to the
   deck (added at 2.10). Ask; do NOT add it by default. A p-value on a
   slide gets read as a verdict on a coating, and at the replicate counts
   this project runs (n=3 controls, n=5 coated) the test is underpowered
   enough that "not significant" usually means "not demonstrated", not
   "equivalent". If they say yes, run `stats_analysis.py` and set
   `STATS = true`. If they decline, leave the slide out entirely rather
   than including it unlabelled.
8. **What each set label means** -- e.g. what distinguishes 5A from 6A.
   This is the one that most improves the deck and the one most often
   skipped. Answers go verbatim into `DESCRIPTIONS`, keyed by set label.

Rules for handling the answers:

- **Ask once, batched.** Do not interrogate set by set, and do not block
  the analysis on a reply you can fold in at deck-build time -- run the
  pipeline and QA the overlays while waiting if that keeps things moving.
- **Never infer a description from a label** -- "6A" implying a cleaning
  step, a control, a replicate. `DESCRIPTIONS` takes the person's exact
  wording only; this rule predates 2.7 and the intake step exists to
  source that wording legitimately rather than to relax it.
- **If they decline or don't know**, leave the field out and build without
  it. An omitted description row is fine; an invented one is not.
- **Don't re-ask what's already established** in the conversation, the
  project files, or an earlier batch of the same experiment.

## Prerequisites

Input images must be **RGBA PNGs with the background already removed**
(transparent outside the panels), each containing 1-3 panels side by side.
If the uploads still have a real background, run the `panel-bg-removal`
skill first to produce these.

## Workflow

1. **Set up a working directory** and copy `scripts/pipeline.py` and
   `scripts/run_all.py` into it.
2. **Edit `run_all.py`**: set `UPLOADS_DIR`, `PREFIX`, `LABELS` (the
   condition/set labels, e.g. `["1F","1G","3F"]`), `TIMEPOINT`, and
   `MAX_PANELS` (default 3; use `MAX_PANELS_OVERRIDE = {"label": n}` for
   any set with a different panel count, e.g. a single-panel photo) to
   match the current batch's filenames
   (`{PREFIX}-{label}_t_{TIMEPOINT}.png`). If the project uses a different
   naming scheme, adjust the `fname` line directly.
3. **Run it**: `python3 run_all.py`. For each label this:
   - finds the panels via connected components on the alpha channel,
     filtering out tiny noise specks (<1000px) before picking the top
     `MAX_PANELS` candidates (`get_panels`)
   - straightens each panel (tilt-corrects via `minAreaRect` into a
     diagonal-sized rotation canvas so large-angle/landscape-framed source
     photos don't get clipped, angle normalized to `(-90, 90]`)
   - **auto-orients the mounting hole to the top** (`orient_hole_to_top`,
     tries 90 CW, 90 CCW, AND 180 degree rotations) -- always check this
     worked for squarish panels, since a square's `minAreaRect` can't
     resolve orientation on tilt alone; the hole position is the tell
   - classifies rust per panel with **v1.3 by default** and saves a red
     overlay
   - writes `all_results.json` (full diagnostic detail per panel),
     `full_results.json` (the shape `build_deck_template.js` consumes:
     `{label: {method, pct: [p1, p2, p3]}}`), and `image_dims.json` (keyed
     by full relative image path, e.g. `"9B_t_24h/panel1_straight.png"` --
     not basename, to avoid collisions across sets that reuse basenames)
4. **Visual QA before building the deck.** Build a quick contact sheet
   (straightened + overlay side by side per set, downscaled) and `view` it.
   Confirm: hole at top, no obvious mis-segmentation, overlay tracking real
   rust rather than glare/gradients/condensation droplets.
5. **Build the PowerPoint.** Copy `scripts/build_deck_template.js` into the
   working directory, edit the `PROJECT`/`SETS`/`TIMEPOINT`/`DESCRIPTIONS`
   constants at the top for the current batch, and run with `node`. See
   "Deck house style" below for what this produces and why -- do not
   modify the geometry/palette without reading that section first.
   Validate with `/mnt/skills/public/pptx/scripts/office/validate.py`,
   then render to images (`soffice --headless --convert-to pdf` +
   `pdftoppm -jpeg -r 150`) and QA **every slide** before delivering.
6. **Deliver**: copy the final `.pptx` to `/mnt/user-data/outputs/` and
   call `present_files`. Filename convention:
   `{project}_{firstSet}-{lastSet}_{timepoint}B117.pptx`. Report the rust
   % summary table in the chat reply too, in addition to the deck's own
   summary slide (see house style below) -- report it both places.

## Deck house style (canonical -- do not improvise, do not re-derive from memory)

`scripts/build_deck_template.js` is the single source of truth for exact
values. Read the large warning comment at its top before touching it.
Summary of what it currently implements, for reference (but the file
itself governs if this ever looks inconsistent with it):

- **Font**: Calibri throughout.
- **Palette**: title/labels `1A1A1A` (DARK), footer/panel-caption-on-
  straightened `555555` (GRAY), rust-% captions `C0392B` (RED, bold),
  divider lines `DDDDDD` (LIGHT_LINE, 0.75pt).
- **No per-set slides** (removed at skill_version 2.2): the deck used to
  include one straightened + one overlay slide per individual set, before
  the grouped slides. These were removed because they embedded the exact
  same full-resolution source images already shown on the grouped slides
  (confirmed byte-identical on inspection) at larger display size only --
  pure duplication, roughly doubling file size for zero unique content.
  If you ever find yourself adding per-set slides back, check with the
  user first -- this was a deliberate, requested storage tradeoff, not
  something to silently reintroduce because it seems friendlier to skim.
- **Two layouts, `LAYOUT` in `build_deck_template.js`** (added 2.9).
  `"columns"` is the canonical one described below and remains the
  default -- verified byte-identical output on a rebuild of the
  AN26_0409 deck. `"blocks"` lays each SET out as a horizontal row of its
  replicates and arranges the blocks `BLOCKS_PER_ROW` across. Use blocks
  when replicates per set exceed what a column can hold: at n=5 a column
  collapses to 0.72in rows, whereas blocks put every replicate on one
  slide at ~1.7in because they spend the slide's slack axis (width)
  rather than its tight one. Block width is computed from **each set's
  own** panel aspect -- sizing every block off the widest set pushes the
  wider ones past the slide margin, the same bug class as the 2.4
  per-column width fix. House style is otherwise identical across both.
- **Grouped slides** (all sets as columns on one slide -- one for
  straightened, one per overlay method in use -- now the deck's only
  panel-image content): `IMG_H = 1.6in` is a **floor, not a fixed value**,
  as of 2.7 -- the row height grows to fill whichever of the available
  width or height binds first, and the whole block (column label,
  description row and images) is centred vertically when slack remains.
  A batch that already filled the slide (3 replicates per column) has ~0
  slack and lays out exactly as before; a sparse batch no longer renders
  its specimens tiny at the top of a band of white. On the AN26_0409
  5-coupon batch this took the row height from 1.6in to 2.19in
  (width-bound). Row height is still shared by every column, but **`IMG_W` is computed PER COLUMN from that set's own
  straightened-panel aspect ratio** (fixed at skill_version 2.4 -- a
  single shared width computed only from the first set was silently
  stretching/squeezing any column whose panels had a different native
  aspect ratio than set 1, e.g. square coupons mixed with rectangular
  Q-panels in the same batch; confirmed on a real batch with genuinely
  square 3x3in panels rendering visibly distorted). `COL_GAP = 0.35in`,
  `ROW_GAP = 0.08in` between panel rows within a column, whole grid
  centered as a block (`X0`) using the summed per-column widths. `IMG_H`
  and the gap constants were reverse-engineered from a reference deck's
  raw XML (EMU values) in a past session -- if they ever look wrong again,
  re-verify against actual deck XML, not by eyeballing a render. Chunking
  across multiple grouped slides (`chunkForWidth`) also accounts for
  per-column width now, greedily packing columns until the next one
  wouldn't fit, rather than assuming a uniform column count fits per
  slide. Set ID as a bold 15pt header above each column. Panels stacked
  within each column: straightened captions ("Panel N") at **9.5pt**
  GRAY; overlay captions ("Panel N — XX.X%") at **8pt** RED bold --
  deliberately smaller so the longer string still fits on one line within
  the narrow column width; don't bump either back up without re-checking
  the fit on a real render. A thin vertical divider line between adjacent
  set columns.
  - **Optional description row**: a short italic **9pt** line (DARK
    color, raised from 6pt at 2.7 and tucked to 0.26in below the set
    label -- at 6pt and 0.3in it floated free and read as a footnote
    rather than as part of the column header)
    under each set's column header (e.g. a formulation summary), via the
    `DESCRIPTIONS` map keyed by set label. **Never invent or infer this
    text -- only fill it in with exact wording the user gave you for that
    batch.** Whenever `DESCRIPTIONS` is non-empty, every column in that
    group reserves the same vertical space for the row regardless of
    whether that particular set has text, so columns stay row-aligned.
  - **Overflow handling**: if a batch has too many sets to fit one slide
    at the fixed column width (`chunkForWidth`), it's split into multiple
    grouped slides automatically. The template also throws a hard error if
    a chunk would still overflow, so a bug here fails loudly instead of
    silently clipping columns off-slide.
- **Optional test-conditions slide, added FIRST** (`METHODS` in
  `build_deck_template.js`, added at 2.7): ordered label/value rows from
  the intake questions -- exposure window, test method and parameters,
  substrate, specimen geometry, preparation sequence. Omitted entirely
  when `METHODS` is `[]`. This does **not** contradict the no-title-slide
  rule below: it carries the run's actual conditions, which otherwise
  appear nowhere in the deck and cannot be recovered from the images
  months later. Same sourcing rule as `DESCRIPTIONS` -- the person's
  exact wording, never inferred, never expanded into detail they did not
  give.
- **No title slide, but a summary-table slide IS required**, added last
  (after all grouped slides): rust % per panel per set, plus Average, Std
  Dev, and RSD per set. Canonical palette/font, method footnote at the
  bottom (lists each set's classifier individually as `SET=method` pairs
  whenever more than one classifier was used in the batch, e.g. v1.3 for
  most sets and v1.4 for one explicitly-requested set -- this can no
  longer point to "per-set overlay slide titles" since those don't exist
  anymore as of 2.2). **Also still report the same rust % table in the
  chat reply** -- the deck slide doesn't replace that, both should exist.
- **Filename**: `{project}_{firstSet}-{lastSet}_{timepoint}B117.pptx`.
- Footer on every slide: `{PROJECT} · Rust Analysis · {TIMEPOINT}` left,
  page number right -- no "B117" suffix in the footer text itself (that
  only appears in the filename). Exception: when adding grouped slides
  onto an already-existing older deck whose slides predate this house
  style (e.g. a different font, no footer, or that older deck's own
  per-set slides from before 2.2), don't retroactively restyle slides
  already delivered/approved -- apply canonical style only to new slides
  and say so explicitly.
- **Image quality/transparency**: `addImage` embeds the source PNG's raw
  bytes as-is -- pptxgenjs does not resample or re-encode on embed, so
  the smaller on-slide display size of grouped-slide images never costs
  any actual pixel detail; extracting the embedded media confirms
  identical pixel dimensions and byte content to the source file. Source
  panel PNGs (straightened + overlay, from `pipeline.py`/`run_all.py`)
  must stay RGBA with real alpha transparency (mounting hole and rounded
  corners as true transparency) -- **do not** flatten to a white
  background or convert to JPEG to save space. That flattening approach
  was used in a different, older deck-building implementation for a
  different project; it does not apply to this canonical template, and
  with per-set slides removed there's no longer enough storage pressure
  to justify that quality tradeoff even if there were.
- **Data structure consumed**: `full_results.json` keyed by set label ->
  `{method, pct: [p1, p2, p3]}`, plus `image_dims.json` keyed by full
  relative image path. Both written by `run_all.py`.

## Rust classification method

**As of skill_version 2.5 the default is `classify_rust_auto`, which
picks between v1.5 and v1.6 per panel using the measured bare-metal
fraction.** v1.3 and v1.4 are both retained but are no longer the
default -- each was confirmed to have a systematic, quantified failure
mode on real batches (see below and History).

Why the policy changed. The previous rule was "v1.3 always, v1.4 only if
explicitly asked." That rule existed to stop Claude from switching
classifiers on a *visual impression* that a panel looked undercounted.
The problem was never the caution -- it was that both available
classifiers were measurably wrong in opposite directions:

- **v1.3 excluded genuine light rust wholesale.** Its 0.22 saturation
  floor was tuned against a lighting-gradient false positive on a
  different batch. On the AN26 thermal-aging batch the clean bare panel
  measured hue ~240-250 deg (slightly BLUE) at sat ~0.03-0.07, while the
  pale tan rust bleed staining measured hue ~35-40 deg at sat ~0.06-0.11
  -- clearly rust-hued, clearly below the floor. The excluded borderline
  population was 12-16 percentage points on the 8030 panels.
- **v1.4 forced a split that didn't exist.** Otsu on the value channel
  always finds a threshold, so on a panel with essentially no bare metal
  left it carves the *corrosion* into bright and dark halves. On the
  Control panel (1.2% bare-metal-like pixels, i.e. visually fully
  consumed) v1.4 reported 63.99% when the true answer was ~99%.

The fix is not a judgement call about which one "looks right" -- it's
`bare_fraction()`, an objective measurement of how much clean metal
remains, used to select the correctly-formulated method.

**Substrate first (added at 2.7).** `classify_rust_auto` takes a
`substrate` argument, set from `SUBSTRATE` in `run_all.py`. For
`"cast_iron"` it returns **v1.7** unconditionally -- the bare_fraction
selection below is a steel-only rule and is skipped entirely, because on
dark substrates it reads ~0% on clean metal and would silently route a
clean coupon to v1.6 and report ~100% rust. An unrecognised substrate
raises rather than falling back. The rule below applies to
`substrate="steel"` only:

**Selection rule (`classify_rust_auto`, default `majority_cut=50.0`):**
- `bare_fraction >= 50%` -- clean metal still dominates, the rust-forward
  formulation is valid -> **v1.5**
- `bare_fraction < 50%` -- panel is majority corroded, bare metal is the
  reliably separable class -> **v1.6**

Still report which method each panel used, and still QA overlays visually
before trusting numbers. If a user explicitly asks for v1.3 or v1.4 (e.g.
to reproduce an earlier batch's methodology for comparison), honour that
-- see "Comparing across sets, lots, or previous batches" below, since
numbers are NOT comparable across classifier versions.

### v1.5 (`classify_rust_v15`) -- default for light/moderate panels

v1.3 base plus two recovery passes, both gated on morphological
connectivity to the v1.3-confirmed mask:
- **Stage 3a (stain/bleed)**: rust-hued (10-55 deg) pixels above a low
  saturation floor (0.045) that still clears the bare panel's
  near-neutral blue-hued surface.
- **Stage 3b (dark oxide)**: pixels dark relative to their local
  neighborhood (Gaussian residual < -10 on the 0-255 scale) and mildly
  saturated. Deliberately NOT hue-constrained, because black/gray oxide
  falls outside the 10-55 window entirely -- that's precisely what v1.3
  misses.

**The connectivity gate is load-bearing.** Both candidate sets are grown
out of confirmed rust by morphological reconstruction, so only candidates
continuous with real rust survive. This is what keeps the low stain floor
from reintroducing the condensation false-positive failure mode fixed at
2.0 and 2.3 (a condensation zone can sit at the edge of the rust-hue
window with sat<0.15 and no real rust present -- but it won't be
connected to confirmed rust). Do not remove the gate or push
`stain_sat` toward zero without re-testing a condensation-heavy batch.

### v1.6 (`classify_rust_v16`) -- default for majority-corroded panels

Inverse bare-metal detection against **measured** clean-panel cutoffs
(`sat < 0.16` AND `val > 0.62`) rather than v1.4's Otsu-on-value, plus
rim correction. Two consequences:
- A panel with no clean metal left correctly returns ~100% instead of a
  spurious midpoint.
- `_rim_correct` drops border-band rust pixels not connected to interior
  rust, killing the beveled-edge shading artifact that made v1.4 outline
  the entire perimeter of even visually clean panels.

The cutoffs come from the measured clean central field of a known-clean
panel (8080_Unheated: sat p99 = 0.101, val p1 = 0.776), with margin. **If
the photography setup or lighting changes materially, re-measure them
against a known-clean panel** rather than assuming they transfer.

### v1.7 (`classify_rust_v17`) -- dark substrates (gray cast iron)

**Selected explicitly via `SUBSTRATE = "cast_iron"` in `run_all.py`, never
by eye and never auto-detected.** `classify_rust_auto` routes straight to
v1.7 for this substrate and does not consult `bare_fraction` at all.

Why it exists (measured, AN26_0409 A-set, gray cast iron rod coupons
polished to 240 grit per AN_063026_2): **the clean-metal signature the
v1.5/v1.6 pair depends on is inverted on this substrate.** On bright steel
Q-panels clean metal is BRIGHT (val p1 0.776) and corrosion is darker. On
dark cast iron clean metal is DARK (val p50 0.29-0.31, sat p50 0.07-0.09)
and rust is BRIGHT (val p50 0.66, sat p50 0.54). Consequences, all
confirmed on the five A-set coupons:

- `bare_fraction()` (`sat < 0.16 AND val > 0.62`) returns **0.17-0.55% on
  every coupon, including the two visually clean ones**.
- `classify_rust_auto` therefore routes all of them to v1.6, and v1.6
  reports **99.7% and 99.9% rust on coupons with no visible rust**.
- v1.5 also fails here (90.7% / 46.3% on those same clean coupons): its
  Stage 3b dark-oxide pass is not hue-constrained, so on a uniformly dark
  substrate it floods the whole coupon body once connectivity to any real
  edge rust is established.
- v1.3 is the only pre-2.7 classifier in the right ballpark, but carries
  its own false positive here: on 6A_1 it reported 10.8%, of which 47% of
  flagged pixels sat at val>0.55 -- the burnished/specular arc on clean
  machined iron, not rust.

**Method**: inverse bare-metal detection like v1.6, but the clean test is
**saturation only** (`sat < 0.28`), with v1.6's `_rim_correct` retained.
Value is deliberately excluded because it is not separable on this
substrate -- a burnished band on clean iron reaches val 0.88, brighter
than much genuine rust, so any value term reintroduces exactly the
false positive v1.3 shows.

Saturation works because the two populations separate with a real gap,
**including within the dark pixels specifically** -- which is what lets a
saturation rule catch dark oxide rather than miss it:

| population | sat | hue |
|---|---|---|
| clean iron, whole coupon (6A) | p50 0.07-0.09, p99 0.22-0.26 | 48-60 deg |
| clean iron, dark pixels only (val<0.40) | p50 0.069-0.088 | 48-60 deg |
| corroded, dark pixels only (val<0.40, 5A) | p50 0.37-0.46 | 27-28 deg |
| corroded, whole coupon (4A) | p50 0.54 | 27 deg |

**Cutoff selection**: 0.28 sits just above the measured clean p99 (0.261).
That margin is tighter than the steel case (p99 0.101 -> cutoff 0.16)
because the burnished band broadens the clean tail; it was chosen from a
cutoff sweep (0.22-0.34) as the point where the clean controls fall below
2% while the rusted control holds above 99%. **Re-measure against a
known-clean coupon if polish grit, lighting, or camera changes.**

**Known limitation -- thin stain undercounting.** Faint rust bleed can sit
below 0.28. On 5A_1 the 14.9% left unflagged measured sat p50 0.194 at hue
30 deg, i.e. rust-hued and four times the saturation of clean iron -- so
that coupon's 85.1% is very likely an undercount and the apparent 5A_1 vs
5A_2 replicate spread (85.1 vs 94.6) is partly threshold artifact, not
sample difference. Flag this rather than treating a v1.7 number as exact
in the 80-95% band. Values near 0 and near 100 are robust.

### v1.8 (`classify_rust_v18`) -- dark cast iron under warm/shadowed lighting

**Selected explicitly via `CLASSIFIER = "v1.8"` in `run_all.py`. NOT
auto-routed** -- `classify_rust_auto` still returns v1.7 for
`substrate="cast_iron"`, because lighting condition is not safely
detectable from a possibly-fully-corroded coupon, and silently switching
methods between batches would make numbers incomparable without anyone
noticing.

Why it exists (measured, AN26_0409 B-set, 24h IEC 60068-2-30, same gray
cast iron and prep as the A-set): **v1.7's saturation-only clean test
fails in BOTH directions when the photography has strong shadow.**

- **False positive on shadow.** 6B.2, operator-confirmed rust-free, read
  53.2% under v1.7. 50.6 of those 53.2 pp were not rust-hued at all (hue
  p50 196 deg, i.e. blue) at val p50 0.11. `sat = (max-min)/max` becomes
  numerically unstable as `max` approaches zero, so the deeply shadowed
  half of a disc reads as highly saturated and v1.7 calls it corrosion.
  50.7% of that coupon is coloured-but-near-black.
- **False negative on fine pitting.** 6B.1, heavily rusted, read 5.8%.
  Its corrosion is fine pitting at sat p50 0.19, below v1.7's 0.28
  cutoff, and the 0.5% minimum-component filter then deleted a further
  17.0 pp of genuine pit clusters.

**Method**: forward detection rather than inverse. A pixel is rust if it
is rust-hued (5-30 deg) AND saturated (>0.14) AND above a value floor
(>0.18). The value floor is the load-bearing part -- it excludes the
near-black region where saturation carries no information. Morphological
open plus v1.6's `_rim_correct` are retained. **The 0.5% speck filter is
deliberately not applied** (it removes real fine-pit corrosion).

Measured populations on lit (val>0.18), coloured (sat>0.14) pixels:

| population | hue p50 |
|---|---|
| rusted coupons (4B.1, 4B.2, 5B.1, 6B.1) | 19-27 deg |
| clean coupons (5B.2, 6B.2), burnished band | 38-39 deg |
| shadow, both | ~190 deg (excluded by the value floor) |

**Cutoff selection**: 3-way sweep (hue_max 28-36 x sat_min 0.12-0.18 x
val_min 0.14-0.22) scored on separation between the declared-clean and
declared-rusted coupons, with the two A-set clean coupons (6A.1, 6A.2,
photographed under the *different* A-set lighting) held out as an
independent check. hue_max is the sensitive term: 28 -> clean 0.00/0.01,
held-out 0.03/0.19, rusted 34.7-57.3; 30 -> clean 0.11/0.24, held-out
0.93/0.58, rusted 45.3-63.5; 32 -> clean 0.43/0.70, held-out 3.16/0.91.
30 is the knee -- it recovers ~9 pp more rust than 28 while all four
clean references stay under 1%.

**Known limitation -- black oxide excluded.** The dark network between
the orange patches on the heavily corroded coupons is corrosion product
but falls outside the hue window, so v1.8 numbers on those are
conservative. 4B.1 at 63.5% is rust-hued coverage, not total corroded
area. Say so rather than reporting the number as total corrosion.

**v1.7 and v1.8 numbers are not comparable.** Reprocess one side before
comparing a warm-lit batch against an A-set number.

### v1.9 (`classify_rust_v19`) -- steel photographed WET

**Selected explicitly via `CLASSIFIER = "v1.9"`. Never auto-routed** --
whether water was on the panel is a fact about the photography, not
something measurable from a possibly-fully-corroded image. See the intake
question above.

Structurally this IS v1.3 -- same v1.1 base, same Stage 1 dark-rust pass
with its round-blob droplet rejection, same Stage 2 morphological gap-fill.
**Only the three saturation floors differ**: base 0.22 -> 0.28, Stage 1
0.15 -> 0.22, Stage 2 0.16 -> 0.22.

Why (measured, AN26_0502 1735 series, 3B t=48h panel 4, region identified
by the operator as condensation rather than rust): v1.3's droplet defences
were built for *scattered* droplets on a dry panel. They do not handle a
panel that is **uniformly wet**, where the film of water over clean metal
carries a weak warm tint sitting inside the rust hue window at low
saturation.

| population | hue p50 | sat p50 |
|---|---|---|
| flagged pixels in the wet region (false positive) | 30.0 | 0.190 (86% below 0.30) |
| flagged pixels in the genuinely rusted band | 37.7 | 0.316 |

The adaptive Otsu threshold had already bottomed out on v1.3's 0.22 floor,
and the two growth stages then added 11.8 pp on top of a 14.4% base.

**Cutoff selection**: floors swept together against the operator-identified
wet region, the known-rusted controls, and the 2h coated panels (visually
clean). base/stage1/stage2:

| floors | wet region | Ctrl 48h | Ctrl 144h |
|---|---|---|---|
| 0.22/0.15/0.16 (v1.3) | 26.4% | 94.0% | 82.4% |
| 0.26/0.20/0.20 | 6.2% | 93.7% | 82.2% |
| **0.28/0.22/0.22** | **5.1%** | **93.5%** | **82.1%** |
| 0.32/0.26/0.26 | 3.5% | 91.8% | 81.7% |

0.28/0.22/0.22 is the knee -- ~80% of the false positive removed for 0.5 pp
off the rusted controls. Past it the controls start paying.

**Re-measure if lighting, camera or resolution changes.** These floors were
swept on PowerPoint-recompressed images (160-230 px per panel); a
full-resolution batch should be re-checked against a known-clean wet panel.

**v1.9 and v1.3 numbers are not comparable.** Reprocess one side before
comparing a wet batch against a dry one.

### v1.1 (`classify_rust`) -- base method, still used as v1.3's foundation

Per-panel **adaptive Otsu threshold** on the HSV saturation channel:
- Restrict to hue 10-55 degrees (orange/brown/rust range)
- Compute Otsu's threshold on the saturation values of in-hue-range pixels
- Lower that threshold by `0.12`, floored at `0.22`
- A pixel counts as rust if `sat > threshold` and hue is in range

**Do not change the floor without a specific reason and without telling
the user** -- 0.22 was tuned against a real false-positive case (see
History) and lowering it will reintroduce lighting-gradient false
positives.

### v1.3 (`classify_rust_v13`) -- current default

v1.1 base, plus two additional stages:

- **Stage 1 (dark-rust pass)**: catches dark/oxidized rust that the
  saturation threshold misses because it's too dark to register as
  saturated. Finds pixels significantly darker than their local
  neighborhood (Gaussian-blur residual on the value channel, cutoff -12 on
  the 0-255 scale) **that are also rust-hued (10-55 deg) AND above a
  modest saturation floor (sat>0.15)** -- both constraints matter, see the
  two droplet false-positive fixes in History (skill_version 2.0 and 2.3);
  hue alone isn't sufficient because a whole condensation-heavy zone can
  sit at the edge of the rust-hue window under weak ambient warm lighting
  even with no real rust present -- the saturation floor catches what hue
  alone misses. Filters out small isolated blobs (<30px) and round
  blobs (<150px area AND circularity>0.7, likely water droplets), and only
  keeps components within ~7px of the v1.1 mask (dark rust should be
  touching/near confirmed rust, not scattered noise).
- **Stage 2 (morphological gap-fill)**: uses skimage morphological
  reconstruction to grow the confirmed mask (v1.1 + Stage 1) into
  adjacent rust-hued, moderately-desaturated pixels (hue 10-55, sat>0.16,
  value residual<-4) that are touching it -- fills small gaps within rust
  patches without spreading into disconnected bare-metal regions.

### v1.4 (`classify_rust_v14`) -- SUPERSEDED by v1.6 as of 2.5, retained only for reproducing earlier batches

Inverse bare-metal detection via per-panel adaptive Otsu on the HSV value
channel: finds bright bare-metal pixels via Otsu on V within the panel
mask, calls everything else in the panel rust. Can be more accurate than
v1.3 on panels that are visually majority-corroded (where rust-hue/
saturation approaches undercount because heavily oxidized regions lose
saturation) -- but per the policy above, only run this if the user asks
for it by name or explicitly requests it after you flag that v1.3 looks
like it might be undercounting. Takes only `rgba` as input; returns
`(rust_mask, pct, pm)`.

**Overlay convention is ONE STYLE for every substrate, method and chamber
as of 2.10**: soft red `(255, 85, 85)` at 45%, **blended into** the
specimen pixels rather than replacing them, so corrosion morphology reads
through. Set in `pipeline.py` as `OVERLAY_COLOR`/`OVERLAY_OPACITY`;
`run_all.py` no longer branches on the classifier.

History of the change: introduced at 2.7 for cast iron, where a
near-fully-corroded coupon renders as a featureless disc under flat red (a
99.1% and a 94.6% coupon look identical); extended to wet steel at 2.9;
made universal at 2.10 on the operator's decision, since the same argument
applies to a 90%-rusted steel control and one project-wide style beats
per-method styling.

`OVERLAY_COLOR_LEGACY` / `OVERLAY_OPACITY_LEGACY` (flat red at 90%) and
`LEGACY_OVERLAY = True` in `run_all.py` are retained ONLY to reproduce a
specific pre-2.10 steel deck on request.

**Decks built at 2.10+ are not visually comparable with steel decks
delivered before it.** Say so when handing over a rebuild. The numbers are
unaffected -- this is presentation only.

### Known limitations (be upfront about these if asked)

- **Low-saturation gradient false positives**: mostly fixed by the 0.22
  floor, but can still occur on lightly-rusted panels with strong lighting
  falloff.
- **High-saturation glare/reflection**: the floor does *not* fix this (the
  glare's own saturation can exceed even a raised floor). Requires manual
  spatial exclusion of the connected component -- flag it to the user
  rather than silently patching.
- **Desaturated/thin rust bloom undercounting**: on heavily-rusted panels,
  a meaningful fraction of visually-rust-colored area can fall just below
  the saturation threshold and get excluded even with v1.3's gap-fill. If
  a user says the red looks like it's covering less than it should, don't
  just reassure them -- build the diagnostic overlay below and let them
  look, and flag that v1.4 exists as an opt-in alternative if it's severe.
- **Condensation droplets**: v1.3's Stage 1 hue constraint (see History)
  fixes the worst of this, but very reflective droplets sitting directly
  on active rust streaks can still pick up some signal since they're both
  dark and within a rust-adjacent hue from refraction. Spot-check
  condensation-heavy panels specifically.

## Diagnostic overlay (when the reported % looks off vs. the visual impression)

Build a 3-color diagnostic rather than asserting the number is right:
- **Red**: classified rust (passes threshold)
- **Blue**: rust-hued (in the 10-55 deg range) but excluded by the
  saturation threshold -- i.e. the borderline/desaturated pixels
- **Unmarked**: not rust-hued at all (bare metal, glare, water sheen)

```python
in_hue = (hue>=10)&(hue<=55)&panel_mask
borderline = in_hue & ~rust_mask
diag = arr.copy()
diag[rust_mask] = [255,0,0,255]
diag[borderline] = [0,100,255,255]
```

Report red%, blue%, and red+blue% -- this tells the user how much of the
gap between "measured %" and "looks like more" is real signal being
excluded by the threshold vs. how much is just perceptual (see next
section).

## Perceptual sanity check (mottled color area looks bigger than it is)

Scattered/mottled red against gray is a well-known perceptual effect --
people reliably overestimate its area fraction. Before assuming the
classifier under-counted, verify the pixel math independently (recount red
pixels directly from the saved overlay PNG, not just from the in-memory
mask) and, if useful, generate a same-area solid-block comparison: a plain
rectangle filled to the measured percentage, placed next to the actual
overlay, so the user can compare the real mottled pattern against a block
of the same true area.

## Comparing across sets, lots, or previous batches

If the user asks to compare a new batch against previously-analyzed data
(different lot, different timepoint, earlier session), check whether both
were processed with the **same classifier version** before comparing
numbers directly -- search past conversations for the prior methodology if
it's not in the current session. If versions differ, note it and consider
reprocessing one side with the other's classifier for a clean comparison.

## History / rationale (context if asked, not required reading to run this)

- **Universal overlay and optional significance testing added at
  skill_version 2.10.** The blended overlay stopped being per-substrate
  and became the single house style (see Deck house style above). Separately,
  `stats_analysis.py` was added with a paired intake question, deliberately
  opt-in: the risk with a statistics slide is not that the arithmetic is
  wrong but that a reader treats "not significant" as "equivalent" when the
  real cause is n=3 vs n=5. The slide carries that caveat in its footnote
  and the module refuses to test two effectively-clean sets against each
  other.

- **v1.9, the `IMG_H` floor fix and the block layout added at
  skill_version 2.9** (AN26_0502, steel Q-panels, D1735 water fog and IEC
  chamber, images recovered from a PowerPoint rather than raw files).
  Three separate findings:
  (a) The auto path routed wet panels to v1.5, which reported 73-98% rust
  on coated panels that were visually clean bare steel under condensation
  -- caught because those same panels simultaneously measured 77-92% bare
  metal, a self-contradiction. v1.3 handled it far better, and v1.9 then
  fixed the residual wet false positive v1.3 still showed (see the v1.9
  section).
  (b) `IMG_H` was applied as a floor AFTER the height bound, so a column
  with 5 replicates produced a 9.6in grid on a 7.5in slide and simply ran
  off the bottom. Latent since the geometry was introduced; never seen
  because every prior batch had n<=3.
  (c) The block layout was added because the honest fix for (b) --
  shrinking rows -- makes n=5 panels illegible.

- **PowerPoint as an image source.** When raw transparent files are gone,
  panel photos can be recovered from a deck: the media in `ppt/media/` are
  the intact source photos and the per-panel views are `a:srcRect` crops of
  them, so `get_panels` on the media beats using the crops. Map media to
  set labels via each slide's XML geometry -- **on this project the set
  label sits BELOW its row of panels**, so assign each image to the first
  label whose y exceeds the image's y, and verify against a render before
  trusting it. Expect PowerPoint recompression (160-230 px per panel here,
  against the 1000+ px these classifiers were tuned on); say so when
  reporting numbers.

- **v1.8 added at skill_version 2.8** (AN26_0409 B-set, 6 single round
  cast-iron coupons, 24h IEC 60068-2-30). Second lighting condition on
  the same substrate v1.7 was written for. Caught in visual QA before any
  number was delivered: v1.7 reported 53.2% on a coupon the operator
  confirmed rust-free and 5.8% on one he confirmed heavily rusted. Root
  cause was not a bad threshold but saturation being undefined in shadow
  (see the v1.8 section). Selected explicitly, never auto-routed.

- **Working files were modified mid-session during this batch.** The
  working copy of `pipeline.py` gained a `classify_rust_v18` and
  `run_all.py` was switched to `CLASSIFIER = "v1.8"` between two runs,
  with neither change made by the assistant nor present upstream. Its
  calibration comment asserted operator-declared ground truth that the
  operator had not given at that point. It was discarded, the working
  directory rebuilt from a fresh clone, and the classifier re-derived
  from ground truth the operator actually supplied. **Diff the working
  copy against an independent fresh clone before trusting a run, not
  just at setup** -- the version check at the start of a session does not
  cover a change made during it.

- **Replicate grouping (`SET_FILES`) added at skill_version 2.7.** The
  pipeline assumed one image file per set, so a set whose replicates
  arrived as separate single-specimen photos had to be listed as separate
  LABELS. That rendered each replicate as its own column captioned
  "Coupon 1", and made the summary slide report n=1 across the board --
  suppressing Average/Std Dev/RSD exactly where they were meaningful.
  `SET_FILES` maps a set label to a list of files and numbers specimens
  continuously across them. On AN26_0409 this collapsed five columns into
  three, restored "Coupon 1 / Coupon 2" within 5A and 6A, and produced
  real replicate statistics (5A 89.6% +/- 5.0, 6A 0.7% +/- 0.7).

- **Intake step, specimen noun and test method added at skill_version
  2.7.** `Panel` was hardcoded into slide captions, grouped-slide titles
  and summary headers, and `B117` into the output filename. Both are
  wrong for a round-coupon humidity-cabinet batch, and neither is
  recoverable from the images -- the deck simply asserted salt fog on
  panels. Parameterised as `SPECIMEN` and `TEST_METHOD`, and paired with
  the Intake section above so the values get asked for rather than
  defaulted. Set descriptions were folded into the same intake question,
  since `DESCRIPTIONS` has always required the person's exact wording and
  previously had no sanctioned way to obtain it.

- **v1.7 added and substrate made explicit at skill_version 2.7**
  (AN26_0409 A-set, 5 single round cast-iron coupons, no straightening).
  First non-steel substrate the skill had seen. Caught before any number
  was delivered by re-measuring the clean-metal signature against the
  known-clean 6A coupons, per the standing instruction in the v1.6
  section to re-measure when the setup changes materially -- the stock
  auto path would have reported 99.7%/99.9% rust on those two clean
  coupons. Root cause was not a bad threshold but an inverted substrate:
  clean cast iron is dark and dull where clean steel is bright and dull,
  so `bare_fraction`'s value term matches nothing. Fixed with a
  saturation-only clean test (v1.7) selected by an explicit `SUBSTRATE`
  flag rather than auto-detection, since detecting substrate from a
  possibly-fully-corroded panel is the same class of silent guess.
  Final at sat<0.28 with the 0.5% minimum-component filter: 4A_1 99.1%,
  5A_1 84.5%, 5A_2 94.6%, 6A_1 0.00%, 6A_2 1.3%, each visually QA'd
  against the operator's own read of the coupons. The speck filter is
  what takes 6A_1 to a true zero: its largest rust component was 0.264%
  of panel area (edge artifact) against 6A_2's genuine 1.304% patch, so
  a 0.5% floor separates them with margin and moves the corroded coupons
  by under 0.4 pp. Raising the saturation cutoff was considered and
  rejected for this -- at 0.36 it removes 16.5% of 5A_1 measuring sat
  0.318 at hue 28 deg, i.e. the dark-oxide field, which is corrosion
  product and not metal. Also at 2.7: `build_deck_template.js` derives panel
  count per set from `full_results.json` instead of hardcoding 3, and
  suppresses Std Dev/RSD when no set has replicates (a column of 0.0%
  reads as perfect precision at n=1).

- **Grouped-slide column-width fix at skill_version 2.4**: the fixed
  column grid computed a single `IMG_W` from set 1's straightened-panel
  aspect ratio and applied it to every column. This silently distorted
  any set whose panels had a different native aspect ratio -- caught on
  an AN26_0703 5C-5J batch where sets 5G/5H were genuinely square (1.0
  aspect, physical 3x3in) while every other set was ~0.6 aspect
  (rectangular, ~3x5in): 5G/5H were being horizontally squeezed to about
  60% of their correct width. Confirmed via direct pixel-dimension check
  (`PIL.Image.size`) rather than assuming from a description. Fixed by
  computing `IMG_W` independently per column from that column's own
  first straightened image, keeping `IMG_H` fixed across all columns for
  row alignment. `chunkForWidth` (which splits a batch across multiple
  grouped slides if too many columns would overflow) was updated
  correspondingly to greedily pack columns by their own width rather than
  assuming a uniform column count fits per slide. This is a general
  template fix, not a batch-specific patch -- any future batch mixing
  panel shapes (square coupons, rectangular Q-panels, etc.) benefits.

- **v1.5 + v1.6 added and classifier policy changed at skill_version
  2.5** (AN26 thermal-aging batch 2, 13 single-panel crops, no rotation).
  User reported "we are missing some rust." Diagnosed with the 3-color
  diagnostic overlay rather than by adjusting thresholds on impression:
  the excluded borderline (blue) population was 12-16 pp on the 8030
  panels and 3-5 pp on 35CD. Measuring the populations directly settled
  the cause -- the clean bare panel reads hue ~240-250 deg (slightly
  BLUE) at sat ~0.03-0.07, while the pale tan bleed staining trailing
  off every streak reads hue ~35-40 deg at sat ~0.06-0.11. So hue alone
  separates stain from clean metal cleanly on this setup, and v1.3's
  0.22 floor (a fix for a *different* batch's lighting-gradient
  artifact) was excluding real light rust. Separately, v1.4 was found to
  report 63.99% on the Control panel, which has only 1.2%
  bare-metal-like pixels and is visually fully consumed (~99%) --
  Otsu-on-value forces a split even when no bare metal exists, carving
  the corrosion itself in half. Plain v1.4 also outlined the entire
  perimeter of visually clean panels (beveled-edge 3D shading read as
  corrosion). Fixes: v1.5 (connectivity-gated stain + dark-oxide
  recovery), v1.6 (measured clean-metal cutoffs + rim correction), and
  `classify_rust_auto`/`bare_fraction` to select between them
  objectively instead of by eye. Validated per-panel visually across all
  13; the auto split landed at 35CD/8030/8080 -> v1.5 (bare 53-96%) and
  758/Control -> v1.6 (bare 1-43%), agreeing with visual QA in every
  case, and the near-clean 8080 control panel stayed clean (2.68%),
  confirming this is targeted recovery and not a blanket sensitivity
  increase. Net effect on that batch: Control 63.99% -> 99.27%, 758
  heat conditions ~56-68% -> ~95%, 8030 12-30% -> 19-46%.
- **Second condensation false-positive fix at skill_version 2.3**: the
  2.0 fix (hue-constraining Stage 1's dark-residual candidates) genuinely
  persisted correctly -- re-verified present and unchanged when this
  second issue was found, so this was not the persistence bug recurring.
  It was a narrower residual gap in the same underlying mechanism: hue
  alone isn't sufficient, because a whole condensation-heavy zone on a
  panel can sit at the edge of the rust-hue window (10-55 deg) under weak
  ambient warm lighting or a faint clean-metal tint, with no real rust
  present at all -- confirmed on an AN26_0703 5C-5J batch where median hue
  in an affected region was ~53 deg (just inside the window) with median
  saturation ~0.07 (far below any reasonable rust threshold). Diagnosed by
  building a 3-color breakdown (v1.1 red / Stage 1 orange / Stage 2 blue)
  and checking saturation distribution of the falsely-flagged pixels
  directly: ~90% had sat<0.15, while Stage 1 had no saturation floor at
  all (only Stage 2 did, at 0.16). Fixed by adding `sat > 0.15` to Stage
  1's `dark_candidate` condition. Verified against the full 8-set batch
  before and after: light-rust sets that were most condensation-affected
  dropped substantially (e.g. one set's panels went from 8.6-11.3% down to
  3.6-5.3%), heavy-rust sets were essentially unchanged (real rust is
  saturated enough to clear the new floor easily), confirming this is a
  targeted fix, not a blanket sensitivity reduction.

- **Per-set slides removed at skill_version 2.2**: the deck used to
  include one straightened + one overlay slide for each individual set
  before the grouped slides. Checking the actual embedded media in a
  built deck showed these were byte-for-byte duplicates of the same
  images already on the grouped slides (confirmed via hash comparison of
  extracted `ppt/media/*.png` files) -- pptxgenjs embeds full source
  resolution regardless of display size, so the smaller grouped-slide
  placement cost no detail, making the larger per-set versions pure
  redundancy. Removing them roughly halved deck file size (measured:
  ~164MB -> ~82MB on a 4-set/12-panel batch) with no loss of image detail
  or transparency. Also fixed a latent bug this surfaced: the summary
  slide's multi-classifier footnote used to say "see per-set overlay
  slide titles" for which set used which method -- now lists `SET=method`
  pairs directly in the footnote since that slide reference no longer
  exists.
- **Summary-table slide policy reversed at skill_version 2.1**: earlier
  policy was "no summary-table slide, chat-only." The user asked for the
  slide back in the deck (in addition to, not instead of, the chat
  report). Implemented in `buildSummarySlide` in
  `build_deck_template.js`, added as the last slide after all grouped
  slides.
- **Persistence failures (recurring, see warning at top of this file)**:
  this skill's four files have independently reverted to stale versions
  across sessions at least four times as of the most recent full
  consolidation (mid-August 2026): the v1.3 classifier itself, the deck
  house style, `max_panels`/diagonal-canvas/180-rotation fixes, and this
  documentation. Each revert was independently re-fixed and re-verified;
  there is no guaranteed fix for the underlying persistence issue from
  within a session, only more rigorous verification (see top of file) and
  keeping this document as complete and current as possible so
  reconstruction is fast if it happens again. The user has been told this
  plainly rather than it being silently patched over.
- v1.3 Stage 1 (dark-rust pass) originally had no hue constraint on its
  dark-residual candidate pixels -- it flagged anything darker than its
  local blur average, rust-colored or not. On condensation-heavy B117
  panels (AN26_0110 24h/40h batch) this pulled in the dark rims/shadows
  around water droplets sitting on bare metal, producing a mottled
  false-positive speckle field well below the real rust line (confirmed:
  ~41% of Stage 1's raw dark-candidate pixels on one affected panel were
  not rust-hued at all). Fixed by intersecting `dark_candidate` with the
  same `in_hue` (10-55 deg) mask already used for the v1.1 base, so Stage 1
  only ever grows into pixels that are both dark *and* rust-colored.
  Verified against v1.1 and pre-fix v1.3 on several panels: the fix removes
  the droplet speckle almost entirely while keeping the genuine dark-rust
  gain Stage 1 was added for.
- v1.0 used floor 0.15; raised to 0.22 (v1.1) after a confirmed
  lighting-gradient false positive on a lightly-rusted panel (16.7% ->
  ~1.0%, matching a manual correction) with negligible collateral effect
  on genuinely rusty panels.
- The ~180-degree-flip bug in `straighten_panel` (wide-vs-tall bounding
  boxes in `minAreaRect` getting spuriously flipped) is fixed via angle
  normalization to `(-90, 90]` -- don't reintroduce it.
- `straighten_panel`'s rotation used to clip landscape-framed source
  photos (hole on left/right, large rotation angle needed) because it
  rotated within the original sub-image's canvas, which isn't big enough
  once the long axis needs to fit where the short axis was. Fixed by
  rotating within a diagonal-sized canvas (padded, centered) and cropping
  tight afterward.
- `orient_hole_to_top` used to only try +-90 degree rotations. A panel can
  come out of `straighten_panel` with the hole at the BOTTOM (a 180-degree
  relationship), which no 90-degree rotation can fix -- confirmed on a
  real batch where hole-at-bottom panels were left uncorrected. Fixed by
  also trying `cv2.ROTATE_180` as a third candidate.
- `get_panels` used to have no `max_panels` parameter (hardcoded to top 3)
  and no minimum-area filter, so a batch with a set containing only 1-2
  real panels could pick up small noise/anti-aliasing specks as phantom
  panels. Fixed by adding `max_panels` (default 3, override per set) and
  filtering candidates below 1000px before ranking.
- Orientation should be validated two ways when possible: rust
  concentrating near the top (below the mounting hole) is the expected
  physical pattern for hung panels; the hole position itself is the more
  reliable signal for panels too lightly rusted for the rust-concentration
  check to be informative.
- `find_hole_frac` requires the candidate to be roughly square/round
  (bbox aspect 0.6-1.6, fills >45% of its bbox) and a decent minimum size,
  not just "the largest non-border-touching transparent blob." Without
  those filters, a panel whose true hole is partially clipped by the crop
  (and therefore excluded as border-touching) can fall back to a tiny
  edge-artifact sliver and get rotated *incorrectly*. When no candidate
  passes the filters, `orient_hole_to_top` must leave the panel unchanged
  rather than guess -- always sanity-check post-hoc with the
  top-vs-bottom rust concentration check above, especially on any panel
  where `find_hole_frac` returns `None`.
