# panel-rust-analysis skill_version: 2.10 -- must match SKILL.md's
# skill_version, the repo copy, and the panel-rust-analysis line in
# PROJECT_CANON.md. If it is out of sync with any of those, this file has
# reverted to a stale snapshot: run from the repo clone instead of this
# copy (see SKILL.md's VERSION CHECK section) rather than trusting it.
"""
Significance testing between sets for a rust-analysis batch.

Added at skill_version 2.10. OPTIONAL -- run only when the person asks for
it (see SKILL.md "Intake", question 8). Writes stats.json, consumed by
build_deck_template.js to add a statistics slide per timepoint.

WHAT TEST AND WHY
-----------------
**Welch's t-test**, not Student's. Corrosion replicate groups routinely have
very different variances -- an uncoated control can spread 1% to 20% while a
coated set sits at 0.3 +/- 0.1 -- and Student's t assumes equal variance.
Welch does not, and costs almost nothing when variances happen to match.

**Holm-Bonferroni correction across the comparisons within one timepoint.**
Four sets give six pairwise comparisons; at alpha 0.05 uncorrected there is
roughly a 26% chance of at least one false positive per timepoint, and a
batch with six timepoints would produce them reliably. Holm is uniformly
more powerful than plain Bonferroni and needs no extra assumptions.

**Hedges' g** is reported alongside p. With n=3 vs n=5 a real difference can
miss significance purely on sample size, and a tiny difference can clear it
if variances are small. The effect size says how big the difference is; the
p-value says how confident we are it is not noise. Report both -- neither
alone answers "does this coating matter".

HONEST LIMITS -- these belong in any write-up that quotes these numbers
----------------------------------------------------------------------
1. **n=3 and n=5 is very small.** Welch on these sizes has low power: a
   coating genuinely twice as good as another will often fail to reach
   p<0.05. A non-significant result here means "not demonstrated", NOT
   "no difference".
2. **Percentages are bounded at 0 and 100 and are not normal**, especially
   when a set is near either end. A set reading 0.0, 0.0, 0.1, 0.0, 0.1 has
   almost no variance, which inflates t. Where every value in both groups
   sits below `NEAR_ZERO_PCT`, this module flags the comparison rather than
   pretending the test is meaningful.
3. **Replicates are panels in one chamber run, not independent runs.**
   Anything affecting a whole run -- position in the cabinet, one bad spray
   pass -- is shared by every panel and is invisible to this test. It
   measures panel-to-panel variability within a run, and does not license
   claims about run-to-run reproducibility.
4. **Timepoints are not independent of each other** (the same panels are
   photographed repeatedly), so the correction is applied WITHIN a
   timepoint only. Do not read six timepoints as six independent
   confirmations.
"""
import json
import itertools
import numpy as np
from scipy import stats as sps

ALPHA = 0.05
# Below this, a "set" is effectively clean and a significance test on the
# noise between two clean sets is not meaningful, however small the p-value.
NEAR_ZERO_PCT = 0.5


def hedges_g(a, b):
    """Bias-corrected standardised mean difference."""
    na, nb = len(a), len(b)
    sa, sb = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = np.sqrt(((na - 1) * sa + (nb - 1) * sb) / max(na + nb - 2, 1))
    if pooled == 0:
        return float("nan")
    d = (np.mean(a) - np.mean(b)) / pooled
    J = 1 - 3 / (4 * (na + nb) - 9)          # small-sample correction
    return float(d * J)


def holm(pvals):
    """Holm-Bonferroni adjusted p-values, order preserved."""
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    adj = [0.0] * n
    running = 0.0
    for rank, i in enumerate(order):
        val = (n - rank) * pvals[i]
        running = max(running, val)          # enforce monotonicity
        adj[i] = min(1.0, running)
    return adj


def compare_sets(results, control=None):
    """All pairwise Welch comparisons within one timepoint.

    `results` is the {set: {"method":..., "pct":[...]}} mapping from
    full_results.json. `control` names the reference set, if any, so it can
    be marked in the output; every pair is tested regardless.
    """
    labels = list(results.keys())
    rows = []
    for a, b in itertools.combinations(labels, 2):
        va, vb = np.array(results[a]["pct"], float), np.array(results[b]["pct"], float)
        note = ""
        if len(va) < 2 or len(vb) < 2:
            rows.append({"a": a, "b": b, "n_a": len(va), "n_b": len(vb),
                         "mean_a": float(va.mean()), "mean_b": float(vb.mean()),
                         "p_raw": None, "g": None,
                         "note": "n<2, no test possible"})
            continue
        if va.max() < NEAR_ZERO_PCT and vb.max() < NEAR_ZERO_PCT:
            note = "both sets effectively clean (<%.1f%%); difference not meaningful" % NEAR_ZERO_PCT
        t, p = sps.ttest_ind(va, vb, equal_var=False)   # Welch
        rows.append({"a": a, "b": b, "n_a": int(len(va)), "n_b": int(len(vb)),
                     "mean_a": float(va.mean()), "mean_b": float(vb.mean()),
                     "sd_a": float(va.std(ddof=1)), "sd_b": float(vb.std(ddof=1)),
                     "p_raw": float(p), "g": hedges_g(va, vb),
                     "vs_control": control in (a, b), "note": note})

    testable = [r for r in rows if r["p_raw"] is not None]
    adj = holm([r["p_raw"] for r in testable]) if testable else []
    for r, pa in zip(testable, adj):
        r["p_adj"] = float(pa)
        r["significant"] = bool(pa < ALPHA and not r["note"])
    for r in rows:
        r.setdefault("p_adj", None)
        r.setdefault("significant", False)
    return rows


def analyse(per_timepoint, control=None, out="stats.json"):
    """per_timepoint: {timepoint: results-dict}. Writes stats.json."""
    out_obj = {"alpha": ALPHA, "test": "Welch t-test, Holm-corrected within timepoint",
               "near_zero_pct": NEAR_ZERO_PCT, "control": control, "timepoints": {}}
    for tp, res in per_timepoint.items():
        out_obj["timepoints"][tp] = compare_sets(res, control=control)
    with open(out, "w") as f:
        json.dump(out_obj, f, indent=2)
    return out_obj


if __name__ == "__main__":
    import sys
    tps = sys.argv[1:]
    per = {tp: json.load(open(f"full_{tp}.json")) for tp in tps}
    o = analyse(per, control="Control")
    for tp, rows in o["timepoints"].items():
        print(f"--- t={tp}")
        for r in rows:
            p = "n/a" if r["p_adj"] is None else f"{r['p_adj']:.4f}"
            g = "n/a" if r["g"] is None or np.isnan(r["g"]) else f"{r['g']:+.2f}"
            print(f"  {r['a']:>8} vs {r['b']:<8} {r['mean_a']:6.2f} vs {r['mean_b']:6.2f} "
                  f"p_adj={p:>8} g={g:>7} {'SIG' if r['significant'] else '   '} {r['note']}")
