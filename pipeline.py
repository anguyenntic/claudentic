# panel-rust-analysis skill_version: 2.12 -- must match SKILL.md's
# skill_version, the repo copy, and the panel-rust-analysis line in
# PROJECT_CANON.md. If it is out of sync with any of those, this file has
# reverted to a stale snapshot: run from the repo clone instead of this
# copy (see SKILL.md's VERSION CHECK section) rather than trusting it.
import cv2
import numpy as np
from PIL import Image

def load_rgba(path):
    return np.array(Image.open(path).convert("RGBA"))

def get_panels(arr, max_panels=3):
    alpha = arr[...,3]
    mask = (alpha > 10).astype(np.uint8)
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    # filter out tiny noise specks (e.g. anti-aliasing artifacts near a
    # transparent background) before selecting the top panel candidates
    valid = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 1000]
    comps = sorted(valid, key=lambda i: stats[i, cv2.CC_STAT_AREA], reverse=True)[:max_panels]
    comps = sorted(comps, key=lambda i: stats[i, cv2.CC_STAT_LEFT])
    return comps, labels, stats

def straighten_panel(arr, labels, comp_id, stats):
    x,y,w,h,area = stats[comp_id]
    pad = 15
    x0=max(0,x-pad); y0=max(0,y-pad)
    x1=min(arr.shape[1], x+w+pad); y1=min(arr.shape[0], y+h+pad)
    sub = arr[y0:y1, x0:x1].copy()
    sub_labels = labels[y0:y1, x0:x1]
    keep = (sub_labels == comp_id)
    sub[~keep] = 0

    mask_u8 = keep.astype(np.uint8)
    contours,_ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(c)
    (cx,cy),(rw,rh),angle = rect
    if rw < rh:
        rot_angle = angle
    else:
        rot_angle = angle - 90

    # normalize into (-90, 90] to avoid spurious ~180 degree flips
    while rot_angle > 90:
        rot_angle -= 180
    while rot_angle <= -90:
        rot_angle += 180

    # Rotating toward portrait can be a large angle (~90 deg) when the
    # source photo is landscape-framed (hole on left/right) - keeping the
    # original (wide, short) canvas size for that rotation clips off most
    # of the panel's length, since the long dimension no longer fits in the
    # short axis. Use a canvas sized to the diagonal (with margin) instead,
    # centering the content in it, so nothing is cut off regardless of
    # rotation angle - the result gets cropped tight to content afterward
    # anyway, so the extra padding costs nothing.
    sh, sw = sub.shape[:2]
    diag = int(np.ceil((sh**2 + sw**2) ** 0.5)) + 20
    canvas = np.zeros((diag, diag, 4), dtype=sub.dtype)
    off_x = (diag - sw) // 2
    off_y = (diag - sh) // 2
    canvas[off_y:off_y+sh, off_x:off_x+sw] = sub

    center = (diag/2, diag/2)
    M = cv2.getRotationMatrix2D(center, rot_angle, 1.0)
    rotated = cv2.warpAffine(canvas, M, (diag, diag), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))

    # recompute bbox on rotated alpha and crop tight
    ralpha = rotated[...,3]
    rmask = (ralpha > 10).astype(np.uint8)
    ys, xs = np.where(rmask>0)
    if len(xs)==0:
        return rotated
    x0r,x1r = xs.min(), xs.max()
    y0r,y1r = ys.min(), ys.max()
    cropped = rotated[y0r:y1r+1, x0r:x1r+1]
    cropped = orient_hole_to_top(cropped)
    return cropped

def find_hole_frac(mask, edge_margin=3):
    """Locate the mounting-hole (a fully-enclosed, roughly round transparent
    region inside the panel mask) and return its (y_frac, x_frac) center as
    a fraction of panel height/width. Returns None if no confident hole is
    found -- callers should treat None as "don't rotate", not "guess".

    A real hole is small relative to the panel but roughly square/round in
    its bounding box (aspect ~0.6-1.6) and fills a good fraction of that
    bbox (>0.45); this rejects thin edge-artifact slivers that can appear
    when a real hole is partially clipped by a tight crop and excluded by
    the border check, which otherwise get picked up as false positives.
    """
    h, w = mask.shape
    panel_area = mask.sum()
    inv = (~mask).astype(np.uint8)
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(inv, connectivity=8)
    best = None
    for i in range(1, n):
        x, y, ww, hh, area = stats[i]
        # reject anything within edge_margin px of the border, not just exact touches
        if x <= edge_margin or y <= edge_margin or x + ww >= w - edge_margin or y + hh >= h - edge_margin:
            continue
        if area < max(300, 0.0008 * panel_area):
            continue
        aspect = ww / max(hh, 1)
        if aspect < 0.6 or aspect > 1.6:
            continue
        fill_ratio = area / (ww * hh)
        if fill_ratio < 0.45:
            continue
        if best is None or area > stats[best][4]:
            best = i
    if best is None:
        return None
    cx, cy = centroids[best]
    return cy / h, cx / w

def orient_hole_to_top(rgba, top_frac_threshold=0.3):
    """Rotate a straightened panel (90 deg CW/CCW, or 180) if needed so the
    mounting hole ends up near the top. No-op if already near top, or if
    no hole is found (in which case the panel is returned unchanged).

    Must try all three non-identity rotations, not just +-90 - a panel can
    come out of straighten_panel's tilt correction with the hole at the
    BOTTOM (a 180-degree relationship), which no 90-degree rotation can
    fix. Confirmed on a real batch: with only +-90 tried, sets where the
    hole landed at the bottom after straightening were left uncorrected
    (hole stayed at the bottom in the final output) even though a hole was
    clearly detected - the candidate rotations simply didn't include the
    one that would have fixed it."""
    mask = rgba[..., 3] > 10
    frac = find_hole_frac(mask)
    if frac is None:
        return rgba
    yf, _ = frac
    if yf < top_frac_threshold:
        return rgba
    for code in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE, cv2.ROTATE_180):
        rot = cv2.rotate(rgba, code)
        rfrac = find_hole_frac(rot[..., 3] > 10)
        if rfrac is not None and rfrac[0] < top_frac_threshold:
            return rot
    return rgba  # couldn't confirm any rotation fixes it; leave as-is

def hsv_channels(rgb):
    arr = rgb.astype(np.float32)/255.0
    R,G,B = arr[...,0], arr[...,1], arr[...,2]
    maxc = np.max(arr, axis=2); minc = np.min(arr, axis=2)
    diff = maxc - minc
    hue = np.zeros_like(maxc)
    mask_r = (maxc == R) & (diff > 0)
    mask_g = (maxc == G) & (diff > 0)
    mask_b = (maxc == B) & (diff > 0)
    hue[mask_r] = (60*((G[mask_r]-B[mask_r])/diff[mask_r]) + 360) % 360
    hue[mask_g] = (60*((B[mask_g]-R[mask_g])/diff[mask_g]) + 120)
    hue[mask_b] = (60*((R[mask_b]-G[mask_b])/diff[mask_b]) + 240)
    sat = np.where(maxc>0, diff/np.maximum(maxc,1e-6), 0)
    val = maxc
    return hue, sat, val

def otsu_threshold(vals):
    hist, edges = np.histogram(vals, bins=256, range=(0,1))
    hist = hist.astype(np.float64)
    total = hist.sum()
    sumB=0.0; wB=0.0; maxvar=0.0; thresh_i=0
    sum_all = np.sum(hist*np.arange(256))
    for i in range(256):
        wB += hist[i]
        if wB==0: continue
        wF = total-wB
        if wF==0: break
        sumB += i*hist[i]
        mB = sumB/wB
        mF = (sum_all-sumB)/wF
        varBetween = wB*wF*(mB-mF)**2
        if varBetween > maxvar:
            maxvar = varBetween
            thresh_i = i
    return thresh_i/255.0

def classify_rust(rgba, floor=0.22, lower_by=0.12):
    # rgba: straightened panel RGBA array
    rgb = rgba[...,:3]
    alpha = rgba[...,3]
    pm = alpha > 10
    hue, sat, val = hsv_channels(rgb)
    in_hue = (hue>=10) & (hue<=55) & pm
    sats = sat[in_hue]
    if len(sats) == 0:
        t = floor
    else:
        t = max(otsu_threshold(sats) - lower_by, floor)
    rust_mask = (sat > t) & in_hue
    pct = rust_mask.sum() / max(pm.sum(),1) * 100
    return rust_mask, pct, pm

def classify_rust_v13(rgba, floor=0.22, lower_by=0.12):
    """v1.3: v1.1 base + Stage 1 dark-rust pass + Stage 2 morphological gap-fill.

    Stage 1 (dark-rust pass): catches dark/oxidized rust that the saturation
    threshold misses because it's too dark to register as saturated. Finds
    pixels significantly darker than their local neighborhood (Gaussian-blur
    residual on the value channel, cutoff -12 on the 0-255 scale) that are
    also rust-hued (10-55 deg) AND above a modest saturation floor
    (sat>0.15) -- both constraints matter: the hue constraint alone isn't
    sufficient, since a panel can have a widespread weak/ambient warm color
    cast (from lighting, or a faint clean-metal tint) that puts a whole
    condensation-heavy zone right at the edge of the rust-hue window even
    with no real rust present; the saturation floor catches what hue alone
    misses (confirmed: ~90% of a real false-positive speckle field had
    sat<0.15, see History). Filters out small isolated blobs (<30px) and
    round blobs (<150px area AND circularity>0.7 -- these are water
    droplets, not rust), and only keeps components that lie within 7px of
    the v1.1 rust mask (dark rust should be touching/near confirmed rust,
    not scattered noise).

    Stage 2 (morphological gap-fill): uses skimage morphological
    reconstruction to grow the confirmed-rust mask (v1.1 + Stage 1) into
    adjacent rust-hued, moderately-desaturated pixels (hue 10-55, sat>0.16,
    val residual<-4) that are touching it -- fills small gaps within rust
    patches without spreading into disconnected bare-metal regions.
    """
    from skimage.morphology import reconstruction, label
    from skimage.measure import regionprops

    rgb = rgba[..., :3]
    alpha = rgba[..., 3]
    pm = alpha > 10
    hue, sat, val = hsv_channels(rgb)

    # --- v1.1 base mask ---
    in_hue = (hue >= 10) & (hue <= 55) & pm
    sats = sat[in_hue]
    t = floor if len(sats) == 0 else max(otsu_threshold(sats) - lower_by, floor)
    v11_mask = (sat > t) & in_hue

    # --- Stage 1: dark-rust pass ---
    val255 = (val * 255.0)
    blurred = cv2.GaussianBlur(val255, (0, 0), sigmaX=15)
    residual = val255 - blurred
    dark_candidate = (residual < -12) & pm & in_hue & (sat > 0.15) & ~v11_mask

    stage1_mask = np.zeros_like(v11_mask)
    if dark_candidate.any():
        lbl = label(dark_candidate, connectivity=2)
        # dilate v1.1 mask by 7px for proximity test
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        v11_dilated = cv2.dilate(v11_mask.astype(np.uint8), kernel, iterations=1).astype(bool)
        for region in regionprops(lbl):
            if region.area < 30:
                continue
            # circularity = 4*pi*area / perimeter^2
            perim = region.perimeter if region.perimeter > 0 else 1e-6
            circularity = 4 * np.pi * region.area / (perim ** 2)
            if region.area < 150 and circularity > 0.7:
                continue  # likely a water droplet
            coords = region.coords
            if not v11_dilated[coords[:, 0], coords[:, 1]].any():
                continue  # not near confirmed rust
            stage1_mask[coords[:, 0], coords[:, 1]] = True

    confirmed = v11_mask | stage1_mask

    # --- Stage 2: morphological gap-fill ---
    gapfill_candidate = (hue >= 10) & (hue <= 55) & (sat > 0.16) & (residual < -4) & pm & ~confirmed
    seed = np.zeros_like(val255)
    mask_img = np.zeros_like(val255)
    seed[confirmed] = 1.0
    mask_img[confirmed | gapfill_candidate] = 1.0
    if mask_img.any():
        rec = reconstruction(seed, mask_img, method='dilation')
        stage2_mask = (rec > 0.5) & gapfill_candidate
    else:
        stage2_mask = np.zeros_like(v11_mask)

    rust_mask = confirmed | stage2_mask
    pct = rust_mask.sum() / max(pm.sum(), 1) * 100
    return rust_mask, pct, pm


def classify_rust_v14(rgba):
    """v1.4: inverse bare-metal detection via per-panel adaptive Otsu on the
    HSV value channel. For panels that are visually majority-corroded, the
    rust-hue/saturation approach (v1.1/v1.3) can under-count because heavily
    oxidized regions lose saturation. Instead, find the bright bare-metal
    pixels via Otsu on V within the panel mask, and call everything else
    (within the panel) rust.
    """
    rgb = rgba[..., :3]
    alpha = rgba[..., 3]
    pm = alpha > 10
    hue, sat, val = hsv_channels(rgb)
    vals = val[pm]
    if len(vals) == 0:
        rust_mask = np.zeros_like(pm)
        return rust_mask, 0.0, pm
    t = otsu_threshold(vals)
    bare_metal = (val > t) & pm
    rust_mask = pm & ~bare_metal
    pct = rust_mask.sum() / max(pm.sum(), 1) * 100
    return rust_mask, pct, pm


def classify_rust_v15(rgba, stain_sat=0.045, dark_drop=-10, dark_sat=0.05,
                      blur_sigma=25):
    """v1.5: v1.3 base + Stage 3 recovery of pale rust bleed/stain and dark
    oxide, gated on morphological connectivity to confirmed rust.

    WHY THIS EXISTS (measured, AN26 thermal-aging batch 2): on these panels
    the CLEAN bare surface reads hue ~240-250 deg (slightly BLUE) at
    sat ~0.03-0.07, while the pale tan/yellow rust bleed staining that
    trails off every rust streak reads hue ~35-40 deg at sat ~0.06-0.11 --
    solidly rust-hued, just desaturated. v1.3's 0.22 saturation floor
    (tuned against a lighting-gradient false positive on a DIFFERENT batch,
    see History) therefore excludes genuine light rust staining wholesale.
    The excluded borderline population measured 12-16 percentage points on
    the 8030 panels alone, and 3-5 pp on the 35CD panels.

    Two recovery passes on top of v1.3's confirmed mask:
      - Stage 3a (stain/bleed): rust-hued (10-55 deg) pixels above a LOW
        saturation floor (default 0.045) that still clears the bare
        panel's near-neutral blue-hued surface.
      - Stage 3b (dark oxide): pixels dark relative to their local
        neighborhood (Gaussian residual, default cutoff -10 on the 0-255
        scale) and mildly saturated. Deliberately NOT hue-constrained --
        black/gray magnetite-type oxide falls outside the 10-55 window
        entirely, which is why v1.3 misses it.

    CRITICAL -- the connectivity gate: both candidate sets are grown out of
    the v1.3-confirmed mask by morphological reconstruction, so only
    candidates touching/continuous with confirmed rust survive. This is
    what prevents reintroducing the documented condensation false-positive
    failure mode (a whole condensation zone sitting at the edge of the
    rust-hue window under warm ambient light with NO real rust present --
    see the 2.0 and 2.3 History entries). Rust stain bleeds OUT of real
    rust; it does not appear in isolation. Do NOT remove this gate or
    lower stain_sat toward zero without re-checking a condensation-heavy
    batch, or you will undo both prior fixes at once.

    Use for light/moderate panels where clean bare metal still dominates.
    For majority-corroded panels use classify_rust_v16 instead -- v1.5
    still needs a confirmed-rust seed to grow from, so it degrades on
    panels whose corrosion has no clean neighborhood to contrast against.
    """
    from skimage.morphology import reconstruction

    pm = rgba[..., 3] > 10
    hue, sat, val = hsv_channels(rgba[..., :3])
    confirmed, _v13_pct, _ = classify_rust_v13(rgba)

    in_hue = (hue >= 10) & (hue <= 55) & pm
    stain_c = in_hue & (sat > stain_sat) & pm & ~confirmed

    val255 = val * 255.0
    residual = val255 - cv2.GaussianBlur(val255, (0, 0), sigmaX=blur_sigma)
    dark_c = (residual < dark_drop) & (sat > dark_sat) & pm & ~confirmed

    candidate = stain_c | dark_c
    seed = np.zeros_like(val255)
    mask_img = np.zeros_like(val255)
    seed[confirmed] = 1.0
    mask_img[confirmed | candidate] = 1.0
    if mask_img.any():
        rec = reconstruction(seed, mask_img, method='dilation')
        recovered = (rec > 0.5) & candidate
    else:
        recovered = np.zeros_like(confirmed)

    rust_mask = confirmed | recovered
    pct = rust_mask.sum() / max(pm.sum(), 1) * 100
    return rust_mask, pct, pm


# Clean bare-panel signature, MEASURED from the clean central field of a
# known-clean panel (8080_Unheated, AN26 thermal-aging batch 2):
#   sat: mean 0.076, p95 0.093, p99 0.101
#   val: mean 0.838, p5  0.808, p1  0.776
# The cutoffs below sit well outside that distribution so normal
# panel-to-panel exposure variation doesn't flip clean metal into rust.
# Re-measure these against a known-clean panel if lighting/setup changes.
BARE_SAT_MAX = 0.16
BARE_VAL_MIN = 0.62
BARE_RIM_PX = 14


def _rim_correct(rust_mask, pm, rim_px=BARE_RIM_PX):
    """Drop border-band rust pixels that aren't connected to interior rust.

    A panel's beveled edge reads dark purely from 3D shading, and any
    inverse bare-metal test misreads that shading as corrosion -- plain
    v1.4 outlines the entire perimeter of even a visually clean panel.
    Genuine edge corrosion is continuous with rust further in, so
    requiring connectivity to the eroded interior removes the shading
    artifact while keeping real edge rust.
    """
    from skimage.morphology import reconstruction

    pm_u8 = pm.astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                  (rim_px * 2 + 1, rim_px * 2 + 1))
    interior = cv2.erode(pm_u8, k, iterations=1).astype(bool)
    rust_interior = rust_mask & interior
    if not rust_interior.any():
        return rust_interior
    seed = np.zeros(rust_mask.shape, dtype=np.float32)
    mask_img = np.zeros(rust_mask.shape, dtype=np.float32)
    seed[rust_interior] = 1.0
    mask_img[rust_mask] = 1.0
    rec = reconstruction(seed, mask_img, method='dilation')
    return rec > 0.5


def classify_rust_v16(rgba, sat_max=BARE_SAT_MAX, val_min=BARE_VAL_MIN,
                      rim_px=BARE_RIM_PX):
    """v1.6: inverse bare-metal detection against the MEASURED clean-panel
    signature, plus rim correction. Supersedes v1.4 for majority-corroded
    panels.

    Two improvements over v1.4:
      1. v1.4 ran Otsu on the value channel alone, which forces a split
         even when there is essentially no bare metal left -- on a fully
         consumed panel it carves the corrosion itself into "bright" and
         "dark" halves and reports ~64% when the true answer is ~99%.
         v1.6 instead tests against fixed, measured clean-metal cutoffs
         (sat < 0.16 AND val > 0.62), so a panel with no clean metal
         correctly returns ~100% rather than a spurious midpoint.
      2. Rim correction (see _rim_correct) removes the beveled-edge
         shading false positive that made v1.4 outline the perimeter of
         clean panels.

    Use for majority-corroded panels. On lightly-corroded panels the
    inverse formulation is the wrong way round (bare metal stops being the
    reliably separable class) -- use classify_rust_v15 there.
    """
    pm = rgba[..., 3] > 10
    hue, sat, val = hsv_channels(rgba[..., :3])
    bare = pm & (sat < sat_max) & (val > val_min)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    bare = cv2.morphologyEx(bare.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
    rust_mask = pm & ~bare
    rust_mask = _rim_correct(rust_mask, pm, rim_px=rim_px)
    pct = rust_mask.sum() / max(pm.sum(), 1) * 100
    return rust_mask, pct, pm


def classify_rust_v20(rgba, dark_frac=0.62, return_parts=False):
    """v2.0: v1.9 base + dark-oxide recovery by absolute darkness, gated on
    connectivity to confirmed rust. For STEEL PHOTOGRAPHED WET carrying dark
    oxide the colour-based passes cannot reach.

    WHY THIS EXISTS (measured, AN26_0111, 12 wet steel Q-panels, with operator
    annotation of two panels):

    v1.9 leaves the dark bands at panel edges and the dark cores of rust
    streaks uncounted, and no colour rule can recover them. Warm bias
    100*(R-B)/(R+G+B), which stays meaningful at low value where HSV
    saturation does not:

      confirmed rust        p10 +10.8  p50 +17.7  p90 +32.0   V p50  51
      dark band (missed)    p10 -10.7  p50  +0.5  p90 +19.3   V p50  53
      clean wet grey field  p10  +0.6  p50  +1.35 p90  +3.8   V p50 102

    The missed band is LESS warm than clean wet steel at the median, so any
    hue or chroma threshold loose enough to include it must also include the
    entire clean field. Darkness is the only separating axis left: the band
    sits at about half the brightness of the clean field.

    METHOD: a pixel is a candidate if it is below `dark_frac` of the panel's
    OWN median brightness, and it is kept only if morphological
    reconstruction connects it to the v1.9-confirmed mask.

    THE CONNECTIVITY GATE IS LOAD-BEARING, as in v1.5. Without it the pass
    recruits the shadowed side of every condensation droplet -- verified on
    this batch: the unconnected dark candidates form a speckle field across
    the whole panel body, which is the droplet false positive fixed at 2.0
    and 2.3. Do not remove it.

    WHY A GLOBAL REFERENCE, having tried three local ones. All were built and
    inspected on this batch; the operator chose this one after seeing all four:
      - LOCAL GAUSSIAN mean (sigma 150): kills a false positive this method
        has on 11A p1 (below), but a Gaussian at sigma comparable to the
        feature width is pulled down by the feature itself, so a WIDE dark
        band partly becomes its own background and under-recruits. Visibly
        worse than this method on 0A p1, which carries the widest band.
      - ITERATIVE clean-pixel mean: UNSTABLE. Excluding dark candidates
        raises the background, which qualifies more pixels as dark, which
        excludes more. At 3 iterations it flooded the grey field (0A p1 37%,
        11A p1 36%) while a scalar score on two hand-picked regions still
        looked good -- do not evaluate a change here without rendering it.
      - GREY CLOSING / rolling ball: the dilation step takes a local MAX,
        which the specular highlights on the condensation droplets drive to
        near 255, so the background saturates and ~93% of every panel
        qualifies. Wrong operator for a droplet-covered surface.
      - LOCAL 60th PERCENTILE (radius 70): stable and resolves the
        global-vs-Gaussian conflict, but on this batch it was not visibly
        better than this method anywhere except 11A p1. Kept as
        `classify_dark_percentile` in the batch notes if it is wanted later.

    KNOWN FALSE POSITIVE, accepted by the operator: because the reference is
    the panel median, this method cannot track a strong top-to-bottom
    brightness gradient, so the darkest part of an upper grey field can be
    recruited. On AN26_0111 11A panel 1 it flags a blotch of about 1.06% of
    panel area that the operator confirmed is not rust -- i.e. that panel's
    number is high by roughly 1 pp. Check for this on any panel with a strong
    gradient and report it per panel rather than silently.

    KNOWN LIMITATION -- edge shadow is accepted as rust. 61% of what this
    adds lies within 40 px of the panel edge, on every panel including the
    cleanest. Q-panel edges genuinely corrode first under B117, but a sheared
    edge in shadow is indistinguishable from edge oxide by any measurement
    available here. Interior gain averaged 1.18 pp per panel on this batch;
    the edge strip averaged 1.84 pp. Report both rather than implying the
    total is all corrosion.

    Replicate scatter is worse than v1.9's (RSD 20-31% vs 2-21% on this
    batch) because the edge strip varies panel to panel. Coverage improved,
    precision degraded -- say so when handing over numbers.

    v2.0 numbers are NOT comparable with v1.9, v1.3 or any other version.
    """
    from skimage.morphology import reconstruction

    confirmed, _pct, pm = classify_rust_v19(rgba)
    V = rgba[..., :3].astype(np.float32).sum(axis=2) / 3.0
    ref = float(np.median(V[pm])) if pm.any() else 0.0
    cand = pm & ~confirmed & (V < dark_frac * ref)

    seed = np.zeros(V.shape, np.float32)
    mask_img = np.zeros(V.shape, np.float32)
    seed[confirmed] = 1.0
    mask_img[confirmed | cand] = 1.0
    if mask_img.any() and confirmed.any():
        grown = reconstruction(seed, mask_img, method='dilation') > 0.5
    else:
        grown = confirmed.copy()
    grown &= pm
    pct = 100.0 * grown.sum() / max(pm.sum(), 1)
    if return_parts:
        return grown, pct, pm, confirmed, cand
    return grown, pct, pm

def local_brightness_ref(V, pm, radius=150, pct=60, ds=4):
    """Local `pct`th percentile of V over a disk of `radius` px.

    The background estimate used by classify_rust_v21. Computed on a
    downscaled copy and resampled up: a background estimate wants to be
    smooth, so the interpolation costs nothing real and the percentile
    filter on a 3000x1800 panel would otherwise dominate runtime. Pixels
    outside the panel are filled with the panel median first, so the filter
    is not dragged down at the specimen edge.
    """
    from scipy import ndimage as ndi
    fill = float(np.median(V[pm])) if pm.any() else 0.0
    W = np.where(pm, V, fill)
    small = W[::ds, ::ds]
    r = max(1, int(round(radius / ds)))
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    disk = (x * x + y * y) <= r * r
    ref_s = ndi.percentile_filter(small, pct, footprint=disk, mode='nearest')
    ref = ndi.zoom(ref_s, (V.shape[0] / ref_s.shape[0],
                           V.shape[1] / ref_s.shape[1]), order=1)
    if ref.shape != V.shape:
        out = np.full(V.shape, fill, np.float32)
        h = min(ref.shape[0], V.shape[0]); w = min(ref.shape[1], V.shape[1])
        out[:h, :w] = ref[:h, :w]
        ref = out
    return ref


def classify_rust_v21(rgba, dark_frac=0.62, radius=150, pct=60,
                      return_parts=False):
    """v2.1: v2.0 with a LOCAL brightness reference instead of the panel median.

    Selected explicitly via CLASSIFIER = "v2.1". Never auto-routed, for the
    same reason as v1.9 and v2.0: it depends on facts about the photography.

    Identical to v2.0 except the reference `dark_frac` is taken against --
    the local 60th percentile of brightness over a 150 px disk rather than
    the median of the whole panel. dark_frac and the connectivity gate are
    unchanged.

    WHY (measured, AN26_0112, 24 wet steel Q-panels, B117 24 h; the operator
    reported BOTH failures in one message and they share one cause):

    This batch's panels carry a far steeper top-to-bottom brightness gradient
    than AN26_0111's, which v2.0 was calibrated on:

        top rows    median brightness 66-95
        bottom rows median brightness 188-211      -> a 2-3x ratio

    Against a global median of ~129 the v2.0 cutoff lands at ~80. That is
    inside the clean grey UPPER field, and far below anything in the bright
    LOWER field, so one cutoff fails in both directions at once: it flags
    clean dark metal at the top and cannot reach genuine dark oxide at the
    bottom.

    The decisive measurement, on 2A panel 1, using warm bias
    100*(R-B)/(R+G+B):

        confirmed rust          +15.7
        clean field              +1.5
        what v2.0 ADDED          +0.0     <- colder than clean metal

    i.e. v2.0's addition there was shadow, not corrosion, and it was worth
    11.1 pp on that panel. Under v2.1 the added region measures +3.8, warmer
    than the clean field, and the blob is gone on render.

    Effect on that batch (set means, v2.0 -> v2.1):
        2A 10.5 -> 7.0    3A  5.4 -> 5.3    4A 35.3 -> 36.6   5A 33.8 -> 34.7
        2B  5.3 -> 5.8    3B  5.0 -> 4.8    4B 34.2 -> 35.1   5B 39.1 -> 40.3
    Rankings and conclusions were unchanged, but the largest apparent
    difference in the experiment (2A vs 3A, +5.1 pp) was mostly artifact and
    fell to +1.7 pp.

    THE CONNECTIVITY GATE IS LOAD-BEARING, as in v1.5 and v2.0. Do not
    remove it.

    KNOWN LIMITATION -- near-black oxide is still undercounted, and this is a
    CAPTURE limitation, not a tuning one. Two further fixes were built on
    this batch and both were rejected ON RENDER:

      - a warm-bias recovery pass (warm > 6, sat > 0.12, rust hue,
        connectivity-gated) recovers thin bleed but not the near-black band,
        and it picks up droplet shadow;
      - a relaxed darkness cutoff (0.78-0.92) with a minimum-component-size
        gate does reach the band, and at the same settings paints a
        full-height stripe down both edges of the near-clean guard panels.

    The reason no threshold works, so nobody re-derives it: in the missed
    band warm bias is +3.0 while that panel's clean field is +1.4 -- but a
    NEAR-CLEAN panel's clean field measures +3.3, higher than the rusted
    panel's band. There is no colour threshold that separates them ACROSS
    panels. At brightness 50-90 on an 8-bit phone HEIC with per-scene tone
    mapping the chroma is simply gone, and black oxide and shadow occupy the
    same place in every colour space available.

    So report those levels as LOWER BOUNDS and put it on the test-conditions
    slide. The fixes are photographic: shoot straight down from a fixed
    height with even lighting; dry a sacrificial panel at a later timepoint
    as a calibration reference; or have the operator annotate one known-oxide
    and one known-shadow region and fit the cutoffs to that ground truth.

    v2.1 numbers are NOT comparable with v2.0, v1.9 or any other version.
    """
    from skimage.morphology import reconstruction

    confirmed, _pct, pm = classify_rust_v19(rgba)
    V = rgba[..., :3].astype(np.float32).sum(axis=2) / 3.0
    ref = local_brightness_ref(V, pm, radius=radius, pct=pct)
    cand = pm & ~confirmed & (V < dark_frac * np.maximum(ref, 1))

    seed = np.zeros(V.shape, np.float32)
    mask_img = np.zeros(V.shape, np.float32)
    seed[confirmed] = 1.0
    mask_img[confirmed | cand] = 1.0
    if mask_img.any() and confirmed.any():
        grown = reconstruction(seed, mask_img, method='dilation') > 0.5
    else:
        grown = confirmed.copy()
    grown &= pm
    pct_out = 100.0 * grown.sum() / max(pm.sum(), 1)
    if return_parts:
        return grown, pct_out, pm, confirmed, cand
    return grown, pct_out, pm


def bare_fraction(rgba, sat_max=BARE_SAT_MAX, val_min=BARE_VAL_MIN):
    """Fraction of the panel matching the clean bare-metal signature.

    Used as the objective selector between v1.5 and v1.6 -- it measures
    how much clean metal is actually left rather than relying on a visual
    'looks majority corroded' judgement call.
    """
    pm = rgba[..., 3] > 10
    hue, sat, val = hsv_channels(rgba[..., :3])
    bare = pm & (sat < sat_max) & (val > val_min)
    return bare.sum() / max(pm.sum(), 1) * 100


# --- Substrate detection (added at skill_version 2.7) ---
# Detects bright steel vs dark cast iron WITHOUT assuming the panel is
# clean, by looking only at the DULL pixels (sat < SUBSTRATE_PROBE_SAT).
# Those are clean metal on either substrate; corrosion is saturated on
# both. The question then reduces to whether that clean population is
# bright (steel) or dark (cast iron), which is the axis that inverts.
#
# THE ABSTAIN RULE IS LOAD-BEARING. A panel with essentially no clean
# metal left has no clean population to measure, and whatever few dull
# pixels remain are unrepresentative -- measured on AN26_0409 4A_1
# (visually ~fully corroded, 1.1% dull) those stragglers read val p50
# 0.624, which would have voted STEEL on a cast iron coupon and routed the
# batch to the wrong classifier. So below SUBSTRATE_MIN_DULL_FRAC the
# panel returns None and casts no vote, rather than guessing.
SUBSTRATE_PROBE_SAT = 0.28
SUBSTRATE_MIN_DULL_FRAC = 0.02
SUBSTRATE_VAL_CUT = 0.55


def detect_substrate(rgba):
    """Return (substrate, diagnostics). substrate is "steel", "cast_iron",
    or None when the panel is too corroded to judge (see abstain rule)."""
    pm = rgba[..., 3] > 10
    hue, sat, val = hsv_channels(rgba[..., :3])
    dull = pm & (sat < SUBSTRATE_PROBE_SAT)
    frac = dull.sum() / max(pm.sum(), 1)
    diag = {"dull_frac": float(frac), "dull_val_p50": None}
    if frac < SUBSTRATE_MIN_DULL_FRAC or dull.sum() < 500:
        return None, diag
    vm = float(np.median(val[dull]))
    diag["dull_val_p50"] = vm
    return ("steel" if vm > SUBSTRATE_VAL_CUT else "cast_iron"), diag


def detect_substrate_batch(panels):
    """Consensus substrate across a batch. `panels` is an iterable of RGBA
    arrays. A batch is one substrate, so abstaining panels ride along with
    the confident ones -- which is what lets a fully-corroded coupon be
    classified correctly using its clean siblings as the evidence.

    Raises if no panel is confident, or if confident panels disagree.
    Neither is guessable and both mean the operator should set SUBSTRATE
    explicitly.
    """
    votes = {}
    for p in panels:
        sub, _d = detect_substrate(p)
        if sub:
            votes[sub] = votes.get(sub, 0) + 1
    if not votes:
        raise ValueError(
            "substrate detection abstained on every panel (all too corroded "
            "to show clean metal). Set SUBSTRATE explicitly in run_all.py.")
    if len(votes) > 1:
        raise ValueError(
            "substrate detection disagreed across the batch (%r). A batch "
            "should be one substrate. Set SUBSTRATE explicitly." % votes)
    return next(iter(votes))


# --- Cast-iron / dark-substrate calibration (added at skill_version 2.7) ---
# MEASURED from the known-clean central field of the AN26_0409 6A coupons
# (gray cast iron, precut rod stock polished to 240 grit per AN_063026_2):
#   clean 6A_2: sat p50 0.070, p95 0.153, p99 0.224 | val p50 0.294
#   clean 6A_1: sat p50 0.092, p95 0.231, p99 0.261 | val p50 0.306
#   rusted 4A_1:            sat p50 0.542           | val p50 0.655
#
# NOTE THE INVERSION relative to the steel Q-panel constants above. On
# bright steel, clean metal is BRIGHT (val p1 0.776) and corrosion is
# darker; on dark 240-grit cast iron, clean metal is DARK (val ~0.30) and
# rust is BRIGHT (val ~0.66). BARE_VAL_MIN=0.62 therefore matches almost
# nothing on cast iron: bare_fraction() returns 0.2-0.6% on every coupon
# INCLUDING visually clean ones, classify_rust_auto routes them all to
# v1.6, and v1.6 reports ~99.9% rust on clean metal. Confirmed on all five
# AN26_0409 A-set coupons.
#
# Value is unusable as a discriminator here (a burnished//specular band on
# clean iron reaches val 0.88, brighter than much real rust), so v1.7 uses
# SATURATION ALONE. That works because saturation separates the two
# populations with a real gap on this substrate, including within the dark
# pixels specifically: dark (val<0.40) regions on the corroded 5A coupons
# read sat 0.37-0.46 at hue ~27 (dark oxide/magnetite), while dark regions
# on the clean 6A coupons read sat 0.07-0.09 at hue 48-60. So a saturation
# cutoff picks up dark oxide -- the thing v1.3 misses -- without flagging
# clean metal.
#
# The 0.28 cutoff sits just above the measured clean p99 (0.261). That
# margin is TIGHTER than the steel case (0.101 p99 -> 0.16 cutoff) because
# the burnished band broadens the clean tail. Re-measure against a
# known-clean coupon if the polish grit, lighting, or camera changes.
BARE_SAT_MAX_CI = 0.28
# Drop rust components smaller than this fraction of panel area. Isolated
# specks at this scale are polish-scratch shadow and edge artifact, not
# corrosion worth reporting. Set to 0 to disable.
RUST_MIN_AREA_FRAC = 0.005


def _drop_specks(rust_mask, pm, min_area_frac):
    if not rust_mask.any():
        return rust_mask
    n, lbl, stats, _c = cv2.connectedComponentsWithStats(
        rust_mask.astype(np.uint8), connectivity=8)
    keep = np.zeros_like(rust_mask)
    thresh = min_area_frac * pm.sum()
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= thresh:
            keep[lbl == i] = True
    return keep
BARE_RIM_PX_CI = 14


def bare_fraction_ci(rgba, sat_max=BARE_SAT_MAX_CI):
    """Fraction of a dark-substrate panel matching the clean cast-iron
    signature. Saturation-only -- see the calibration note above for why
    value is not used on this substrate."""
    pm = rgba[..., 3] > 10
    hue, sat, val = hsv_channels(rgba[..., :3])
    return (pm & (sat < sat_max)).sum() / max(pm.sum(), 1) * 100


def classify_rust_v17(rgba, sat_max=BARE_SAT_MAX_CI, rim_px=BARE_RIM_PX_CI,
                      rim_correct=True, min_area_frac=RUST_MIN_AREA_FRAC):
    """v1.7: inverse bare-metal detection for DARK substrates (gray cast
    iron), against a measured saturation-only clean signature.

    Same inverse formulation as v1.6 -- find clean metal, call the rest
    rust -- but the clean test is `sat < 0.28` with no value term, because
    on cast iron the value channel is inverted and non-separable (see the
    calibration note above). Rim correction is retained from v1.6 to kill
    the beveled-edge shading artifact.

    Use for cast iron and other dark machined substrates. Do NOT use on
    bright steel Q-panels -- there, clean metal is bright and a
    saturation-only test will flag the darker corrosion correctly but also
    lose v1.6's value-based separation of glare. Select it explicitly via
    classify_rust_auto(substrate="cast_iron"), not by eye.
    """
    pm = rgba[..., 3] > 10
    hue, sat, val = hsv_channels(rgba[..., :3])
    bare = pm & (sat < sat_max)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    bare = cv2.morphologyEx(bare.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
    rust_mask = pm & ~bare
    if rim_correct:
        rust_mask = _rim_correct(rust_mask, pm, rim_px=rim_px)
    if min_area_frac:
        rust_mask = _drop_specks(rust_mask, pm, min_area_frac)
    pct = rust_mask.sum() / max(pm.sum(), 1) * 100
    return rust_mask, pct, pm


def classify_rust_auto(rgba, majority_cut=50.0, substrate="steel"):
    """Pick v1.5 or v1.6 by how much clean bare metal remains.

    Returns (rust_mask, pct, pm, method_str) -- note the 4-tuple, unlike
    the other classifiers' 3-tuple.

    Below `majority_cut` percent bare metal the panel is majority
    corroded and v1.6 (inverse) is the right formulation; above it, clean
    metal still dominates and v1.5 (rust-forward + stain recovery) is.
    Validated on the 13-panel AN26 thermal-aging batch 2: the split fell
    at 35CD/8030/8080 -> v1.5 (bare 53-96%) and 758/Control -> v1.6
    (bare 1-43%), matching per-panel visual QA in every case.
    """
    if substrate == "cast_iron":
        # Dark substrate: the steel bare-metal signature does not transfer
        # (see the BARE_SAT_MAX_CI calibration note). v1.7 is the whole
        # selection -- there is no second method to choose between here,
        # and bare_fraction() must NOT be consulted, since it reads ~0 on
        # clean cast iron and would silently route to v1.6.
        rust_mask, pct, pm = classify_rust_v17(rgba)
        return rust_mask, pct, pm, "v1.7"
    if substrate != "steel":
        raise ValueError("unknown substrate %r (expected 'steel' or 'cast_iron')" % substrate)
    bf = bare_fraction(rgba)
    if bf < majority_cut:
        rust_mask, pct, pm = classify_rust_v16(rgba)
        return rust_mask, pct, pm, "v1.6"
    rust_mask, pct, pm = classify_rust_v15(rgba)
    return rust_mask, pct, pm, "v1.5"


# HOUSE OVERLAY STYLE, all substrates and all chambers (2.10).
# Soft red blended into the specimen rather than replacing it, so corrosion
# morphology reads through. Introduced for cast iron at 2.7 because a
# near-fully-corroded coupon renders as a featureless disc under flat red,
# extended to wet steel at 2.9, and made universal at 2.10 on the
# operator's decision -- the same argument applies to a 90%-rusted steel
# control, and one style across the project beats per-method styling.
#
# CONSEQUENCE, state it when handing over a rebuild: decks built at 2.10+
# are NOT visually comparable with steel decks delivered before it. The
# numbers are unaffected -- this is presentation only.
OVERLAY_COLOR = (255, 85, 85)
OVERLAY_OPACITY = 0.45

# Pre-2.10 flat red. Retained ONLY to reproduce a specific older steel deck
# on request; not the default, and not for new work.
OVERLAY_COLOR_LEGACY = (255, 0, 0)
OVERLAY_OPACITY_LEGACY = 0.9

# Aliases kept so existing callers keep working; identical to the house
# style since 2.10 made the blended overlay universal.
OVERLAY_COLOR_CI = OVERLAY_COLOR
OVERLAY_OPACITY_CI = OVERLAY_OPACITY


def make_overlay(rgba, rust_mask, color=OVERLAY_COLOR, opacity=OVERLAY_OPACITY,
                 blend=True):
    """Draw the rust mask over a panel.

    Two modes, because the steel and cast-iron house styles differ (2.7):

    - `blend=True` (DEFAULT since 2.10, all substrates): mix `color` into
      the pixel at `opacity` and keep the specimen's own alpha, so
      corrosion texture reads through.
    - `blend=False` (pre-2.10 flat red): REPLACE the pixel with `color` and
      set its alpha to `opacity`. Retained only to reproduce a specific
      older steel deck. Do not "simplify" the two paths together --
      blending at 0.9 looks nearly identical but is not the same output.
    """
    if blend:
        out = rgba.copy().astype(np.float32)
        for c in range(3):
            out[..., c] = np.where(rust_mask,
                                   (1 - opacity) * out[..., c] + opacity * color[c],
                                   out[..., c])
        out[..., 3] = rgba[..., 3]
        return np.clip(out, 0, 255).astype(np.uint8)

    out = rgba.copy()
    for c in range(3):
        out[..., c] = np.where(rust_mask, color[c], out[..., c])
    out[..., 3] = np.where(rust_mask, int(opacity * 255), rgba[..., 3])
    return out


# --- Warm-lit / high-shadow cast-iron calibration (v1.8) ------------------
# Derived on AN26_0409 B-set (24h IEC 60068-2-30), gray cast iron, against
# ground truth supplied by the operator: 5B_2 and 6B_2 rust-free, 4B_1,
# 4B_2, 5B_1, 6B_1 heavily rusted.
#
# WHY v1.7 FAILS ON THIS BATCH, in both directions (measured):
#   - 6B_2 (rust-free) read 53.2%. 50.6 of those 53.2 pp are NOT rust-hued
#     (hue p50 196 deg, blue) at val p50 0.11 -- the deeply shadowed half
#     of the disc. sat = (max-min)/max is numerically unstable as max
#     approaches 0, so a saturation-only clean test reads shadow as
#     corrosion. 50.7% of that coupon is coloured-but-near-black.
#   - 6B_1 (heavily rusted) read 5.8%. Its corrosion is fine pitting at
#     sat p50 0.19, under v1.7's 0.28 cutoff, and the 0.5% minimum-
#     component filter then removed a further 17.0 pp of genuine pit
#     clusters.
#
# HUE is the discriminator that holds here, and it agrees with the
# populations recorded in the v1.7 note (corroded ~27 deg, clean iron
# 48-60 deg). Measured on lit (val>0.18), coloured (sat>0.14) pixels:
#   rusted coupons: hue p50 19-27 deg
#   clean coupons:  hue p50 38-39 deg  (the burnished band)
#   shadow, both:   hue p50 ~190 deg   (excluded by the value floor)
#
# CUTOFF SELECTION: 3-way sweep, hue_max 28-36 x sat_min 0.12-0.18 x
# val_min 0.14-0.22, scored on separation between the two declared-clean
# and four declared-rusted coupons, with the two A-set clean coupons
# (6A_1, 6A_2, photographed under the DIFFERENT A-set lighting) held out
# as an independent check. hue_max is the sensitive term:
#   hue_max 28 -> clean 0.00/0.01, held-out clean 0.03/0.19, rusted 34.7-57.3
#   hue_max 30 -> clean 0.11/0.24, held-out clean 0.93/0.58, rusted 45.3-63.5
#   hue_max 32 -> clean 0.43/0.70, held-out clean 3.16/0.91, rusted 50.2-68.9
# 30 is the knee: it recovers ~9 pp more rust than 28 while every one of
# the four clean references stays under 1%. Past 30 the held-out clean
# coupon climbs fast for a smaller rust gain.
#
# The 0.5% speck filter (RUST_MIN_AREA_FRAC) is deliberately NOT applied:
# on fine-pit corrosion it deletes real rust (17.0 pp on 6B_1). Rim
# correction IS kept.
#
# NOT interchangeable with v1.7 -- numbers from the two are not
# comparable, and v1.8 is selected EXPLICITLY (CLASSIFIER = "v1.8"), never
# by auto-routing, because lighting is not safely detectable from a
# possibly-fully-corroded coupon. Re-measure against a known-clean coupon
# if lighting, polish grit or camera changes.
RUST_HUE_MIN_WARM = 5.0
RUST_HUE_MAX_WARM = 30.0
RUST_SAT_MIN_WARM = 0.14
RUST_VAL_MIN_WARM = 0.18


def classify_rust_v18(rgba, hue_min=RUST_HUE_MIN_WARM, hue_max=RUST_HUE_MAX_WARM,
                      sat_min=RUST_SAT_MIN_WARM, val_min=RUST_VAL_MIN_WARM,
                      rim_px=BARE_RIM_PX_CI, rim_correct=True):
    """v1.8: FORWARD rust detection for dark cast iron photographed with
    warm light and strong shadow. Rust must be rust-hued AND saturated AND
    above a value floor; the value floor is what excludes the near-black
    region where saturation carries no information. See the calibration
    note above for the measured v1.7 failure this replaces.
    """
    pm = rgba[..., 3] > 10
    hue, sat, val = hsv_channels(rgba[..., :3])
    rust_mask = (pm & (hue >= hue_min) & (hue <= hue_max)
                 & (sat > sat_min) & (val > val_min))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    rust_mask = cv2.morphologyEx(rust_mask.astype(np.uint8),
                                 cv2.MORPH_OPEN, k).astype(bool)
    if rim_correct:
        rust_mask = _rim_correct(rust_mask, pm, rim_px=rim_px)
    pct = rust_mask.sum() / max(pm.sum(), 1) * 100
    return rust_mask, pct, pm


# --- Wet-exposure steel calibration (v1.9, AN26_0502) --------------------
# Steel panels photographed WET, straight out of a water-fog cabinet
# (D1735). Condensation covers the whole panel, and the film of water over
# clean metal carries a weak warm tint that lands inside the rust hue
# window at low saturation. v1.3's droplet defences (Stage 1 hue + 0.15
# saturation floor, round-blob rejection) handle scattered droplets on a
# dry panel; they do not handle a panel that is uniformly wet.
#
# MEASURED (3B t=48h panel 4, operator-identified false positive region):
#   flagged pixels in the wet region: hue p50 30.0, sat p50 0.190,
#     86% below sat 0.30
#   flagged pixels in the genuinely rusted band: hue p50 37.7, sat p50 0.316
# The adaptive Otsu threshold had bottomed out at v1.3's 0.22 floor, and
# the two growth stages (floors 0.15 and 0.16) then added 11.8 pp on top.
#
# CUTOFF SELECTION: floors swept together against the operator-identified
# wet region, the known-rusted controls, and the 2h coated panels (visually
# clean). base/stage1/stage2:
#   0.22/0.15/0.16 (v1.3) -> wet region 26.4% | Ctrl 48h 94.0 | Ctrl 144h 82.4
#   0.26/0.20/0.20        -> wet region  6.2% | Ctrl 48h 93.7 | Ctrl 144h 82.2
#   0.28/0.22/0.22        -> wet region  5.1% | Ctrl 48h 93.5 | Ctrl 144h 82.1
#   0.32/0.26/0.26        -> wet region  3.5% | Ctrl 48h 91.8 | Ctrl 144h 81.7
# 0.28/0.22/0.22 is the knee: it removes ~80% of the false positive for
# 0.5 pp off the rusted controls. Past it the controls start paying.
#
# Select EXPLICITLY (CLASSIFIER = "v1.9"). Not auto-routed: whether panels
# were photographed wet is a fact about the photography, not something
# recoverable from the pixels. Numbers are not comparable to v1.3.
WET_FLOOR = 0.28
WET_STAGE1_FLOOR = 0.22
WET_STAGE2_FLOOR = 0.22


def classify_rust_v19(rgba, floor=WET_FLOOR, s1_floor=WET_STAGE1_FLOOR,
                      s2_floor=WET_STAGE2_FLOOR, lower_by=0.12):
    """v1.9: v1.3 with all three saturation floors raised for wet steel.

    Structurally identical to classify_rust_v13 -- same v1.1 base, same
    Stage 1 dark-rust pass with its blob filters, same Stage 2
    morphological gap-fill. Only the saturation floors differ. Use for
    steel panels photographed wet; use v1.3 for dry panels with scattered
    droplets.
    """
    from skimage.morphology import reconstruction, label
    from skimage.measure import regionprops

    pm = rgba[..., 3] > 10
    hue, sat, val = hsv_channels(rgba[..., :3])
    in_hue = (hue >= 10) & (hue <= 55) & pm
    sats = sat[in_hue]
    t = floor if len(sats) == 0 else max(otsu_threshold(sats) - lower_by, floor)
    v11 = (sat > t) & in_hue

    val255 = val * 255.0
    residual = val255 - cv2.GaussianBlur(val255, (0, 0), sigmaX=15)
    dark = (residual < -12) & pm & in_hue & (sat > s1_floor) & ~v11
    stage1 = np.zeros_like(v11)
    if dark.any():
        lbl = label(dark, connectivity=2)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        dil = cv2.dilate(v11.astype(np.uint8), k, iterations=1).astype(bool)
        for r in regionprops(lbl):
            if r.area < 30:
                continue
            per = r.perimeter if r.perimeter > 0 else 1e-6
            if r.area < 150 and 4 * np.pi * r.area / (per ** 2) > 0.7:
                continue
            c = r.coords
            if not dil[c[:, 0], c[:, 1]].any():
                continue
            stage1[c[:, 0], c[:, 1]] = True

    confirmed = v11 | stage1
    gap = ((hue >= 10) & (hue <= 55) & (sat > s2_floor)
           & (residual < -4) & pm & ~confirmed)
    seed = np.zeros_like(val255); mask_img = np.zeros_like(val255)
    seed[confirmed] = 1.0; mask_img[confirmed | gap] = 1.0
    if mask_img.any():
        stage2 = (reconstruction(seed, mask_img, method='dilation') > 0.5) & gap
    else:
        stage2 = np.zeros_like(confirmed)

    rust_mask = confirmed | stage2
    pct = rust_mask.sum() / max(pm.sum(), 1) * 100
    return rust_mask, pct, pm
