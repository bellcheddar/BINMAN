# BINMAN

This project is built from BINMAN_BUILD_SPEC.md, which is authoritative.

- Never stop except at a Gate (spec Section 0). Decide, log to DECISIONS.md, continue.
- Logging: BUILD_LOG.md (events), PROGRESS.md (phase checklist), DECISIONS.md (choices).
- Every stage writes data/manifests/<stage>.jsonl and is resumable and idempotent.
- Commit locally at the end of every phase. Gate G4 (push, repo creation) was
  authorised by Marc at build start: the public repo is in scope. See DECISIONS.md D-001.
- Hardware settings come from config/tuning.toml. Never hard-code cores or memory.
- Thresholds come from config/thresholds.toml. Never hard-code a cutoff in Python.
- UI design system: "Depot" (spec 6.2). The marcdeller.com house header and palette do
  NOT apply to this app UI. They do apply to the README.
- The language model never computes, estimates or reports a number. All numeric values
  are computed deterministically in Python.
- House style: British English, no em dashes (colons or parentheses), and none of:
  groundbreaking, revolutionary, paradigm-shifting, game-changing, cutting-edge,
  unprecedented, seamless, leverage (verb), delve.
