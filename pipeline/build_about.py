"""Generate the About tab (spec 6.6).

**Governing rule: the About tab is generated, never authored.** Every number,
version, citation and count is read at build time from artefacts the pipeline
already produces, and written to `app/static/about.json`. A hand-written About
page is wrong within one build and nobody notices. Where a value cannot be read
from an artefact, the page shows "not recorded" and the build logs it.

Sources read:
    data/validation/MANIFEST.md     dataset versions, licences, row counts
    data/validation/references.json Crossref-verified references
    data/validation/results.json    Section 9 metrics (when validate.py has run)
    config/thresholds.toml          every scientific cutoff
    config/tuning.toml              the derived build settings
    config/hardware.toml            what it ran on
    data/manifests/*.jsonl          per-stage counts and failures
    app/static/vendor/VENDOR.json   pinned front-end assets
    data/atlas/binman.sqlite        the shipped row counts

Writes:
    app/static/about.json           everything the template renders
    app/static/workflow.svg         the schematic, drawn from the manifests
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import (  # noqa: E402
    ATLAS, CONFIG_DIR, MANIFESTS, ROOT, VALIDATION, Manifest, load_config,
    log_event, read_jsonl, utcnow,
)

ABOUT_JSON = ROOT / "app" / "static" / "about.json"
WORKFLOW_SVG = ROOT / "app" / "static" / "workflow.svg"
VENDOR_JSON = ROOT / "app" / "static" / "vendor" / "VENDOR.json"
DB_PATH = ATLAS / "binman.sqlite"
STAGE = "build_about"

NOT_RECORDED = "not recorded"


def _json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


# --------------------------------------------------------------------------- #
# stage counts
# --------------------------------------------------------------------------- #

def stage_counts() -> dict:
    """Real counts and failure tallies per stage, read from the manifests."""
    stages = {}
    for path in sorted(MANIFESTS.glob("*.jsonl")):
        name = path.stem
        if name == "catalogue":
            # The catalogue is the data, not a manifest of it.
            rows = read_jsonl(path)
            tiers: dict[str, int] = {}
            for row in rows:
                if row.get("pdb_id"):
                    tiers[str(row.get("tier", "?"))] = tiers.get(str(row.get("tier", "?")), 0) + 1
            stages["catalogue"] = {
                "total": sum(tiers.values()), "ok": sum(tiers.values()),
                "failed": 0, "tiers": tiers,
            }
            continue
        manifest = Manifest(name)
        counts = manifest.counts()
        failures = manifest.failures()
        reasons: dict[str, int] = {}
        for row in failures:
            reason = str(row.get("status", "failed:unknown")).split(":", 2)
            label = reason[1] if len(reason) > 1 else "unknown"
            reasons[label] = reasons.get(label, 0) + 1
        stages[name] = {
            "total": counts.get("total", 0),
            "ok": counts.get("ok", 0),
            "failed": counts.get("failed", 0),
            "failure_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])[:8]),
        }
    return stages


def atlas_counts() -> dict:
    """Row counts from the shipped database, which is what the UI serves."""
    if not DB_PATH.exists():
        return {"available": False}
    out: dict = {"available": True, "size_mb": round(DB_PATH.stat().st_size / (1024 ** 2), 1)}
    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        for table in ("entry", "bridge", "ligand", "polymer_entity",
                      "degron", "ligase", "lysine", "edge"):
            try:
                out[table] = int(connection.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                out[f"{table}_failed"] = int(connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE status != 'ok'").fetchone()[0])
            except sqlite3.Error:
                out[table] = 0
        try:
            out["ccd_class_counts"] = {
                row[0]: row[1] for row in connection.execute(
                    "SELECT ccd_class, COUNT(*) FROM ligand GROUP BY ccd_class "
                    "ORDER BY COUNT(*) DESC")
            }
            out["novel_bridges"] = int(connection.execute(
                "SELECT COUNT(*) FROM bridge WHERE novel_bridge = 1").fetchone()[0])
        except sqlite3.Error:
            pass
    finally:
        connection.close()
    return out


# --------------------------------------------------------------------------- #
# datasets
# --------------------------------------------------------------------------- #

def dataset_rows() -> list[dict]:
    """Parse the validation manifest's own stage records, not the markdown.

    Reading the JSONL rather than re-parsing MANIFEST.md keeps a single source
    of truth: the markdown and this page are both renderings of the same rows.
    """
    rows = []
    for row in Manifest("validation_acquire").read():
        rows.append({
            "name": row.get("key", ""),
            "resolved": row.get("status") == "ok",
            "rows": row.get("rows", 0),
            "licence": row.get("licence", NOT_RECORDED),
            "redistributable": bool(row.get("redistributable")),
            "version": row.get("version_note", NOT_RECORDED),
            "retrieved": row.get("at", NOT_RECORDED),
            "url": row.get("url", ""),
            "homepage": row.get("homepage", ""),
            "purpose": row.get("purpose", ""),
            "citation": row.get("citation", NOT_RECORDED),
            "manual_route": row.get("manual_route", ""),
            "attempts": row.get("attempts", []),
        })
    # Keep the newest record per dataset: the stage is re-runnable.
    newest: dict[str, dict] = {}
    for row in rows:
        newest[row["name"]] = row
    return sorted(newest.values(), key=lambda r: (not r["resolved"], r["name"]))


def reference_rows() -> list[dict]:
    """The reference table (spec 6.6.3), joined from references.json."""
    payload = _json(VALIDATION / "references.json", {}) or {}
    datasets = {row["name"]: row for row in dataset_rows()}
    out = []
    for record in payload.get("references", []):
        out.append({
            "name": record.get("title") or NOT_RECORDED,
            "key": record.get("key", ""),
            "type": record.get("type", NOT_RECORDED),
            "version": record.get("version") or _dataset_version(record.get("key", ""), datasets),
            "retrieved": _dataset_retrieved(record.get("key", ""), datasets)
                         or record.get("checked_at", NOT_RECORDED),
            "used_for": record.get("used_for", NOT_RECORDED),
            "licence": record.get("licence") or "not determined",
            "doi": record.get("doi", ""),
            "home": record.get("url", ""),
            "repo": record.get("repo", ""),
            "verified": bool(record.get("verified")),
            "verification": record.get("verification", ""),
            "authors": record.get("authors", ""),
            "year": record.get("year", ""),
            "container": record.get("container", ""),
        })

    # Pinned front-end assets are software the build touched, so they belong in
    # the same table (spec 6.6.3 says every piece of software).
    vendor = _json(VENDOR_JSON, {}) or {}
    seen = {r["name"].lower() for r in out}
    for asset in vendor.get("assets", []):
        label = asset.get("name", "")
        if not label or label.lower() in seen:
            continue
        seen.add(label.lower())
        out.append({
            "name": label, "key": label.lower().replace(" ", "_"),
            "type": asset.get("type", "software"), "version": asset.get("version", NOT_RECORDED),
            "retrieved": asset.get("retrieved_at", NOT_RECORDED),
            "used_for": asset.get("used_for", NOT_RECORDED),
            "licence": asset.get("licence", "not determined"),
            "doi": "", "home": asset.get("home", ""), "repo": asset.get("repo", ""),
            "verified": False, "verification": "vendored asset, pinned by SHA-256",
            "authors": "", "year": "", "container": "",
        })
    return sorted(out, key=lambda r: (r["type"], r["name"].lower()))


def _dataset_version(key: str, datasets: dict) -> str:
    for name, row in datasets.items():
        if key and (key in name or name.startswith(key[:8])):
            return row.get("version", NOT_RECORDED)
    return NOT_RECORDED


def _dataset_retrieved(key: str, datasets: dict) -> str:
    for name, row in datasets.items():
        if key and (key in name or name.startswith(key[:8])):
            return row.get("retrieved", "")
    return ""


# --------------------------------------------------------------------------- #
# model card
# --------------------------------------------------------------------------- #

def model_card() -> dict:
    """Spec 6.6.2. Nothing on this panel is typed by hand.

    Returns `trained: False` with an explanation when Phase 3 has not run, which
    is itself a generated statement rather than a placeholder.
    """
    results = _json(VALIDATION / "results.json", {}) or {}
    lm = results.get("binman_lm") or {}
    training = _json(ROOT / "models" / "binman-lm" / "training.json", {}) or {}
    hardware = load_config().hardware

    return {
        "trained": bool(lm or training),
        "status_note": (
            "Phase 3 has not run, so there is no model to describe. "
            "The app is fully functional without it: the natural-language box is "
            "the only feature that depends on the model, and it is hidden when "
            "BINMAN_LM_URL is unset."
            if not (lm or training) else ""
        ),
        # The served model, not the last one trained. training.json is kept
        # as the record of that run, under a name that says so.
        "identity": _served_identity() or training.get("identity", {}),
        "identity_source": ("the adapter the Space loads"
                            if _served_identity() else
                            "models/binman-lm/training.json, which records the "
                            "last training run and may not be what ships"),
        "last_training_run": training.get("identity", {}),
        "training": training.get("training", {}),
        "tasks": training.get("tasks", []),
        "results": lm,
        "baseline": lm.get("baseline", {}),
        "hardware": {
            "chip": hardware.get("host", {}).get("chip", NOT_RECORDED),
            "gpu_cores": hardware.get("host", {}).get("gpu_cores", NOT_RECORDED),
            "performance_cores": hardware.get("cpu", {}).get("performance_cores", NOT_RECORDED),
            "memory_gb": hardware.get("memory", {}).get("total_gb", NOT_RECORDED),
            "mlx_version": hardware.get("mlx", {}).get("version", NOT_RECORDED),
        },
        "limits": [
            "The model never computes, estimates or reports a numeric value. "
            "Every number in BINMAN is computed deterministically in Python and "
            "passed to the interface.",
            "The vocabulary is closed: the model can only name fields, operators, "
            "ligases and classes that exist in the built atlas.",
            "The underlying databases have a training cutoff. A glue deposited "
            "after the pinned release of each curated database is not in them.",
            "Register mismatch: the synthetic test set shares a generator with the "
            "training set, so the externally authored query set is the number that "
            "matters and the gap between them is reported.",
        ],
        "availability": {
            "endpoint_live": bool(__import__("os").environ.get("BINMAN_LM_URL")),
            "note": "The app is fully functional without the model.",
        },
    }


# --------------------------------------------------------------------------- #
# worked example (spec 6.6.4)
# --------------------------------------------------------------------------- #

# The ligases with established degrader chemistry, read from the atlas rather
# than typed out here: anything the E3 module calls clinically validated,
# chemically validated or covalent-handle-only. Seventeen of the 650, and they
# are the anchors every published PROTAC and glue is built on, so a ternary
# containing one is a degrader structure whatever its title says. Excluding
# cereblon alone was not enough: the first example this picked was 7Z76,
# "compound 10 in complex with the bromodomain of human SMARCA2 and
# pVHL:ElonginC:ElonginB", which is a VHL PROTAC that never uses the word.
DEGRADER_LIGASE_STATUS = (
    "clinically validated", "chemically validated", "covalent handle only")

# A deposited title that says what the structure is. The curated databases
# catch the entries somebody has already written up as glues; these catch the
# ones whose depositors said so in the title but which no database has indexed
# yet. Matched case-insensitively against the entry title.
DEGRADER_WORDS = ("protac", "degrader", "bifunctional", "cereblon", "crbn",
                  "molecular glue", "glue", "ternary complex")

CRITERIA = [
    ("passes_bridging_filter", "passes the bridging filter"),
    ("balance_above_threshold", "bridging balance above the strong threshold"),
    ("substrate_has_degron", "its substrate carries a degron found by the Phase 2 scan"),
    ("ligase_has_pocket_score", "its ligase has a pocket score"),
    ("target_has_favourable_lysine", "its target has a mapped lysine with a favourable verdict"),
    ("highest_resolution", "the highest-resolution structure among the candidates"),
]

# Spec 6.6.4 relaxation order: resolution first, then balance.
RELAX_ORDER = ["highest_resolution", "balance_above_threshold",
               "target_has_favourable_lysine", "substrate_has_degron",
               "ligase_has_pocket_score"]


def worked_example() -> dict:
    """Pick one record deterministically and carry it through all four modules.

    Selection is never hardcoded. Where no record satisfies every criterion the
    conditions relax in the documented order, which ones were relaxed is logged,
    and the page states which criteria the example actually meets.

    The pool deliberately excludes every structure that is already known to be
    a degrader complex: anything a curated glue database lists, anything
    cereblon appears in, and anything whose deposited title says PROTAC, glue
    or degrader. The example used to be 9SAI, a CRBN/DDB1/BRD4 PROTAC ternary,
    which demonstrated that the pipeline can re-find a structure whose own
    title names it. Carrying a bridge nobody has written up through the same
    four modules is the harder claim and the one worth showing, and the
    criteria below are what makes it checkable.
    """
    if not DB_PATH.exists():
        return {"available": False,
                "note": "The atlas has not been built, so no example can be selected."}

    config = load_config()
    balance_strong = float(config.t("bridging.glue_balance_strong"))
    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row

    try:
        candidates = [dict(row) for row in connection.execute(
            "SELECT b.*, e.resolution, e.title, e.method, l.name AS ligand_name, l.mw "
            "FROM bridge b "
            "LEFT JOIN entry e ON e.pdb_id = b.pdb_id "
            "LEFT JOIN ligand l ON l.ccd_id = b.ccd_id "
            "WHERE b.status = 'ok' AND b.ccd_class = 'glue_candidate' "
            "AND b.symmetry_mediated = 0 "
            # Wider than the 400 it used to take, because the exclusions below
            # remove rows from whatever this returns and a pool that ends up
            # short is a pool that silently relaxed a criterion.
            "ORDER BY b.bridging_balance DESC, b.dsasa_total DESC LIMIT 4000"
        )]
        if not candidates:
            return {"available": False,
                    "note": "No glue candidate bridge has been found yet, so no "
                            "example can be selected."}

        degron_accessions = {
            row[0] for row in connection.execute(
                "SELECT DISTINCT uniprot_acc FROM degron WHERE status = 'ok'")
        }
        pocket_accessions = {
            row[0] for row in connection.execute(
                "SELECT uniprot_acc FROM ligase WHERE pocket_score IS NOT NULL")
        }
        favourable_accessions = {
            row[0] for row in connection.execute(
                "SELECT DISTINCT uniprot_acc FROM lysine WHERE verdict = 'favourable'")
        }
        curated_entries = _curated_glue_entries()
        placeholders = ",".join("?" * len(DEGRADER_LIGASE_STATUS))
        degrader_entries = {
            row[0] for row in connection.execute(
                "SELECT DISTINCT p.pdb_id FROM polymer_entity p "
                "JOIN ligase g ON g.uniprot_acc = p.uniprot_acc "
                f"WHERE g.status = 'ok' AND g.exploitation_status IN ({placeholders})",
                DEGRADER_LIGASE_STATUS)
        }

        scored = []
        dropped = {"curated": 0, "degrader_ligase": 0, "titled": 0}
        for row in candidates:
            # Known degrader complexes are out of the pool, not scored and
            # ranked below the rest: a criterion can be relaxed, and this must
            # not be.
            if row["pdb_id"] in curated_entries:
                dropped["curated"] += 1
                continue
            if row["pdb_id"] in degrader_entries:
                dropped["degrader_ligase"] += 1
                continue
            title = (row.get("title") or "").lower()
            if any(word in title for word in DEGRADER_WORDS):
                dropped["titled"] += 1
                continue
            accessions = {
                r[0] for r in connection.execute(
                    "SELECT uniprot_acc FROM polymer_entity WHERE pdb_id = ? "
                    "AND uniprot_acc IS NOT NULL AND uniprot_acc != ''",
                    (row["pdb_id"],))
            }
            met = {
                "passes_bridging_filter": True,
                "balance_above_threshold": (row["bridging_balance"] or 0) >= balance_strong,
                "substrate_has_degron": bool(accessions & degron_accessions),
                "ligase_has_pocket_score": bool(accessions & pocket_accessions),
                "target_has_favourable_lysine": bool(accessions & favourable_accessions),
                "highest_resolution": row.get("resolution") is not None,
            }
            row["criteria_met"] = met
            row["accessions"] = sorted(accessions)
            scored.append(row)

        required = [name for name, _ in CRITERIA]
        relaxed: list[str] = []
        chosen = None
        while True:
            eligible = [
                r for r in scored
                if all(r["criteria_met"].get(name) for name in required)
            ]
            if eligible:
                # Among the candidates, take the highest-resolution structure.
                eligible.sort(key=lambda r: (
                    r.get("resolution") if r.get("resolution") is not None else 99.0,
                    -(r.get("bridging_balance") or 0),
                ))
                chosen = eligible[0]
                break
            next_drop = next((name for name in RELAX_ORDER if name in required), None)
            if next_drop is None:
                break
            required.remove(next_drop)
            relaxed.append(next_drop)

        if chosen is None:
            return {"available": False,
                    "note": "No bridge satisfied even the relaxed criteria."}

        # The example's own degron, so step 2 can show the hairpin it is
        # asserting rather than an empty viewer. Best-scoring candidate on
        # whichever accession in the entry the scan placed one on.
        degron = None
        if chosen.get("accessions"):
            marks = ",".join("?" * len(chosen["accessions"]))
            row = connection.execute(
                f"SELECT uniprot_acc, gene, afdb_id, start_res, end_res, tip_res, "
                f"tip_aa, mean_plddt, tip_rel_sasa, degron_geometry_score "
                f"FROM degron WHERE status = 'ok' AND uniprot_acc IN ({marks}) "
                f"ORDER BY degron_geometry_score DESC LIMIT 1",
                chosen["accessions"]).fetchone()
            if row is not None:
                degron = dict(row)

        # The example's own ligase, so step 3 of the walkthrough can state its
        # triage numbers instead of claiming the stage has not run. Best-ranked
        # first, because an entry can carry more than one: 7OJX holds RNF38
        # alongside ubiquitin and an E2.
        ligase = None
        if chosen.get("accessions"):
            marks = ",".join("?" * len(chosen["accessions"]))
            row = connection.execute(
                f"SELECT uniprot_acc, gene, family, pocket_score, pocket_volume_a3, "
                f"triage_rank, triage_score, exploitation_status, substrate_count "
                f"FROM ligase WHERE status = 'ok' AND uniprot_acc IN ({marks}) "
                f"ORDER BY triage_rank LIMIT 1", chosen["accessions"]).fetchone()
            if row is not None:
                ligase = dict(row)
                ligase["total_ligases"] = connection.execute(
                    "SELECT COUNT(*) FROM ligase WHERE status = 'ok'").fetchone()[0]

        # How many bridges this entry records in total, and how many of them
        # this ligand accounts for. Step 1 used to illustrate the filter with a
        # sentence about a PEG oligomer in the same entry, which was true of the
        # example it was written for and a fabrication about any other.
        entry_bridges = connection.execute(
            "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND pdb_id = ?",
            (chosen["pdb_id"],)).fetchone()[0]
        ligand_bridges = connection.execute(
            "SELECT COUNT(*) FROM bridge WHERE status = 'ok' AND pdb_id = ? "
            "AND ccd_id = ?", (chosen["pdb_id"], chosen["ccd_id"])).fetchone()[0]
        # Checked, not assumed. The record is picked on resolution and balance,
        # so it happens to be the widest interface of its ligand here and there
        # is nothing in the selection that makes that always true.
        largest = connection.execute(
            "SELECT MAX(dsasa_total) FROM bridge WHERE status = 'ok' "
            "AND pdb_id = ? AND ccd_id = ?",
            (chosen["pdb_id"], chosen["ccd_id"])).fetchone()[0]
        is_largest = (largest is not None
                      and chosen.get("dsasa_total") is not None
                      and abs(largest - chosen["dsasa_total"]) < 1e-9)

        labels = dict(CRITERIA)
        return {
            "available": True,
            "bridge_id": chosen.get("id"),
            "pdb_id": chosen.get("pdb_id"),
            "ccd_id": chosen.get("ccd_id"),
            "ligand_name": chosen.get("ligand_name") or NOT_RECORDED,
            "title": chosen.get("title") or NOT_RECORDED,
            "method": chosen.get("method") or NOT_RECORDED,
            "resolution": chosen.get("resolution"),
            "chain_a": chosen.get("chain_a"), "chain_b": chosen.get("chain_b"),
            "dsasa_a": chosen.get("dsasa_a"), "dsasa_b": chosen.get("dsasa_b"),
            "dsasa_total": chosen.get("dsasa_total"),
            "bridging_balance": chosen.get("bridging_balance"),
            "buried_fraction": chosen.get("buried_fraction"),
            "contacts_a": chosen.get("contacts_a"), "contacts_b": chosen.get("contacts_b"),
            "heavy_atoms": chosen.get("heavy_atoms"),
            "interface_residues_a": _decode(chosen.get("interface_residues_a")),
            "interface_residues_b": _decode(chosen.get("interface_residues_b")),
            "accessions": chosen.get("accessions", []),
            # The trimmed entry, so the viewer can frame this bridge's own copy
            # of the ligand. 7OJX holds three ME7 copies across three chain
            # pairs; focusing the ligand in the full deposited entry frames the
            # union of all three, which is the whole complex.
            "structure_file": chosen.get("structure_file") or "",
            "degron": degron,
            "ligase": ligase,
            "entry_bridges": entry_bridges,
            "ligand_bridges": ligand_bridges,
            "is_largest_for_ligand": is_largest,
            "criteria": [
                {"key": key, "label": labels[key],
                 "met": bool(chosen["criteria_met"].get(key)),
                 "relaxed": key in relaxed}
                for key, _ in CRITERIA
            ],
            "relaxed": [{"key": key, "label": labels[key]} for key in relaxed],
            "candidate_pool": len(scored),
            "excluded_from_pool": dropped,
            "honest_note": (
                "This record was chosen because every stage that has run worked on "
                "it. A reader should look at the misses list and the novel-bridge "
                "set in FINDINGS.md for the cases where stages did not."
            ),
        }
    finally:
        connection.close()


def _decode(value):
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return value or []


def _served_identity() -> dict:
    """What the demo actually loads, from the adapter it actually loads.

    models/binman-lm/training.json is overwritten by each training run, so it
    describes the last thing trained rather than the thing that ships. The last
    run was the 32B experiment that was evaluated and rejected, so the model
    card published a base model four times the size of the real one and
    `fused: true`, which FINDINGS.md records as an artefact that parsed 0 of 10
    held-out questions and was deleted rather than shipped. The rank and the
    layer count happened to match, which is why it read as plausible.

    models/binman-lm/served/adapter_config.json is the config fetched from the
    adapter repository the Space loads. It is the only file in the project that
    describes the served model rather than a local experiment.
    """
    path = ROOT / "models" / "binman-lm" / "served" / "adapter_config.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    layers = config.get("layers_to_transform") or []
    return {
        "base_model": config.get("base_model_name_or_path", NOT_RECORDED),
        # No adapter row here: the template renders it as a link of its own, and
        # carrying it in both put the same value in the table twice.
        "fine_tune_type": str(config.get("peft_type", "")).lower() or NOT_RECORDED,
        "adapter_rank": config.get("r", NOT_RECORDED),
        "adapter_alpha": config.get("lora_alpha", NOT_RECORDED),
        "adapter_layers": len(layers) if layers else NOT_RECORDED,
        # A PEFT adapter is applied to the base at load time by construction.
        # Fusing was tried and the result was deleted, so this is not a value
        # read from anywhere: it is what "serves an adapter" means.
        "fused": False,
    }


def _adapter_repo() -> str:
    """The adapter's HuggingFace id, read from the Space that loads it.

    deploy/hf-space/README.md declares it in its `models:` front matter and
    deploy/hf-space/app.py takes it as the default for BINMAN_ADAPTER_REPO, so
    the Space is the thing that actually knows. Reading it here means the link
    on the About page cannot drift from the repository the demo pulls.
    """
    readme = ROOT / "deploy" / "hf-space" / "README.md"
    try:
        lines = readme.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    inside = False
    for line in lines:
        if line.strip() == "models:":
            inside = True
            continue
        if inside:
            stripped = line.strip()
            if stripped.startswith("- "):
                return stripped[2:].strip()
            break
    return ""


def _curated_glue_entries() -> set[str]:
    import csv

    found: set[str] = set()
    for name in ("mgdb_glues", "molgluedb_glues", "mgtbind_ternary"):
        path = VALIDATION / f"{name}.tsv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                for key, value in row.items():
                    if "pdb" in (key or "").lower() and value:
                        for token in str(value).replace(";", ",").split(","):
                            token = token.strip().upper()
                            if len(token) == 4 and token[0].isdigit():
                                found.add(token)
    return found


# --------------------------------------------------------------------------- #
# the workflow schematic (spec 6.6.1)
# --------------------------------------------------------------------------- #

def workflow_svg(stages: dict, atlas: dict, datasets: list[dict]) -> tuple[str, str]:
    """Draw the four-stage schematic from the manifests, plus a text description.

    Theme-aware: every colour comes from a Depot token via `currentColor` or an
    explicit `var(--token)`, so nothing is legible in only one theme. The text
    description is for screen readers, which cannot read the SVG.
    """
    catalogue = stages.get("catalogue", {})
    bridges = stages.get("bridges", {})

    columns = [
        {
            "title": "1 · Acquisition",
            "software": "httpx, tenacity",
            "lines": [
                f"{catalogue.get('total', 0):,} entries",
                f"tier 1  {catalogue.get('tiers', {}).get('1', 0):,}",
                f"tier 2  {catalogue.get('tiers', {}).get('2', 0):,}",
                f"tier 3  {catalogue.get('tiers', {}).get('3', 0):,}",
            ],
            "failed": 0,
            # One line of plain English per stage, drawn as a second row under
            # the boxes. The numbers above say how much; these say what for.
            "plain": ["Fetch every PDB entry that", "could hold a glue."],
        },
        {
            "title": "2 · Geometry",
            "software": "gemmi, FreeSASA",
            "lines": [
                f"{bridges.get('ok', 0):,} entries analysed",
                f"{atlas.get('bridge', 0):,} bridges found",
            ],
            "failed": bridges.get("failed", 0),
            "plain": ["Measure which ligands touch", "two proteins at once."],
        },
        {
            "title": "3 · Scan and triage",
            "software": "DSSP, fpocket",
            "lines": [
                f"{atlas.get('degron', 0):,} degrons scanned",
                f"{atlas.get('ligase', 0):,} ligases triaged",
                f"{atlas.get('lysine', 0):,} lysines scored",
            ],
            "failed": (stages.get("degrons", {}).get("failed", 0)
                       + stages.get("ligases", {}).get("failed", 0)),
            "plain": ["Score what a degrader needs:", "tags, ligases, lysines."],
        },
        {
            "title": "4 · Model",
            "software": "mlx-lm, LoRA",
            "lines": [
                "BINMAN-LM 3B, 32 layers",
                "query, triage, abstain",
                "never emits a number",
            ],
            "failed": 0,
            "plain": ["Reads the question, writes", "the query. Never the number."],
        },
    ]

    box_w, box_h, gap = 196, 148, 34
    left_margin = 128
    top = 74
    module_w = 124
    modules = ("Glue Atlas", "Degron Scan", "E3 Triage", "Degradability")

    # All three columns span exactly the stage boxes, so the figure has one top
    # edge and one bottom edge instead of three. They were drawn to their own
    # fixed heights before: the stage row ran to top+148, the two input boxes
    # stopped at top+134 and the module stack at top+128, which read as a
    # drawing that had not been lined up rather than as three kinds of thing.
    #
    # Derived rather than typed. The second input box is positioned from the
    # bottom and the module height is what is left after the steps, so integer
    # division cannot leave either column a pixel short of the others.
    input_gap = 12
    input_h = (box_h - input_gap) // 2
    input_bottom_y = top + box_h - input_h
    module_step = 40
    module_h = box_h - (len(modules) - 1) * module_step

    # The plain-English row, under the stage boxes only. Derived from the stage
    # row so it cannot drift from it.
    lay_gap = 12
    lay_h = 46
    lay_top = top + box_h + lay_gap

    # The canvas is COMPUTED from the layout rather than fixed. A hardcoded
    # 1060x460 left a third of the height empty and, once widened by hand, cut
    # two pixels off the module column. Deriving both from the content means a
    # layout change cannot silently clip or pad the figure again.
    out_x = left_margin + (len(columns) - 1) * (box_w + gap) + box_w + gap + 10
    width = out_x + module_w + 12
    height = max(lay_top + lay_h,
                 top + (len(modules) - 1) * module_step + module_h) + 16

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'class="schematic" preserveAspectRatio="xMidYMid meet" '
        f'role="img" aria-labelledby="wf-title wf-desc">',
        '<title id="wf-title">BINMAN pipeline schematic</title>',
        '<desc id="wf-desc">Described in the text below the figure.</desc>',
        '<style>'
        '.wf-box{fill:var(--surface);stroke:var(--line);stroke-width:1.5}'
        '.wf-ds{fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5;stroke-dasharray:4 3}'
        '.wf-t{fill:var(--ink);font:600 13px var(--display),sans-serif}'
        '.wf-s{fill:var(--muted);font:10px var(--data),monospace}'
        '.wf-n{fill:var(--ink);font:11px var(--data),monospace}'
        '.wf-bad{fill:var(--bad);font:11px var(--data),monospace}'
        '.wf-arrow{stroke:var(--line);stroke-width:1.5;fill:none}'
        '.wf-head{fill:var(--muted);font:600 10px var(--display),sans-serif;'
        'letter-spacing:.06em;text-transform:uppercase}'
        '.wf-lay-box{fill:none;stroke:var(--line);stroke-width:1.5;stroke-dasharray:3 3}'
        '.wf-lay{fill:var(--muted);font:11px var(--display),sans-serif}'
        '</style>',
        f'<marker id="wf-tip" markerWidth="7" markerHeight="7" refX="6" refY="3.5" '
        f'orient="auto"><path d="M0,0 L7,3.5 L0,7Z" fill="var(--line)"/></marker>',
    ]

    # Inputs on the left: primary sources, and validation sets as a distinct shape.
    parts.append(f'<text class="wf-head" x="12" y="{top - 24}">Inputs</text>')
    parts.append(
        f'<rect class="wf-box" x="12" y="{top}" width="108" height="{input_h}" rx="2"/>'
        f'<text class="wf-t" x="22" y="{top + 24}">Sources</text>'
        f'<text class="wf-s" x="22" y="{top + 42}">RCSB, AFDB,</text>'
        f'<text class="wf-s" x="22" y="{top + 56}">UniProt</text>'
    )
    parts.append(
        f'<rect class="wf-ds" x="12" y="{input_bottom_y}" width="108" '
        f'height="{input_h}" rx="2"/>'
        f'<text class="wf-t" x="22" y="{input_bottom_y + 24}">Ground truth</text>'
        f'<text class="wf-s" x="22" y="{input_bottom_y + 42}">Published</text>'
        f'<text class="wf-s" x="22" y="{input_bottom_y + 56}">datasets</text>'
    )

    for index, column in enumerate(columns):
        x = left_margin + index * (box_w + gap)
        parts.append(
            f'<g class="wf-node" data-stage="{index + 1}" tabindex="0">'
            f'<rect class="wf-box" x="{x}" y="{top}" width="{box_w}" height="{box_h}" rx="2"/>'
            f'<text class="wf-t" x="{x + 12}" y="{top + 24}">{column["title"]}</text>'
            f'<text class="wf-s" x="{x + 12}" y="{top + 40}">{column["software"]}</text>'
        )
        for line_index, line in enumerate(column["lines"]):
            parts.append(
                f'<text class="wf-n" x="{x + 12}" y="{top + 64 + line_index * 16}">{line}</text>'
            )
        if column["failed"]:
            parts.append(
                f'<text class="wf-bad" x="{x + 12}" y="{top + box_h - 14}">'
                f'{column["failed"]:,} failed</text>'
            )
        parts.append('</g>')
        # Plain English under the box, in a dashed outline so it reads as a
        # gloss on the stage rather than as a fifth stage.
        parts.append(
            f'<rect class="wf-lay-box" x="{x}" y="{lay_top}" width="{box_w}" '
            f'height="{lay_h}" rx="2"/>'
        )
        for line_index, line in enumerate(column.get("plain") or []):
            parts.append(
                f'<text class="wf-lay" x="{x + 12}" '
                f'y="{lay_top + 19 + line_index * 15}">{line}</text>'
            )
        if index < len(columns) - 1:
            start = x + box_w
            parts.append(
                f'<path class="wf-arrow" d="M{start},{top + box_h / 2} '
                f'L{start + gap - 6},{top + box_h / 2}" marker-end="url(#wf-tip)"/>'
            )

    # Both input arrows leave their own box at its mid-height and converge on
    # the first stage box, so they follow the boxes wherever those are placed.
    parts.append(
        f'<path class="wf-arrow" d="M120,{top + input_h / 2} '
        f'L{left_margin - 6},{top + box_h / 2 - 10}" marker-end="url(#wf-tip)"/>'
    )
    parts.append(
        f'<path class="wf-arrow" d="M120,{input_bottom_y + input_h / 2} '
        f'L{left_margin - 6},{top + box_h / 2 + 10}" marker-end="url(#wf-tip)"/>'
    )

    # Modules leaving on the right. `out_x` is computed above, with the canvas.
    parts.append(f'<text class="wf-head" x="{out_x}" y="{top - 24}">Modules</text>')
    for index, label in enumerate(modules):
        y = top + index * module_step
        parts.append(
            f'<rect class="wf-box" x="{out_x}" y="{y}" width="{module_w}" '
            f'height="{module_h}" rx="2"/>'
            f'<text class="wf-n" x="{out_x + 10}" y="{y + module_h / 2 + 4}">{label}</text>'
        )
    # The arrow into the module column starts at the last stage box, not at a
    # notional gap beyond it, which previously ran off the canvas.
    last_box_right = left_margin + (len(columns) - 1) * (box_w + gap) + box_w
    parts.append(
        f'<path class="wf-arrow" d="M{last_box_right},{top + box_h / 2} '
        f'L{out_x - 6},{top + box_h / 2}" marker-end="url(#wf-tip)"/>'
    )
    parts.append('</svg>')

    description = (
        "The pipeline runs left to right in four stages. Two kinds of input enter "
        "on the left: the primary data sources (RCSB, AlphaFold DB, UniProt, "
        "InterPro), and separately the validation datasets that serve as ground "
        "truth. "
        f"Stage 1, acquisition, catalogued {catalogue.get('total', 0):,} entries "
        f"into priority tiers using httpx and tenacity. "
        f"Stage 2, geometry, analysed {bridges.get('ok', 0):,} entries with gemmi "
        f"and FreeSASA and found {atlas.get('bridge', 0):,} bridges, with "
        f"{bridges.get('failed', 0):,} entries failing. "
        f"Stage 3, scan and triage, used DSSP and fpocket to produce "
        f"{atlas.get('degron', 0):,} degron candidates, {atlas.get('ligase', 0):,} "
        f"triaged ligases and {atlas.get('lysine', 0):,} scored lysines. "
        "Stage 4 trains BINMAN-LM with mlx-lm, which does text work only and never "
        "emits a number. Four modules leave on the right: Glue Atlas, Degron Scan, "
        "E3 Triage and Degradability. "
        "In plain terms: stage 1 fetches every PDB entry that could hold a glue, "
        "stage 2 measures which ligands touch two proteins at once, stage 3 scores "
        "what a degrader needs (tags, ligases and lysines), and stage 4 reads the "
        "question and writes the query without ever producing the number."
    )
    return "\n".join(parts), description


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #

def build() -> dict:
    config = load_config()
    stages = stage_counts()
    atlas = atlas_counts()
    datasets = dataset_rows()
    references = reference_rows()
    svg, description = workflow_svg(stages, atlas, datasets)
    example = worked_example()
    results = _json(VALIDATION / "results.json", {}) or {}

    # Two different things were being counted as one, and the page said the
    # wrong one about both.
    #
    # "Could not be read from an artefact" means the build produced no value:
    # a gap to go and fix. A licence reading "not determined: <what was
    # checked>" is the opposite of that. It was read from the artefact, and it
    # records a finding about the world: somebody checked the source and it
    # publishes no terms. UbiBrowser 2.0 is the live case. Its site states
    # nothing, and its NAR paper is CC BY-NC-4.0 on the version of record,
    # which covers the article and not the database.
    #
    # Reporting that as "could not be read" is a false statement about this
    # project's own provenance, on the one page whose whole claim is that every
    # value comes from an artefact. They are separated here, and the page says
    # a different sentence about each.
    unrecorded: list[str] = []
    undetermined: list[dict] = []
    for row in references:
        state = licence_state(row["licence"])
        if state == "missing":
            unrecorded.append(f"licence for reference '{row['key']}'")
        elif state == "not_published":
            licence = row["licence"]
            reason = licence.split(":", 1)[1].strip() if ":" in licence else ""
            undetermined.append({"key": row["key"], "reason": reason})
        if not row["doi"] and not row["home"]:
            unrecorded.append(f"DOI and URL both missing for '{row['key']}'")

    about = {
        "generated_at": utcnow(),
        "generator": "pipeline/build_about.py",
        # No standing note. The page no longer prints one, and the behaviour it
        # described is still visible where it matters: the unrecorded banner
        # fires when a value could not be read, and NOT_RECORDED appears in the
        # cell itself rather than a guess.
        "schematic_description": description,
        "stages": stages,
        "atlas": atlas,
        "datasets": datasets,
        "datasets_resolved": sum(1 for d in datasets if d["resolved"]),
        "datasets_total": len(datasets),
        "references": references,
        "reference_summary": {
            "total": len(references),
            "verified": sum(1 for r in references if r["verified"]),
            "unverified": sum(1 for r in references if not r["verified"]),
            "licence_not_determined": sum(
                1 for r in references
                if not r["licence"] or r["licence"].startswith("not determined")),
        },
        "licences_not_published": undetermined,
        "model_card": model_card(),
        "worked_example": example,
        "validation": results,
        "thresholds": config.thresholds,
        "tuning": config.tuning,
        "hardware": config.hardware,
        "gates": _gate_state(),
        "unrecorded": sorted(set(unrecorded)),
        # Where the model and the code actually live. The adapter id is read
        # from the Space's own front matter rather than written twice.
        "links": {
            "github": "https://github.com/bellcheddar/BINMAN",
            "adapter": (f"https://huggingface.co/{_adapter_repo()}"
                        if _adapter_repo() else ""),
            "adapter_id": _adapter_repo(),
            "space": "https://huggingface.co/spaces/Dellboy/binman-lm",
            "space_live": "https://dellboy-binman-lm.hf.space",
        },
        "citation": {
            "project": "Deller, M. C. BINMAN: Blind-spot INventory of Molecular "
                       "Adhesives and Neosubstrates.",
            "repository": "https://github.com/bellcheddar/BINMAN",
            "instruction": (
                "Cite BINMAN for the atlas itself, and cite every underlying "
                "resource separately: the atlas is a derivative of the databases "
                "listed in the reference table, and they deserve their own citation."
            ),
        },
    }

    ABOUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    ABOUT_JSON.write_text(json.dumps(about, indent=2, default=str) + "\n")
    WORKFLOW_SVG.write_text(svg + "\n")

    Manifest(STAGE).record(
        "build", status="ok", references=len(references),
        datasets_resolved=about["datasets_resolved"], datasets_total=len(datasets),
        example_available=bool(example.get("available")),
        unrecorded=len(about["unrecorded"]),
        about_bytes=ABOUT_JSON.stat().st_size,
    )
    log_event("4.1b", f"About tab generated: {len(references)} references, "
                      f"{about['datasets_resolved']}/{len(datasets)} datasets resolved, "
                      f"worked example {'selected' if example.get('available') else 'unavailable'}, "
                      f"{len(about['unrecorded'])} value(s) not recorded, "
                      f"{len(about['licences_not_published'])} source(s) publish "
                      "no licence.")
    return about


def licence_state(licence: str | None) -> str:
    """Which of three things a reference's licence field is saying.

    `missing`       the build produced no value: a gap to go and fix.
    `not_published` the source was checked and publishes no terms. This is a
                    finding about the world, recorded in the artefact, and the
                    opposite of a value that could not be read.
    `stated`        a licence was found and recorded.

    The first two were counted as one, so the About page reported "could not be
    read from an artefact" about a value that had been read and that records a
    deliberate finding. That is a false statement about this project's own
    provenance, on the page whose whole claim is that every value comes from an
    artefact. See D-060.
    """
    text = (licence or "").strip()
    if not text or text == NOT_RECORDED:
        return "missing"
    if text.startswith("not determined"):
        return "not_published"
    return "stated"


def _gate_state() -> list[dict]:
    """Which gates are open, read from GATE_OPEN.md rather than assumed."""
    path = ROOT / "GATE_OPEN.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    match = re.search(r"#\s*Gate\s+(\S+)\s+open", text)
    return [{
        "gate": match.group(1) if match else NOT_RECORDED,
        "excerpt": text.split("## What is needed", 1)[-1].strip()[:900],
    }]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the About tab")
    parser.parse_args()
    about = build()
    print(f"references          : {about['reference_summary']}")
    print(f"datasets resolved   : {about['datasets_resolved']}/{about['datasets_total']}")
    print(f"worked example      : {about['worked_example'].get('available')}")
    if about["worked_example"].get("available"):
        example = about["worked_example"]
        print(f"  {example['pdb_id']} / {example['ccd_id']} "
              f"balance {example['bridging_balance']} res {example['resolution']}")
        print(f"  relaxed: {[r['key'] for r in example['relaxed']] or 'nothing'}")
    print(f"not recorded        : {len(about['unrecorded'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
