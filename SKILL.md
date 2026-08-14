---
name: panel-rust-analysis
description: "Full pipeline for corrosion/rust test panel photos: straighten each panel, orient the mounting hole to the top, classify rust pixels, generate red rust-overlay images, and assemble everything into a PowerPoint deck. Use this whenever the user uploads transparent-background (RGBA, pre-background-removed) panel photos -- each containing 1-3 panels side by side -- and asks to run the 'usual' analysis, 'panel straighten and rust analysis', 'do it the same as before', or similar. Also use for follow-up requests on an existing batch: reorienting panels, adjusting the rust-classification threshold, building a diagnostic overlay to sanity-check the % against a visual impression, or re-running with a different classifier. If the input images still have their original background (not yet transparent), use the panel-bg-removal skill first."
skill_version: "2.2"
---

## VERSION CHECK -- do this before anything else in this skill

This SKILL.md declares `skill_version: "2.2"` above. **Before running any
workflow in this skill, compare that version string against what's on
record in memory** (the person's memory edits / prior conversation
context should have a line like "panel-rust-analysis skill version:
X.Y"). Three possible outcomes:

- **Match** -- proceed normally.
- **File version is LOWER than memory's recorded version, or missing
  entirely** -- this skill has reverted to a stale snapshot (the
  persistence failure documented below happened again). Say so plainly to
  the person before doing anything else: name the mismatch (e.g. "the
  skill file says 2.0 but memory has 2.1 on record -- this reverted
  again"), and treat every fix/style value in this file as suspect until
  reconciled against memory and, if needed, past conversation history.
  Do not silently proceed as if the stale file is correct.
- **File version is HIGHER than memory's recorded version** -- memory is
  stale (e.g. the person is in a fresh context and memory hasn't caught up
  yet, or this is a genuinely newer skill state memory doesn't know about
  yet). Trust the file, and if it seems appropriate update memory to match.

**Whenever you and the person agree on a real change to this skill**
(pipeline fix, deck style change, classifier policy, etc.), bump
`skill_version` in every one of the four skill files (this one,
`pipeline.py`, `build_deck_template.js`, `run_all.py` -- see their own
version markers near the top) to the same new value, AND update the
memory record to match, in the same turn. A version bump that only
happens in the files (not memory) or only in memory (not the files)
defeats the entire point of this mechanism -- both sides must move
together, and both must be independently verified as described below.

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
- **Grouped slides** (all sets as columns on one slide -- one for
  straightened, one per overlay method in use -- now the deck's only
  panel-image content): a **fixed** column grid, not dynamic per-slide
  scaling -- `IMG_H = 1.6in`, `IMG_W` from the first straightened image's
  aspect ratio, `COL_GAP = 0.35in`, `ROW_GAP = 0.08in` between panel rows
  within a column, centered as a block (`X0`). These exact values were
  reverse-engineered from a reference deck's raw XML (EMU values) in a
  past session -- if they ever look wrong again, re-verify against actual
  deck XML, not by eyeballing a render. Set ID as a bold 15pt header above
  each column. Panels stacked within each column: straightened captions
  ("Panel N") at **9.5pt** GRAY; overlay captions ("Panel N — XX.X%") at
  **8pt** RED bold -- deliberately smaller so the longer string still fits
  on one line within the narrow column width; don't bump either back up
  without re-checking the fit on a real render. A thin vertical divider
  line between adjacent set columns.
  - **Optional description row**: a short italic 6pt line (DARK color)
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

**v1.3 (`classify_rust_v13`) is the default for every panel, including
visually majority-corroded ones.**

**Never switch to v1.4 automatically, even if v1.3 looks like it's
undercounting on a heavily-rusted panel -- only use v1.4
(`classify_rust_v14`) if the user explicitly asks for it in that
conversation.** (v1.4 was previously applied proactively on
majority-corroded panels as a standing rule; the user later asked that
this stop entirely -- v1.4 is opt-in only now, full stop.)

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
  the 0-255 scale) **that are also rust-hued (10-55 deg)** -- this hue
  constraint is important, see the droplet false-positive fix in History;
  without it Stage 1 flags condensation-droplet shadows on bare metal
  regardless of color. Filters out small isolated blobs (<30px) and round
  blobs (<150px area AND circularity>0.7, likely water droplets), and only
  keeps components within ~7px of the v1.1 mask (dark rust should be
  touching/near confirmed rust, not scattered noise).
- **Stage 2 (morphological gap-fill)**: uses skimage morphological
  reconstruction to grow the confirmed mask (v1.1 + Stage 1) into
  adjacent rust-hued, moderately-desaturated pixels (hue 10-55, sat>0.16,
  value residual<-4) that are touching it -- fills small gaps within rust
  patches without spreading into disconnected bare-metal regions.

### v1.4 (`classify_rust_v14`) -- opt-in only, never automatic

Inverse bare-metal detection via per-panel adaptive Otsu on the HSV value
channel: finds bright bare-metal pixels via Otsu on V within the panel
mask, calls everything else in the panel rust. Can be more accurate than
v1.3 on panels that are visually majority-corroded (where rust-hue/
saturation approaches undercount because heavily oxidized regions lose
saturation) -- but per the policy above, only run this if the user asks
for it by name or explicitly requests it after you flag that v1.3 looks
like it might be undercounting. Takes only `rgba` as input; returns
`(rust_mask, pct, pm)`.

Overlay convention (all versions): pure red `(255, 0, 0)` at 90% opacity
on a transparent background (`make_overlay` in `pipeline.py`).

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
