# panel-rust-analysis skill_version: 2.2 -- must match SKILL.md's
# skill_version and the version recorded in memory. If this number looks
# out of sync with either, this file has likely reverted to a stale
# snapshot -- see SKILL.md's persistence-warning section before trusting
# anything below.
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
    residual on the value channel, cutoff -12 on the 0-255 scale), filters
    out small isolated blobs (<30px) and round blobs (<150px area AND
    circularity>0.7 -- these are water droplets, not rust), and only keeps
    components that lie within 7px of the v1.1 rust mask (dark rust should
    be touching/near confirmed rust, not scattered noise).

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
    dark_candidate = (residual < -12) & pm & in_hue & ~v11_mask

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


def make_overlay(rgba, rust_mask, color=(255,0,0), opacity=0.9):
    out = rgba.copy()
    alpha = out[...,3].astype(np.float32)/255.0
    overlay_alpha = np.where(rust_mask, opacity, 0.0)
    for c in range(3):
        out[...,c] = np.where(rust_mask, color[c], out[...,c])
    out[...,3] = np.clip(overlay_alpha*255 + (1-overlay_alpha)*0, 0, 255).astype(np.uint8)
    # keep original panel visible where not rust: use original alpha there
    out[...,3] = np.where(rust_mask, (opacity*255), rgba[...,3])
    return out
