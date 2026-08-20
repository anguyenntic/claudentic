"""
panel-rust-analysis skill_version: 2.5 -- must match SKILL.md's
skill_version and the version recorded in memory. If this number looks
out of sync with either, this file has likely reverted to a stale
snapshot -- see SKILL.md's persistence-warning section before trusting
anything below.

Template driver script for the panel-rust-analysis skill.

Copy this into a working directory alongside pipeline.py, edit UPLOADS_DIR /
LABELS / TIMEPOINT (and MAX_PANELS if a set has other than 3 panels) for
the current batch, and run it. It will:
  1. Load each labeled RGBA (background-removed) image
  2. Detect the panels in it (get_panels(arr, max_panels=MAX_PANELS)),
     straighten each, and orient the mounting hole to the top
  3. Classify rust. CLASSIFIER controls this:
       "v1.3"  -- legacy default, rust-hue/saturation only
       "auto"  -- (default as of 2.5) classify_rust_auto picks v1.5 or
                  v1.6 per panel from the measured bare-metal fraction
       "v1.5"  -- force stain-recovery (light/moderate panels)
       "v1.6"  -- force inverse bare-metal (majority-corroded panels)
       "v1.4"  -- legacy inverse method, superseded by v1.6
     v1.5/v1.6 were added at 2.5 after v1.3 was confirmed to exclude
     genuine pale rust bleed staining wholesale (its 0.22 saturation
     floor was tuned on a different batch's lighting-gradient artifact)
     and v1.4 was confirmed to report ~64% on a panel that was ~99%
     consumed. See SKILL.md "Rust classification method" before changing
     this.
  4. Save straightened + red-overlay PNGs
  5. Write all_results.json (full diagnostic detail per panel, including
     which classifier was used) AND full_results.json + image_dims.json in
     the exact shape build_deck_template.js expects:
       full_results.json:  {label: {method: "v1.3", pct: [p1, p2, p3]}}
       image_dims.json:    {"<label>_t_<timepoint>/panelN_<kind>.png": [w, h]}
     keyed by full relative path (not basename) to avoid collisions when
     different sets reuse the same basenames.

Naming convention assumed: {PREFIX}-{label}_t_{timepoint}.png
Adjust the `fname` line if the project's naming differs.
"""
import os, json
from pipeline import (load_rgba, get_panels, straighten_panel, make_overlay,
                      classify_rust, classify_rust_v13, classify_rust_v14,
                      classify_rust_v15, classify_rust_v16, classify_rust_auto,
                      bare_fraction)
from PIL import Image

# ---- EDIT THESE FOR THE CURRENT BATCH ----
UPLOADS_DIR = "/mnt/user-data/uploads"
PREFIX = "AN26_0110"          # project/sample prefix used in filenames
LABELS = ["9B", "9D", "10B", "10D"]   # set/condition labels
TIMEPOINT = "24h"
MAX_PANELS = 3                # override per-set below if needed, e.g. MAX_PANELS_OVERRIDE = {"8B": 1}
MAX_PANELS_OVERRIDE = {}
CLASSIFIER = "auto"           # "auto" | "v1.5" | "v1.6" | "v1.3" | "v1.4" | "v1.1"
STRAIGHTEN = True             # set False for pre-cropped single-panel batches
                              # where the user asked for no rotation
# -------------------------------------------


def _classify(arr):
    """Dispatch to the configured classifier. Returns (mask, pct, method)."""
    if CLASSIFIER == "auto":
        mask, pct, pm, method = classify_rust_auto(arr)
        return mask, pct, method
    fn = {"v1.1": classify_rust, "v1.3": classify_rust_v13,
          "v1.4": classify_rust_v14, "v1.5": classify_rust_v15,
          "v1.6": classify_rust_v16}[CLASSIFIER]
    mask, pct, pm = fn(arr)
    return mask, pct, CLASSIFIER

results = {}          # all_results.json -- full diagnostic detail
full_results = {}     # full_results.json -- canonical deck-template input shape
image_dims = {}       # image_dims.json -- keyed by full relative path

for lab in LABELS:
    fname = f"{PREFIX}-{lab}_t_{TIMEPOINT}.png"
    path = os.path.join(UPLOADS_DIR, fname)
    arr = load_rgba(path)
    max_panels = MAX_PANELS_OVERRIDE.get(lab, MAX_PANELS)
    comps, labels_arr, stats = get_panels(arr, max_panels=max_panels)

    set_dir = f"{lab}_t_{TIMEPOINT}"
    os.makedirs(set_dir, exist_ok=True)
    panel_results = []
    pct_list = []

    methods_used = []
    for idx, comp_id in enumerate(comps):
        if STRAIGHTEN:
            straight = straighten_panel(arr, labels_arr, comp_id, stats)
        else:
            # No rotation/reorientation -- tight-crop to the component only.
            # Used when the user explicitly asks not to straighten or flip
            # (e.g. pre-cropped single-panel batches). The output is still
            # written as panel{N}_straight.png because that is the filename
            # the deck template consumes; the name is a slot, not a claim
            # that rotation was applied.
            x, y, w, h, _area = stats[comp_id]
            pad = 5
            x0 = max(0, x - pad); y0 = max(0, y - pad)
            x1 = min(arr.shape[1], x + w + pad); y1 = min(arr.shape[0], y + h + pad)
            straight = arr[y0:y1, x0:x1].copy()
            straight[labels_arr[y0:y1, x0:x1] != comp_id] = 0

        straight_img = Image.fromarray(straight, mode="RGBA")
        straight_rel = os.path.join(set_dir, f"panel{idx+1}_straight.png")
        straight_img.save(straight_rel)

        rust_mask, pct, method = _classify(straight)
        overlay = make_overlay(straight, rust_mask, color=(255, 0, 0), opacity=0.9)
        overlay_img = Image.fromarray(overlay, mode="RGBA")
        overlay_rel = os.path.join(set_dir, f"panel{idx+1}_overlay.png")
        overlay_img.save(overlay_rel)

        image_dims[straight_rel] = straight_img.size
        image_dims[overlay_rel] = overlay_img.size

        panel_results.append({
            "panel": idx + 1,
            "rust_pct": round(float(pct), 2),
            "straight_path": straight_rel,
            "overlay_path": overlay_rel,
            "classifier": method,
            "bare_fraction": round(float(bare_fraction(straight)), 2),
            "size": straight_img.size,
        })
        pct_list.append(round(float(pct), 2))
        methods_used.append(method)
        print(lab, "panel", idx + 1, "rust%", round(pct, 2), method,
              "bare%", round(bare_fraction(straight), 1), "size", straight_img.size)

    results[lab] = {"timepoint": TIMEPOINT, "panels": panel_results}
    # If auto-selection picked different methods within one set, record them
    # all so the deck's method footnote stays accurate.
    set_method = methods_used[0] if len(set(methods_used)) == 1 else "/".join(methods_used)
    full_results[lab] = {"method": set_method, "pct": pct_list}

with open("all_results.json", "w") as f:
    json.dump(results, f, indent=2)
with open("full_results.json", "w") as f:
    json.dump(full_results, f, indent=2)
with open("image_dims.json", "w") as f:
    json.dump(image_dims, f, indent=2)
print("DONE")
