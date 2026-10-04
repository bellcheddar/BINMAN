# Gate G6 open

Opened at 2026-10-04T00:17:37+00:00.

## What is needed

A decision on whether to ship the Degron Scan at all, now that spec 9.2 is measured and fails.

Sensitivity 0.656 against a floor of 0.70, specificity 0.353 against a floor of 0.60, ROC AUC 0.441 -- below chance -- on 32 depleted and 5,476 matched non-depleted zinc fingers from Sievers et al. 2018. The filter calls 3,544 of the 5,476 negatives. No cut on degron_geometry_score clears both floors (best Youden's J = 0.022), and spec 9.6's single threshold adjustment was already spent on D-010, so no second adjustment was made.

Diagnosis: a C2H2 zinc finger is itself a short antiparallel hairpin with an exposed glycine-bearing turn, so the spec 5.2 geometry describes the domain family rather than degradability. The canonical neosubstrates (IKZF3, ZFP91, E4F1) are recovered, but twelve non-degraded zinc fingers outrank all three.

The default taken, per spec 9.2's own instruction for this case, is to keep the module and relabel it a hypothesis generator rather than a classifier, with the measured numbers on its face. The alternative is to drop the module from the shipped app.

## What unblocks it

```bash
pixi run python -m pipeline.validate --section 9.2
```

## Already done

Sievers et al. 2018 data files S2 and S6 acquired, pooled and wired in as the sievers_zf_screen dataset; spec 9.2 sensitivity, specificity, full contingency table, ROC AUC and a complete threshold sweep computed and written to FINDINGS.md; DECISIONS D-024 records the reasoning and the reversal condition; the module, the README and the app are relabelled as a hypothesis generator.

## What happens next

Nothing is blocked. The build continues with the module shipped and flagged. Marc's call: accept the flagged caveat, or drop the Degron Scan from the app. To make it a classifier instead, add a feature that separates degraded from non-degraded zinc fingers within the C2H2 family -- degron sequence context, CRBN interface complementarity, or Zn-coordination geometry -- and re-run against the same matched set.
