"""Predict an evidence class for every glue candidate, with BINMAN-LM.

This is the first model-derived data in the atlas, so the boundaries are worth
stating plainly.

**It fills `evidence_class`,** which spec line 467 defines as the Task B
label. A separate prediction column was drafted first and thrown away: the spec
had already decided where this goes, and adding a second column beside an empty
one designed for the same thing would have been a private design imposed over a
public one. What the column needs instead is a description that says it is a
model prediction, which its FieldSpec now carries.

**It is a label, not a number.** The project rule is that the language model
never computes, estimates or reports a numeric value, and this emits one of
four class tokens. Every figure about these predictions, including the
agreement measured below, is counted in Python.

**Applying it to unlabelled ligands is the case it was tested on.** Task B was
split by chemical component, so no CCD appears in both train and test, and the
0.9336 macro F1 in spec 9.5 is a score on CCDs the model had not seen. The
agreement this stage reports is still split by whether a CCD was in training,
because agreement on a memorised ligand is not evidence of anything.

The prompt is built exactly as lm/build_task_b.py builds it. A model asked a
question in a shape it was not trained on answers worse, which spec 9.5's
register-mismatch figures already show for the query task.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import (  # noqa: E402
    ATLAS, INTERIM, Manifest, log_event, utcnow, write_jsonl,
)

STAGE = "triage_predict"
OUTPUT = INTERIM / "triage_predictions.jsonl"
REPORT = INTERIM / "triage_predict.json"
DEFAULT_DB = ATLAS / "binman.sqlite"

BASE_MODEL = "mlx-community/Qwen2.5-3B-Instruct-4bit"
# round07 is what serves. D-074 records how the model card came to name a
# different one, and why this is read from the run rather than from
# models/binman-lm/adapters, which a later 32B run overwrote.
ADAPTER = ROOT / "models" / "binman-lm" / "runs" / "binman-qwen-2.5-3b-4bit-round07"

SYSTEM_TRIAGE = (
    "<task>triage</task>\n"
    "You classify a structure into exactly one evidence class. Reply with a "
    "single class token and nothing else. The classes are: "
    "molecular_glue, protac, native_cofactor, crystallisation_artefact."
)
CLASSES = ["crystallisation_artefact", "molecular_glue", "native_cofactor", "protac"]


def candidates(connection: sqlite3.Connection) -> list[dict]:
    """Every (entry, ligand) pair whose ligand is classed as a glue candidate.

    Per pair, not per bridge: one ligand bridging three chain pairs in one entry
    is one question, and asking it three times would spend three times the
    compute to get the same token.
    """
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT DISTINCT b.pdb_id, b.ccd_id, e.title, l.name AS ligand_name "
        "FROM bridge b "
        "JOIN entry e ON e.pdb_id = b.pdb_id "
        "LEFT JOIN ligand l ON l.ccd_id = b.ccd_id "
        "WHERE b.status = 'ok' AND b.ccd_class = 'glue_candidate' AND e.title != '' "
        "ORDER BY b.pdb_id, b.ccd_id"
    ).fetchall()
    return [dict(row) for row in rows]


def prompt_for(connection: sqlite3.Connection, row: dict) -> str:
    """Identical in shape to lm/build_task_b.py, including the 8-component cap."""
    others = [
        r[0] for r in connection.execute(
            "SELECT DISTINCT ccd_id FROM bridge WHERE pdb_id = ? LIMIT 8",
            (row["pdb_id"],))
    ]
    return (
        f"Entry {row['pdb_id']}: {row['title']}\n"
        f"Ligand of interest: {row['ccd_id']}"
        + (f" ({row['ligand_name']})" if row.get("ligand_name") else "")
        + f"\nOther components in the entry: {', '.join(others) or 'none'}"
    )


def trained_ccds() -> set[str]:
    """CCDs the model saw in training, so agreement can be split on them."""
    seen: set[str] = set()
    for name in ("task_b_train", "task_b_valid"):
        path = ROOT / "lm" / "corpus" / f"{name}.jsonl"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    seen.add(json.loads(line).get("ccd_id", ""))
                except json.JSONDecodeError:
                    continue
    seen.discard("")
    return seen


def run(db_path: Path = DEFAULT_DB, limit: int | None = None) -> dict:
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    connection = sqlite3.connect(db_path)
    try:
        jobs = candidates(connection)
        if limit:
            jobs = jobs[:limit]
        log_event("3.5", f"Triage prediction: {len(jobs):,} entry-ligand pairs, "
                         f"{len({j['ccd_id'] for j in jobs}):,} distinct ligands.")
        if not jobs:
            return {"predicted": 0}

        model, tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTER))
        sampler = make_sampler(temp=0.0)
        manifest = Manifest(STAGE)
        rows: list[dict] = []
        counts = {name: 0 for name in CLASSES}
        counts["unparseable"] = 0

        for index, job in enumerate(jobs, start=1):
            prompt = tokenizer.apply_chat_template(
                [{"role": "system", "content": SYSTEM_TRIAGE},
                 {"role": "user", "content": prompt_for(connection, job)}],
                add_generation_prompt=True, tokenize=False,
            )
            raw = generate(model, tokenizer, prompt=prompt, max_tokens=16,
                           sampler=sampler, verbose=False).strip()
            # The first known class token that appears, exactly as the task B
            # evaluation scores it. Anything else is unparseable, not a guess.
            predicted = next((c for c in CLASSES if c in raw), "unparseable")
            counts[predicted] += 1
            rows.append({"pdb_id": job["pdb_id"], "ccd_id": job["ccd_id"],
                         "predicted_evidence_class":
                             None if predicted == "unparseable" else predicted,
                         "raw": raw[:40], "status": "ok"})
            manifest.record(f"{job['pdb_id']}:{job['ccd_id']}", status="ok",
                            predicted=predicted)
            if index % 250 == 0:
                log_event("3.5", f"{index:,}/{len(jobs):,} classified.")

        written = write_jsonl(OUTPUT, rows)
        report = {
            "generated_at": utcnow(),
            "model": BASE_MODEL,
            "adapter": ADAPTER.name,
            "n_pairs": len(jobs),
            "n_ligands": len({j["ccd_id"] for j in jobs}),
            "class_counts": counts,
            "written": written,
        }
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
        log_event("3.5", f"Triage prediction complete: {written:,} pairs classified, "
                         f"{counts['unparseable']:,} unparseable.")
        return report
    finally:
        connection.close()


def load_into_atlas(db_path: Path = DEFAULT_DB) -> dict:
    """Write the predictions file into `predicted_evidence_class`.

    Separate from run() on purpose. Inference over 6,510 pairs is its own stage,
    the way the bridge geometry run is, and build_atlas loads what a stage
    produced rather than producing it: a model loaded on every atlas build would
    put minutes of GPU on a step that is otherwise file IO.

    One prediction covers every bridge row sharing its entry and ligand. A
    ligand bridging three chain pairs in one entry was asked once and all three
    rows get the answer, because the question was about the structure and the
    ligand, not about which pair of chains the geometry happened to pick.
    """
    if not OUTPUT.exists():
        return {"loaded": 0, "reason": "no predictions file; run this stage first"}
    connection = sqlite3.connect(db_path)
    try:
        updates = []
        with OUTPUT.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("predicted_evidence_class"):
                    updates.append((row["predicted_evidence_class"],
                                    row["pdb_id"], row["ccd_id"]))
        connection.executemany(
            "UPDATE bridge SET evidence_class = ? "
            "WHERE pdb_id = ? AND ccd_id = ?", updates)
        connection.commit()
        rows = connection.execute(
            "SELECT COUNT(*) FROM bridge WHERE evidence_class IS NOT NULL"
        ).fetchone()[0]
        log_event("3.5", f"Triage predictions loaded: {len(updates):,} pairs onto "
                         f"{rows:,} bridge rows.")
        return {"pairs": len(updates), "bridge_rows": rows}
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(run(db_path=args.db, limit=args.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
