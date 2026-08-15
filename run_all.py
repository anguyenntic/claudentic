"""
panel-rust-analysis skill_version: 2.3 -- must match SKILL.md's
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
  3. Classify rust via v1.3 (classify_rust_v13) -- the current default for
     ALL panels, including visually majority-corroded ones. Do NOT
     auto-switch to v1.4 for majority-corroded panels -- v1.4 is used only
     if the user explicitly asks for it.
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
from pipeline import load_rgba, get_panels, straighten_panel, classify_rust_v13, make_overlay
from PIL import Image

# ---- EDIT THESE FOR THE CURRENT BATCH ----
UPLOADS_DIR = "/mnt/user-data/uploads"
PREFIX = "AN26_0110"          # project/sample prefix used in filenames
LABELS = ["9B", "9D", "10B", "10D"]   # set/condition labels
TIMEPOINT = "24h"
MAX_PANELS = 3                # override per-set below if needed, e.g. MAX_PANELS_OVERRIDE = {"8B": 1}
MAX_PANELS_OVERRIDE = {}
# -------------------------------------------

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

    for idx, comp_id in enumerate(comps):
        straight = straighten_panel(arr, labels_arr, comp_id, stats)
        straight_img = Image.fromarray(straight, mode="RGBA")
        straight_rel = os.path.join(set_dir, f"panel{idx+1}_straight.png")
        straight_img.save(straight_rel)

        rust_mask, pct, pm = classify_rust_v13(straight)
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
            "classifier": "v1.3",
            "size": straight_img.size,
        })
        pct_list.append(round(float(pct), 2))
        print(lab, "panel", idx + 1, "rust%", round(pct, 2), "v1.3", "size", straight_img.size)

    results[lab] = {"timepoint": TIMEPOINT, "panels": panel_results}
    full_results[lab] = {"method": "v1.3", "pct": pct_list}

with open("all_results.json", "w") as f:
    json.dump(results, f, indent=2)
with open("full_results.json", "w") as f:
    json.dump(full_results, f, indent=2)
with open("image_dims.json", "w") as f:
    json.dump(image_dims, f, indent=2)
print("DONE")
