"""RCSB Search API, Data API and file service access (spec 4.1).

Three entry points:

* `search_entries` paginates the Search API and returns identifiers.
* `fetch_entry_metadata` batches the Data API's GraphQL endpoint, which returns
  entry, polymer entity, non-polymer entity and assembly metadata in one
  request. One GraphQL call per 50 entries beats four REST calls per entry by
  about two orders of magnitude.
* `download_assembly` pulls a gzipped biological assembly mmCIF from the file
  service into the cache.

Everything goes through `pipeline.common.Fetcher`, so every response is cached
on disk, rate limited and retried, and a restart re-reads rather than re-fetches.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence

from pipeline.common import CACHE, Config, Fetcher, load_config, request_hash

SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
GRAPHQL_URL = "https://data.rcsb.org/graphql"
FILES_URL = "https://files.rcsb.org/download"

# The Search API caps a single page; 10 000 is its documented maximum.
SEARCH_PAGE_ROWS = 10000
# GraphQL batch size. Larger batches start timing out on entries with many
# entities, so this is deliberately conservative.
GRAPHQL_BATCH = 50

ASSEMBLY_DIR = CACHE / "rcsb_assemblies"

ENTRY_QUERY = """
query($ids:[String!]!){
  entries(entry_ids:$ids){
    rcsb_id
    struct{title}
    exptl{method}
    rcsb_entry_info{
      resolution_combined
      experimental_method
      polymer_entity_count
      nonpolymer_entity_count
      deposited_polymer_entity_instance_count
      deposited_nonpolymer_entity_instance_count
    }
    rcsb_accession_info{deposit_date initial_release_date}
    polymer_entities{
      rcsb_id
      entity_poly{rcsb_entity_polymer_type}
      rcsb_polymer_entity{pdbx_description}
      rcsb_polymer_entity_container_identifiers{asym_ids auth_asym_ids uniprot_ids}
      rcsb_entity_source_organism{ncbi_scientific_name ncbi_taxonomy_id}
    }
    nonpolymer_entities{
      rcsb_id
      nonpolymer_comp{
        chem_comp{id name formula formula_weight type}
        rcsb_chem_comp_descriptor{SMILES_stereo InChIKey}
      }
      rcsb_nonpolymer_entity_container_identifiers{asym_ids auth_asym_ids}
    }
    assemblies{
      rcsb_id
      rcsb_assembly_info{assembly_id polymer_entity_instance_count nonpolymer_entity_instance_count}
    }
  }
}
"""


# --------------------------------------------------------------------------- #
# search
# --------------------------------------------------------------------------- #

def _terminal(attribute: str, operator: str, value: Any) -> dict:
    return {
        "type": "terminal", "service": "text",
        "parameters": {"attribute": attribute, "operator": operator, "value": value},
    }


def bridging_candidate_query() -> dict:
    """Entries with a ligand and at least two polymer CHAINS it could bridge.

    Spec 1.1 says two distinct polymer *entities*, and that quietly excluded
    every homo-oligomeric glue: a homodimer is one entity whatever its chain
    count, so FKBP12 with FK1012, the original chemical dimeriser, and
    transthyretin with tafamidis, a marketed drug whose mechanism is stabilising
    a homotetramer, were never fetched. A Blind-spot INventory of Molecular
    Adhesives could not represent a glue that sticks a protein to a copy of
    itself. Widened on Marc's authorisation (D-062, D-072).

    The bridging test itself never needed changing. `find_bridges` rejects only
    a chain paired with itself, and the atlas already holds 42,797 same-entity
    bridges, so the geometry has always handled this and only the catalogue was
    narrow.

    `deposited_polymer_entity_instance_count` is the chain count, which is the
    quantity the bridging question actually turns on.
    """
    return {
        "type": "group", "logical_operator": "and",
        "nodes": [
            _terminal("rcsb_entry_info.deposited_polymer_entity_instance_count",
                      "greater_or_equal", 2),
            _terminal("rcsb_entry_info.nonpolymer_entity_count", "greater_or_equal", 1),
        ],
    }


def single_chain_with_ligand_query() -> dict:
    """Tier 4: single polymer entity plus a ligand, for the triage negative class."""
    return {
        "type": "group", "logical_operator": "and",
        "nodes": [
            _terminal("rcsb_entry_info.polymer_entity_count", "equals", 1),
            _terminal("rcsb_entry_info.nonpolymer_entity_count", "greater_or_equal", 1),
        ],
    }


def search_entries(
    query: dict,
    *,
    fetcher: Fetcher | None = None,
    limit: int | None = None,
    content_types: Sequence[str] = ("experimental",),
) -> list[str]:
    """Run a Search API query and return every identifier, paginating as needed."""
    fetcher = fetcher or Fetcher("rcsb")
    identifiers: list[str] = []
    start = 0
    total: int | None = None

    while True:
        rows = SEARCH_PAGE_ROWS
        if limit is not None:
            remaining = limit - len(identifiers)
            if remaining <= 0:
                break
            rows = min(rows, remaining)
        body = {
            "query": query,
            "return_type": "entry",
            "request_options": {
                "paginate": {"start": start, "rows": rows},
                "results_content_type": list(content_types),
                "sort": [{"sort_by": "score", "direction": "desc"}],
            },
        }
        payload = fetcher.fetch_json(
            SEARCH_URL, method="POST", json_body=body,
            key=f"search_{request_hash('POST', SEARCH_URL, None, body)}",
        )
        if total is None:
            total = int(payload.get("total_count", 0))
        page = [row["identifier"] for row in payload.get("result_set", [])]
        identifiers.extend(page)
        if not page or len(identifiers) >= (limit or total or 0) or start + rows >= (total or 0):
            break
        start += rows

    # The API can repeat an identifier across page boundaries when the index
    # shifts mid-crawl, so de-duplicate while preserving order.
    seen: set[str] = set()
    unique = []
    for identifier in identifiers:
        upper = identifier.upper()
        if upper not in seen:
            seen.add(upper)
            unique.append(upper)
    return unique


def search_count(query: dict, *, fetcher: Fetcher | None = None) -> int:
    """Total hits for a query without pulling the identifiers."""
    fetcher = fetcher or Fetcher("rcsb")
    body = {
        "query": query, "return_type": "entry",
        "request_options": {
            "paginate": {"start": 0, "rows": 1},
            "results_content_type": ["experimental"],
        },
    }
    payload = fetcher.fetch_json(
        SEARCH_URL, method="POST", json_body=body,
        key=f"count_{request_hash('POST', SEARCH_URL, None, body)}",
    )
    return int(payload.get("total_count", 0))


# --------------------------------------------------------------------------- #
# metadata
# --------------------------------------------------------------------------- #

@dataclass
class EntryMetadata:
    """Flattened RCSB metadata for one entry, shaped for the SQLite schema."""

    pdb_id: str
    title: str
    method: str
    resolution: float | None
    deposit_date: str
    release_date: str
    organism: str
    polymer_entity_count: int
    nonpolymer_entity_count: int
    default_assembly_id: str
    polymer_entities: list[dict]
    nonpolymer_entities: list[dict]
    assemblies: list[dict]

    @property
    def ligand_max_mw(self) -> float:
        weights = [e["mw"] for e in self.nonpolymer_entities if e.get("mw")]
        return max(weights) if weights else 0.0

    @property
    def uniprot_accessions(self) -> list[str]:
        out: list[str] = []
        for entity in self.polymer_entities:
            for accession in entity.get("uniprot_ids") or []:
                if accession not in out:
                    out.append(accession)
        return out


def _first(sequence, default=None):
    if not sequence:
        return default
    return sequence[0]


def parse_entry(node: dict) -> EntryMetadata:
    """Flatten one GraphQL entry node. Missing fields become empty, never guesses."""
    info = node.get("rcsb_entry_info") or {}
    accession = node.get("rcsb_accession_info") or {}
    resolutions = info.get("resolution_combined") or []
    methods = [m.get("method") for m in (node.get("exptl") or []) if m.get("method")]

    polymers: list[dict] = []
    organisms: list[str] = []
    for entity in node.get("polymer_entities") or []:
        identifiers = entity.get("rcsb_polymer_entity_container_identifiers") or {}
        source = _first(entity.get("rcsb_entity_source_organism") or [], {}) or {}
        organism = source.get("ncbi_scientific_name") or ""
        if organism and organism not in organisms:
            organisms.append(organism)
        polymers.append({
            "entity_id": entity.get("rcsb_id", ""),
            "asym_ids": identifiers.get("asym_ids") or [],
            "auth_asym_ids": identifiers.get("auth_asym_ids") or [],
            "uniprot_ids": identifiers.get("uniprot_ids") or [],
            "name": (entity.get("rcsb_polymer_entity") or {}).get("pdbx_description") or "",
            "polymer_type": (entity.get("entity_poly") or {}).get("rcsb_entity_polymer_type") or "",
            "organism": organism,
            "taxonomy_id": source.get("ncbi_taxonomy_id"),
        })

    nonpolymers: list[dict] = []
    for entity in node.get("nonpolymer_entities") or []:
        comp = entity.get("nonpolymer_comp") or {}
        chem = comp.get("chem_comp") or {}
        descriptor = comp.get("rcsb_chem_comp_descriptor") or {}
        identifiers = entity.get("rcsb_nonpolymer_entity_container_identifiers") or {}
        nonpolymers.append({
            "entity_id": entity.get("rcsb_id", ""),
            "ccd_id": chem.get("id") or "",
            "name": chem.get("name") or "",
            "formula": chem.get("formula") or "",
            "mw": chem.get("formula_weight"),
            "ccd_type": chem.get("type") or "",
            "smiles": descriptor.get("SMILES_stereo") or "",
            "inchikey": descriptor.get("InChIKey") or "",
            "asym_ids": identifiers.get("asym_ids") or [],
            "auth_asym_ids": identifiers.get("auth_asym_ids") or [],
        })

    assemblies: list[dict] = []
    for assembly in node.get("assemblies") or []:
        detail = assembly.get("rcsb_assembly_info") or {}
        assemblies.append({
            "assembly_id": detail.get("assembly_id") or "",
            "polymer_instances": detail.get("polymer_entity_instance_count"),
            "nonpolymer_instances": detail.get("nonpolymer_entity_instance_count"),
        })
    # Prefer assembly 1 when present; otherwise the lowest identifier offered.
    assembly_ids = [a["assembly_id"] for a in assemblies if a["assembly_id"]]
    default_assembly = "1" if "1" in assembly_ids else (sorted(assembly_ids)[0] if assembly_ids else "1")

    return EntryMetadata(
        pdb_id=(node.get("rcsb_id") or "").upper(),
        title=(node.get("struct") or {}).get("title") or "",
        method="; ".join(methods) or (info.get("experimental_method") or ""),
        resolution=float(resolutions[0]) if resolutions else None,
        deposit_date=(accession.get("deposit_date") or "")[:10],
        release_date=(accession.get("initial_release_date") or "")[:10],
        organism="; ".join(organisms[:4]),
        polymer_entity_count=int(info.get("polymer_entity_count") or 0),
        nonpolymer_entity_count=int(info.get("nonpolymer_entity_count") or 0),
        default_assembly_id=default_assembly,
        polymer_entities=polymers,
        nonpolymer_entities=nonpolymers,
        assemblies=assemblies,
    )


def fetch_entry_metadata(
    pdb_ids: Sequence[str],
    *,
    fetcher: Fetcher | None = None,
    batch: int = GRAPHQL_BATCH,
) -> Iterator[EntryMetadata]:
    """Yield metadata for every identifier, in batches, skipping ids RCSB drops."""
    fetcher = fetcher or Fetcher("rcsb")
    ids = [i.upper() for i in pdb_ids]
    for start in range(0, len(ids), batch):
        chunk = ids[start:start + batch]
        body = {"query": ENTRY_QUERY, "variables": {"ids": chunk}}
        try:
            payload = fetcher.fetch_json(
                GRAPHQL_URL, method="POST", json_body=body,
                key=f"gql_{request_hash('POST', GRAPHQL_URL, None, body)}",
            )
        except Exception:
            # A whole batch failing is recoverable: retry the chunk one id at a
            # time so a single bad entry cannot cost the other 49.
            if len(chunk) == 1:
                raise
            for single in chunk:
                try:
                    yield from fetch_entry_metadata([single], fetcher=fetcher, batch=1)
                except Exception:
                    continue
            continue
        for node in (payload.get("data") or {}).get("entries") or []:
            if node:
                yield parse_entry(node)


# --------------------------------------------------------------------------- #
# file service
# --------------------------------------------------------------------------- #

def assembly_url(pdb_id: str, assembly_id: str = "1") -> str:
    return f"{FILES_URL}/{pdb_id.upper()}-assembly{assembly_id}.cif.gz"


def entry_url(pdb_id: str) -> str:
    return f"{FILES_URL}/{pdb_id.lower()}.cif.gz"


def download_assembly(
    pdb_id: str,
    assembly_id: str = "1",
    *,
    fetcher: Fetcher | None = None,
    fall_back_to_entry: bool = True,
) -> Path:
    """Fetch a biological assembly mmCIF into the cache and return its path.

    Falls back to the deposited coordinate file when the assembly file is absent,
    which happens for a small number of older entries. The fallback is recorded
    by the returned filename so the manifest can distinguish the two.
    """
    pdb_id = pdb_id.upper()
    fetcher = fetcher or Fetcher("rcsb")
    ASSEMBLY_DIR.mkdir(parents=True, exist_ok=True)

    dest = ASSEMBLY_DIR / f"{pdb_id}-assembly{assembly_id}.cif.gz"
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    try:
        data = fetcher.fetch_bytes(
            assembly_url(pdb_id, assembly_id), key=f"asm_{pdb_id}_{assembly_id}"
        )
    except FileNotFoundError:
        if not fall_back_to_entry:
            raise
        data = fetcher.fetch_bytes(entry_url(pdb_id), key=f"entry_{pdb_id}")
        dest = ASSEMBLY_DIR / f"{pdb_id}-deposited.cif.gz"
        if dest.exists() and dest.stat().st_size > 0:
            return dest

    # The file service already serves gzip; store the bytes as received and
    # verify they decompress, so a truncated transfer fails now rather than in
    # the geometry pool an hour later.
    dest.write_bytes(data)
    try:
        with gzip.open(dest, "rb") as handle:
            handle.read(4096)
    except OSError as exc:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"{pdb_id}: assembly download is not valid gzip: {exc}") from exc
    return dest
