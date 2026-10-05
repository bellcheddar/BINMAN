"""JSON endpoints behind the ledger, the viewers and the lens graph."""

from __future__ import annotations

import json
import sqlite3

from flask import Blueprint, jsonify, request, send_from_directory

from app import db, lm
from app.queries import (
    RECORD_TYPES, QueryError, count as query_count, execute, parse, schema_summary,
)

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/schema")
def schema():
    return jsonify({"record_types": schema_summary(), "lm_enabled": lm.enabled()})


@bp.post("/query")
def run_query():
    payload = request.get_json(silent=True) or {}
    connection = db.get()
    if connection is None:
        return jsonify({"error": "The atlas has not been built yet.",
                        "rows": [], "total": 0}), 503
    try:
        query = parse(payload.get("query", payload))
    except QueryError as exc:
        # A rejected query is a 400 with the reason, which is also what the LM
        # is trained against.
        return jsonify({"error": str(exc), "rows": [], "total": 0}), 400

    columns = payload.get("columns")
    try:
        rows = execute(connection, query, columns)
        total = query_count(connection, query)
    except QueryError as exc:
        # An unselectable column is the caller's mistake, like a rejected
        # query above, so it is a 400 with the reason. It was reaching the
        # client as a 500 and a stack trace, because only sqlite3.Error was
        # caught here and column validation happens inside execute().
        return jsonify({"error": str(exc), "rows": [], "total": 0}), 400
    except sqlite3.Error as exc:
        return jsonify({"error": f"query failed: {exc}", "rows": [], "total": 0}), 500

    # Interface residue lists are stored as JSON text; decode them for the UI.
    for row in rows:
        for key in ("interface_residues_a", "interface_residues_b",
                    "plip_types_a", "plip_types_b"):
            if isinstance(row.get(key), str) and row[key]:
                try:
                    row[key] = json.loads(row[key])
                except json.JSONDecodeError:
                    pass

    return jsonify({
        "rows": rows, "total": total, "returned": len(rows),
        "query": query.as_dict(), "describe": query.describe(),
    })


@bp.post("/nl")
def natural_language():
    """Natural language to query object, via BINMAN-LM.

    Returns 503 when the model is not configured, which the UI treats as a
    normal state and falls back to the manual builder (spec 3.9).
    """
    if not lm.enabled():
        return jsonify({"error": "The language model is not enabled for this deployment.",
                        "fallback": "manual_builder"}), 503
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "a question is required"}), 400

    result = lm.propose_query(question, schema_summary())
    if not result.ok:
        return jsonify({"error": result.error, "fallback": "manual_builder"}), 502

    # The model's proposal is validated by the same parser as a hand-built
    # query. Nothing it returns is trusted.
    try:
        query = parse(result.payload)
    except QueryError as exc:
        # The query head answered a question the schema cannot answer, and the
        # parser caught it. Ask the head that was trained for this case what is
        # actually missing, so the user reads an explanation instead of the
        # parser's complaint about the model.
        refusal = lm.explain_refusal(question)
        if refusal.ok and isinstance(refusal.payload, dict):
            payload = refusal.payload
            if payload.get("answerable") is False and payload.get("explanation"):
                return jsonify({
                    "error": payload["explanation"],
                    "missing": payload.get("missing") or [],
                    "abstained": True,
                    "fallback": "manual_builder",
                }), 422
        return jsonify({"error": f"the model proposed an invalid query: {exc}",
                        "proposed": result.payload, "fallback": "manual_builder"}), 422
    return jsonify({"query": query.as_dict(), "describe": query.describe()})


@bp.get("/entity/<record_type>/<path:row_id>")
def entity(record_type: str, row_id: str):
    """One record with everything the viewers need, within the 150 KB budget."""
    if record_type not in RECORD_TYPES:
        return jsonify({"error": f"unknown record type {record_type}"}), 404
    connection = db.get()
    if connection is None:
        return jsonify({"error": "The atlas has not been built yet."}), 503

    spec = RECORD_TYPES[record_type]
    key = spec.identity_columns[0]
    table = "bridge" if record_type == "bridge" else spec.table
    row = db.one(f"SELECT * FROM {table} WHERE {key} = ?", (row_id,))
    if row is None:
        return jsonify({"error": f"no {record_type} with {key} = {row_id}"}), 404

    for field in ("interface_residues_a", "interface_residues_b",
                  "plip_types_a", "plip_types_b"):
        if isinstance(row.get(field), str) and row[field]:
            try:
                row[field] = json.loads(row[field])
            except json.JSONDecodeError:
                pass

    if record_type == "bridge" and row.get("pdb_id"):
        row["entry"] = db.one("SELECT * FROM entry WHERE pdb_id = ?", (row["pdb_id"],))
        row["ligand"] = db.one("SELECT * FROM ligand WHERE ccd_id = ?", (row["ccd_id"],))
    return jsonify(row)


@bp.get("/lens")
def lens():
    """Pruned neighbourhood of the focus accession (spec 6.3: never over 400 nodes)."""
    connection = db.get()
    if connection is None:
        return jsonify({"nodes": [], "links": [], "note": "atlas not built"}), 503

    focus = (request.args.get("focus") or "").strip()
    try:
        depth = max(1, min(3, int(request.args.get("depth", 2))))
    except ValueError:
        depth = 2
    from app.thresholds import value as _threshold

    max_nodes = int(_threshold("atlas.lens_graph_max_nodes", 400))

    if not focus:
        rows = db.many(
            "SELECT source_acc, target_acc, edge_type, ccd_id, pdb_id, evidence "
            "FROM edge WHERE status = 'ok' LIMIT ?", (max_nodes * 2,)
        )
    else:
        frontier = {focus}
        seen: set[str] = set()
        rows = []
        for _ in range(depth):
            if not frontier or len(seen) > max_nodes:
                break
            placeholders = ",".join("?" for _ in frontier)
            batch = db.many(
                "SELECT source_acc, target_acc, edge_type, ccd_id, pdb_id, evidence "
                f"FROM edge WHERE status = 'ok' AND (source_acc IN ({placeholders}) "
                f"OR target_acc IN ({placeholders}))",
                tuple(frontier) * 2,
            )
            rows.extend(batch)
            seen |= frontier
            frontier = {
                acc for row in batch for acc in (row["source_acc"], row["target_acc"])
            } - seen

    nodes: dict[str, dict] = {}
    links = []
    for row in rows:
        for acc in (row["source_acc"], row["target_acc"]):
            if acc and acc not in nodes:
                if len(nodes) >= max_nodes:
                    continue
                nodes[acc] = {"id": acc, "kind": "protein"}
        if row["source_acc"] in nodes and row["target_acc"] in nodes:
            links.append({
                "source": row["source_acc"], "target": row["target_acc"],
                "type": row["edge_type"], "ccd_id": row["ccd_id"],
                "pdb_id": row["pdb_id"], "evidence": row["evidence"],
            })

    # Annotate with what we know, so the lenses have something to colour by.
    if nodes:
        placeholders = ",".join("?" for _ in nodes)
        for row in db.many(
            f"SELECT uniprot_acc, gene, family, triage_rank, pocket_score, "
            f"exploitation_status FROM ligase WHERE uniprot_acc IN ({placeholders})",
            tuple(nodes),
        ):
            node = nodes.get(row["uniprot_acc"])
            if node:
                node.update({
                    "kind": "ligase", "gene": row["gene"], "family": row["family"],
                    "triage_rank": row["triage_rank"], "pocket_score": row["pocket_score"],
                    "exploitation_status": row["exploitation_status"],
                })
    return jsonify({
        "nodes": list(nodes.values()), "links": links,
        "focus": focus, "depth": depth, "max_nodes": max_nodes,
        "truncated": len(nodes) >= max_nodes,
    })


@bp.get("/structures/<path:filename>")
def structures(filename: str):
    """Serve a trimmed, gzipped mmCIF to Mol*."""
    from pathlib import Path

    directory = Path(__file__).resolve().parents[1] / "static" / "structures"
    response = send_from_directory(directory, filename, conditional=True)
    if filename.endswith(".gz"):
        # Mol* reads the file as mmCIF, so declare the encoding rather than the
        # type: the browser decompresses it transparently.
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Type"] = "chemical/x-mmcif"
    return response


@bp.get("/health")
def health():
    counts = db.table_counts()
    return jsonify({
        "atlas_available": db.available(),
        "counts": counts,
        "lm_enabled": lm.enabled(),
    })
