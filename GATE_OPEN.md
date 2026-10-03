# Gate G7 open

Opened at 2026-10-03T23:14:24+00:00.

## What is needed

2 validation dataset(s) could not be obtained automatically: degronopedia, protcid_interfaces.

Each publishes through a JavaScript front end with no documented bulk-export endpoint, or sits behind registration. Spec 4.1b forbids substituting a hand-written control, so the metrics that depend on these are reported as not computed.

See data/validation/MANIFEST.md for the homepage and citation of each, and the exact outcome of every route tried.

## What unblocks it

```bash
# download each file by hand from its homepage, then:
#   mv <file> data/validation/raw/<dataset_name>
pixi run python pipeline/acquire_validation.py --refresh
```

## Already done

9 dataset(s) resolved and parsed: biolip2_annotations, biolip2_artefacts, mgdb_glues, mgtbind_compounds, mgtbind_ternary, molgluedb_glues, protacdb_protacs, ubibrowser_literature_e3, ubibrowser_predicted_e3. Row counts, licences and retrieval timestamps are recorded in data/validation/MANIFEST.md.

## What happens next

G7 is non-blocking by spec. The build continues with the datasets that resolved. Section 9 metrics that depend on a missing dataset are reported as 'not computed: dataset unavailable' in FINDINGS.md, never estimated.
