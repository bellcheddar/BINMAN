"""Fetch chemical component dictionary metadata from RCSB in batches.

Used by the classifier and by the ligand table. Separate from `pipeline.rcsb`
because chem comps are keyed by CCD code rather than by entry, and the whole
dictionary is small enough to cache wholesale.
"""

from __future__ import annotations

from typing import Iterable, Iterator, Sequence

from pipeline.common import Fetcher, request_hash
from pipeline.rcsb import GRAPHQL_URL

CHEM_COMP_QUERY = """
query($ids:[String!]!){
  chem_comps(comp_ids:$ids){
    chem_comp{id name formula formula_weight type mon_nstd_parent_comp_id}
    rcsb_chem_comp_descriptor{SMILES_stereo InChIKey}
  }
}
"""

BATCH = 200


def fetch_chem_comps(
    ccd_ids: Sequence[str], *, fetcher: Fetcher | None = None, batch: int = BATCH
) -> Iterator[dict]:
    """Yield flattened chem comp records for every CCD code that resolves."""
    fetcher = fetcher or Fetcher("rcsb")
    ids = sorted({c.strip().upper() for c in ccd_ids if c and c.strip()})
    for start in range(0, len(ids), batch):
        chunk = ids[start:start + batch]
        body = {"query": CHEM_COMP_QUERY, "variables": {"ids": chunk}}
        try:
            payload = fetcher.fetch_json(
                GRAPHQL_URL, method="POST", json_body=body,
                key=f"ccd_{request_hash('POST', GRAPHQL_URL, None, body)}",
            )
        except Exception:
            if len(chunk) == 1:
                continue
            # Split the batch so one unresolvable code cannot cost the rest.
            mid = len(chunk) // 2
            yield from fetch_chem_comps(chunk[:mid], fetcher=fetcher, batch=batch)
            yield from fetch_chem_comps(chunk[mid:], fetcher=fetcher, batch=batch)
            continue
        for node in (payload.get("data") or {}).get("chem_comps") or []:
            if not node:
                continue
            comp = node.get("chem_comp") or {}
            descriptor = node.get("rcsb_chem_comp_descriptor") or {}
            if not comp.get("id"):
                continue
            yield {
                "ccd_id": comp["id"].upper(),
                "name": comp.get("name") or "",
                "formula": comp.get("formula") or "",
                "mw": comp.get("formula_weight"),
                "ccd_type": comp.get("type") or "",
                "parent_ccd": comp.get("mon_nstd_parent_comp_id") or "",
                "smiles": descriptor.get("SMILES_stereo") or "",
                "inchikey": descriptor.get("InChIKey") or "",
            }
