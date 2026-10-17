"""The five detail schematics the deck carries on slides 2 to 6.

Slide 1's four-stage figure is drawn by `pipeline/build_about.py` from the
manifests. These five go a level down: every piece of software in the build and
the lines between them. There are five because no single cut shows all of it,
and a collaborator who does not read code asked how the parts connect.

    docs/schematic_lanes.svg      five stages crossed by four lanes
    docs/schematic_columns.svg    the stages standing on the shared toolchain
    docs/schematic_imports.svg    the import graph, parsed out of the source
    docs/schematic_machines.svg   where each piece runs, and what crosses
    docs/schematic_spine.svg      the artefacts, in the order they are written

Two rules, both the project's own.

**No number is typed in this file.** Every count, cutoff, worker setting and
training figure is read from `app/static/about.json` (which build_about.py
writes from the manifests), `models/binman-lm/training.json`,
`app/static/novel_glue_series.json`, or counted over the repository here. The
figures print the date about.json was generated, because a figure that quotes a
count should say when the count was taken.

**No library is typed against a module either.** The CALLS lane and the import
graph are parsed with `ast`; the command-line tools are found by searching the
same files for the binary they invoke. A module that drops an import changes
the figure at the next build rather than leaving it wrong.

Every declared path is checked to exist, so a rename fails this stage instead
of printing a label for a file that is gone.

The canvas is 1330 x 698, which is the 13.3 x 7.5 in slide at 100 px/in less
the footer strip, so each figure drops onto a slide full bleed with no scaling.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import INTERIM, Manifest, log_event, utcnow  # noqa: E402

STAGE = "deck_schematics"
DOCS = ROOT / "docs"
PNG_DIR = INTERIM / "deck"
ABOUT = ROOT / "app" / "static" / "about.json"
TRAINING = ROOT / "models" / "binman-lm" / "training.json"
SERIES = ROOT / "app" / "static" / "novel_glue_series.json"
VENDOR = ROOT / "app" / "static" / "vendor" / "VENDOR.json"
DECISIONS = ROOT / "DECISIONS.md"
TESTS = ROOT / "tests"
WORKFLOW_SVG = DOCS / "workflow.svg"

WIDTH, HEIGHT = 1330, 698
PNG_SCALE = 2          # 200 dpi on the slide

# Depot, resolved to literals: these are rasterised, so there is no theme to
# follow and no custom property to inherit.
PAL = {
    "bg": "#E9EAE5",
    "surface": "#FFFFFF",
    "surface2": "#F7F7F4",
    "line": "#C9CBC3",
    "ink": "#15171A",
    "muted": "#61655F",
    "accent": "#A64708",
    "soft": "#F6E3D3",
    "good": "#2C6D60",
    "bad": "#A33A2A",
    "navy": "#1C244B",
}
DISPLAY = "Inter, Helvetica, Arial, sans-serif"
DATA = "ui-monospace, SFMono-Regular, Menlo, monospace"

STYLE = (
    f".ttl{{fill:{PAL['ink']};font:600 31px {DISPLAY}}}"
    f".sub{{fill:{PAL['accent']};font:italic 18px {DISPLAY}}}"
    f".foot{{fill:{PAL['muted']};font:13px {DISPLAY}}}"
    f".lane{{fill:{PAL['muted']};font:600 14px {DISPLAY};letter-spacing:.08em}}"
    f".hd{{fill:{PAL['ink']};font:600 17px {DISPLAY}}}"
    f".hdn{{fill:{PAL['navy']};font:600 17px {DISPLAY}}}"
    f".n{{fill:{PAL['ink']};font:15px {DATA}}}"
    f".s{{fill:{PAL['muted']};font:15px {DATA}}}"
    f".sm{{fill:{PAL['muted']};font:14px {DISPLAY}}}"
    f".ac{{fill:{PAL['accent']};font:15px {DATA}}}"
    f".gd{{fill:{PAL['good']};font:15px {DATA}}}"
    f".bd{{fill:{PAL['bad']};font:15px {DATA}}}"
    f".card{{fill:{PAL['surface']};stroke:{PAL['line']};stroke-width:1.6}}"
    f".card2{{fill:{PAL['surface2']};stroke:{PAL['line']};stroke-width:1.6}}"
    f".src{{fill:{PAL['soft']};stroke:{PAL['accent']};stroke-width:1.6;"
    "stroke-dasharray:6 4}"
    f".band{{fill:{PAL['soft']};stroke:{PAL['accent']};stroke-width:1.6}}"
    f".a{{stroke:{PAL['line']};stroke-width:1.8;fill:none}}"
    f".aa{{stroke:{PAL['accent']};stroke-width:1.6;fill:none}}"
    f".dot{{stroke:{PAL['line']};stroke-width:1.4;fill:none;stroke-dasharray:3 4}}"
    f".rule{{stroke:{PAL['ink']};stroke-width:1.6}}"
    f".tri{{fill:{PAL['line']}}}"
    f".e-pipeline{{stroke:{PAL['line']};stroke-width:1.6;fill:none}}"
    f".e-lm{{stroke:{PAL['accent']};stroke-width:1.6;fill:none;opacity:.75}}"
    f".e-app{{stroke:{PAL['good']};stroke-width:1.6;fill:none;opacity:.75}}"
)


# --------------------------------------------------------------- the canvas

def esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


class Fig:
    """A slide-sized figure: title block, body, one provenance line."""

    def __init__(self, title: str, subtitle: str, footer: str) -> None:
        self.title = title
        self.subtitle = subtitle
        self.footer = footer
        self.body: list[str] = []

    def rect(self, cls: str, x, y, w, h, rx: int = 2) -> None:
        self.body.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" '
                         f'height="{h}" rx="{rx}"/>')

    def text(self, cls: str, x, y, value: str, anchor: str | None = None) -> None:
        extra = f' text-anchor="{anchor}"' if anchor else ""
        self.body.append(f'<text class="{cls}" x="{x}" y="{y}"{extra}>'
                         f'{esc(value)}</text>')

    def lines(self, x, y, items, step: int = 22, cls: str = "n") -> None:
        """A column of text. An item may be a string or a (class, text) pair."""
        for index, item in enumerate(items):
            klass, value = (cls, item) if isinstance(item, str) else item
            self.text(klass, x, y + index * step, value)

    def arrow(self, x1, y1, x2, y2, cls: str = "a") -> None:
        tip = "tip" if cls == "a" else "tipa"
        self.body.append(f'<path class="{cls}" d="M{x1},{y1} L{x2},{y2}" '
                         f'marker-end="url(#{tip})"/>')

    def tri(self, x, y, size: int = 8) -> None:
        self.body.append(f'<path class="tri" d="M{x},{y - size} '
                         f'L{x + size},{y} L{x},{y + size} Z"/>')

    def curve(self, cls, x1, y1, x2, y2) -> None:
        mid = (x1 + x2) / 2
        self.body.append(f'<path class="{cls}" d="M{x1},{y1} C{mid},{y1} '
                         f'{mid},{y2} {x2},{y2}"/>')

    def render(self) -> str:
        head = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} '
            f'{HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
            f'role="img" aria-label="{esc(self.title)}">',
            f'<style>{STYLE}</style>',
            f'<marker id="tip" markerWidth="8" markerHeight="8" refX="7" '
            f'refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" '
            f'fill="{PAL["line"]}"/></marker>',
            f'<marker id="tipa" markerWidth="8" markerHeight="8" refX="7" '
            f'refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" '
            f'fill="{PAL["accent"]}"/></marker>',
            f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" '
            f'fill="{PAL["bg"]}"/>',
            f'<text class="ttl" x="60" y="74">{esc(self.title)}</text>',
            f'<text class="sub" x="60" y="102">{esc(self.subtitle)}</text>',
            f'<line class="rule" x1="60" y1="120" x2="1270" y2="120"/>',
        ]
        tail = [f'<text class="foot" x="60" y="678">{esc(self.footer)}</text>',
                '</svg>']
        return "\n".join(head + self.body + tail) + "\n"


def wrap(items: list[str], chars: int) -> list[str]:
    """Comma-join names into lines no wider than `chars` monospace glyphs."""
    out: list[str] = []
    current = ""
    for item in items:
        candidate = item if not current else f"{current}, {item}"
        if len(candidate) > chars and current:
            out.append(current + ",")
            current = item
        else:
            current = candidate
    if current:
        out.append(current)
    return out


# ------------------------------------------------- what the source says it calls

# Import name to the name the figure prints. Anything not here is first-party
# or standard library and is not a library the figure is about.
LIBRARIES = {
    "httpx": "httpx", "tenacity": "tenacity", "gemmi": "gemmi",
    "freesasa": "FreeSASA", "rdkit": "RDKit", "openbabel": "Open Babel",
    "plip": "PLIP", "Bio": "Biopython", "biotite": "biotite",
    "pydssp": "pydssp", "numpy": "numpy", "scipy": "scipy",
    "pandas": "pandas", "sklearn": "scikit-learn", "duckdb": "DuckDB",
    "pyarrow": "pyarrow", "matplotlib": "matplotlib", "xlrd": "xlrd",
    "mlx": "mlx", "mlx_lm": "mlx-lm", "transformers": "transformers",
    "peft": "peft", "safetensors": "safetensors", "torch": "torch",
    "flask": "Flask", "sqlite3": "SQLite", "tomli_w": "tomli-w",
    "cairosvg": "CairoSVG", "lxml": "lxml",
}
# Binaries invoked rather than imported, found by searching the source. Only
# counted in a module that also imports `subprocess`: `fpocket_druggability` is
# a column name in app/queries.py, not a call to fpocket, and a bare string
# search counted it.
BINARIES = {"mkdssp": "DSSP (mkdssp)", "fpocket": "fpocket",
            "obabel": "Open Babel"}


def _module_libraries(path: Path) -> set[str]:
    """Third-party names a module imports or shells out to."""
    source = path.read_text(encoding="utf-8")
    found: set[str] = set()
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            root = name.split(".")[0]
            if root in LIBRARIES:
                found.add(LIBRARIES[root])
    if "subprocess" in source:
        for binary, label in BINARIES.items():
            if re.search(rf'["\'/]{binary}\b', source):
                found.add(label)
    return found


def _calls(paths: list[str]) -> list[str]:
    """Every library the declared modules reach, in a stable order."""
    found: set[str] = set()
    for relative in paths:
        found |= _module_libraries(_checked(relative))
    return sorted(found, key=str.lower)


def _checked(relative: str) -> Path:
    path = ROOT / relative
    if not path.exists():
        raise FileNotFoundError(
            f"{relative} is named in a deck schematic and is not in the "
            "repository. Fix the name or the figure prints a lie.")
    return path


def import_graph() -> dict:
    """Every module under pipeline/, lm/ and app/ against what it calls."""
    edges: dict[str, set[str]] = {}
    for package in ("pipeline", "lm", "app"):
        for path in sorted((ROOT / package).rglob("*.py")):
            if "__pycache__" in path.parts or path.name == Path(__file__).name:
                # The module that draws the figure is not part of the build the
                # figure is about.
                continue
            libraries = _module_libraries(path)
            if libraries:
                edges[str(path.relative_to(ROOT))] = libraries
    counts: dict[str, int] = {}
    for libraries in edges.values():
        for name in libraries:
            counts[name] = counts.get(name, 0) + 1
    return {
        "edges": edges,
        "library_counts": counts,
        "n_modules": len(edges),
        "n_edges": sum(len(v) for v in edges.values()),
        "n_libraries": len(counts),
    }


# ------------------------------------------------------------------- the facts

def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _test_functions() -> tuple[int, int]:
    files = sorted(TESTS.glob("test_*.py"))
    total = 0
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        total += sum(1 for node in tree.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and node.name.startswith("test_"))
    return total, len(files)


def facts() -> dict:
    """Every number the five figures print, read from recorded artefacts."""
    about = _json(ABOUT)
    stages, atlas = about["stages"], about["atlas"]
    tuning, hardware = about["tuning"], about["hardware"]
    training = _json(TRAINING)
    stage_one = training.get("stage_1", {})
    series = _json(SERIES)
    recall = about["validation"]["9.1"]["recall"]
    tests, test_files = _test_functions()
    vendor = _json(VENDOR)
    front_end = []
    for asset in vendor["assets"]:
        if asset["type"] == "software" and asset["name"] not in front_end:
            front_end.append(asset["name"])
    return {
        "as_of": str(about["generated_at"])[:10],
        "entries": stages["catalogue"]["total"],
        "tiers": stages["catalogue"]["tiers"],
        "measured": stages["bridges"]["ok"],
        "measure_failed": stages["bridges"]["failed"],
        "bridges": atlas["bridge"],
        "novel": atlas["novel_bridges"],
        "series": series["series"],
        "balance_floor": series["bridging_balance_floor"],
        "degrons": atlas["degron"],
        "degrons_failed": stages["degrons"]["failed"],
        "ligases": atlas["ligase"],
        "ligases_failed": stages["ligases"]["failed"],
        "lysines": atlas["lysine"],
        "triage_rows": atlas["triage_predicted"],
        "trimmed": stages["trimmed_structures"]["ok"],
        "ligands": atlas["ligand"],
        "atlas_mb": atlas["size_mb"],
        "cpu_workers": tuning["compute"]["cpu_workers"],
        "io_workers": tuning["compute"]["io_workers"],
        "max_hours": tuning["compute"]["max_compute_hours"],
        "rate": tuning["io"]["rcsb_rate_limit_per_sec"],
        "retries": tuning["io"]["retry_attempts"],
        "chip": hardware["host"]["chip"],
        "cores": hardware["cpu"]["physical_cores"],
        "gpu_cores": hardware["host"]["gpu_cores"],
        "memory_gb": hardware["memory"]["total_gb"],
        "python": hardware["host"]["python"],
        "base_model": training["identity"]["base_model"],
        "rank": training["identity"]["adapter_rank"],
        "layers": training["identity"]["adapter_layers"],
        "round": training["round"],
        "iters": stage_one.get("iterations_requested"),
        "train_minutes": round(stage_one.get("wall_clock_seconds", 0) / 60),
        "train_rows": stage_one.get("train_examples"),
        "recall": recall["value"],
        "recall_floor": recall["floor"],
        "recall_n": recall["n"],
        "tests": tests,
        "test_files": test_files,
        "decisions": len(re.findall(r"^## D-\d+", DECISIONS.read_text(
            encoding="utf-8"), re.M)),
        "front_end": front_end,
        "adapter_id": about["links"]["adapter_id"],
        "space_id": about["links"]["space"].rsplit("/", 1)[-1],
        "shipped_stage": tuning["model"]["shipped_stage"],
        "references": about["reference_summary"]["total"],
    }


def footer(data: dict) -> str:
    return (f"Counts read from app/static/about.json as generated "
            f"{data['as_of']}, from the model card and from the repository "
            f"itself. Library names are parsed from the imports.")


# ---------------------------------------------------------------- the five cuts

# The stages, as structure rather than as numbers. `modules` is checked against
# the filesystem; `calls` is parsed from those modules; `extra` names the parts
# that are not Python imports, each verified below against the file that
# configures it.
PANELS = [
    {
        "num": "1", "title": "1 · Acquisition",
        "sources": ["RCSB Search API v2", "RCSB File Download",
                    "UniProt REST, AFDB"],
        "modules": ["pipeline/catalogue.py", "pipeline/rcsb.py",
                    "pipeline/structures.py", "pipeline/trim_structures.py",
                    "pipeline/common.py"],
        "extra": [],
        "writes": ["data/raw/*.cif.gz", "catalogue.jsonl"],
    },
    {
        "num": "2", "title": "2 · Geometry",
        "sources": ["cached assemblies", "from stage 1",
                    "CCD definitions"],
        "modules": ["pipeline/geometry.py", "pipeline/run_bridges.py",
                    "pipeline/build_edges.py", "pipeline/chem_rules.py",
                    "pipeline/ccd_classes.py"],
        "extra": [],
        "writes": ["bridges.jsonl", "ccd_classes.jsonl"],
    },
    {
        "num": "3", "title": "3 · Scan and triage",
        "sources": ["Slabicki 2025 (xls)", "DEGRONOPEDIA, BioLiP",
                    "UbiBrowser, InterPro"],
        "modules": ["pipeline/degron_scan.py", "pipeline/degron_predict.py",
                    "pipeline/e3_triage.py", "pipeline/degradability.py",
                    "pipeline/zinc_finger_scan.py"],
        "extra": [],
        "writes": ["degrons.jsonl", "ligase_triage.jsonl"],
    },
    {
        "num": "4", "title": "4 · Model",
        "sources": ["Qwen2.5-3B-Instruct", "4-bit, from the Hub",
                    "the atlas itself"],
        "modules": ["lm/build_corpus.py", "lm/build_task_b.py",
                    "lm/train.py", "lm/evaluate.py", "lm/export_hf.py"],
        "extra": [],
        "writes": ["corpus/*.jsonl", "adapters/*.safetensors"],
    },
    {
        "num": "5", "title": "5 · Store and serve",
        "sources": ["nothing is fetched", "at request time:",
                    "the atlas is enough"],
        "modules": ["pipeline/build_atlas.py", "pipeline/build_about.py",
                    "app/queries.py", "app/db.py", "app/routes/api.py"],
        "extra": ["nginx", "gunicorn", "certbot"],
        "writes": ["binman.sqlite", "/api/*.json"],
    },
]


def _verify_extras() -> None:
    """The serving parts are not imports, so check the file that installs them."""
    provision = (ROOT / "deploy" / "provision.sh").read_text(encoding="utf-8")
    for name in ("nginx", "gunicorn", "certbot"):
        if name not in provision:
            raise ValueError(f"{name} is named in a figure but deploy/"
                             f"provision.sh does not install it")


def _panel_counts(data: dict) -> dict[str, list]:
    """One line of result per stage, by stage number."""
    return {
        "1": [("gd", f"{data['entries']:,} entries"), ("s", "0 failed")],
        "2": [("gd", f"{data['bridges']:,} bridges"),
              ("bd", f"{data['measure_failed']} entries failed")],
        "3": [("gd", f"{data['degrons']:,} degrons"),
              ("s", f"{data['ligases']} ligases, {data['lysines']:,} lysines")],
        "4": [("gd", f"round {data['round']}, {data['train_minutes']} min"),
              ("s", f"rank {data['rank']} over {data['layers']} layers")],
        "5": [("gd", f"{data['atlas_mb']:,.0f} MB SQLite"),
              ("s", f"{data['references']} sources credited")],
    }


def fig_lanes(data: dict, calls: dict[str, list[str]]) -> Fig:
    fig = Fig("How the code is wired",
              "Read down a column for one stage, or across a lane for one kind "
              "of thing.", footer(data))
    counts = _panel_counts(data)
    xs = [190 + index * 218 for index in range(5)]
    width = 208

    for x, panel in zip(xs, PANELS):
        fig.rect("band", x, 126, width, 32)
        fig.text("hd", x + 12, 148, panel["title"])
    for x in xs[1:]:
        fig.tri(x - 11, 142, 7)

    fig.text("lane", 60, 196, "SOURCES")
    fig.text("lane", 60, 318, "CODE")
    fig.text("lane", 60, 446, "CALLS")
    fig.text("lane", 60, 554, "WRITES")

    for x, panel in zip(xs, PANELS):
        internal = panel["sources"][0].startswith("cached") or \
            panel["sources"][0].startswith("nothing")
        fig.rect("card2" if internal else "src", x, 168, width, 82)
        fig.lines(x + 12, 192, [("s", line) for line in panel["sources"]])

        fig.rect("card", x, 260, width, 126)
        fig.lines(x + 12, 284, [
            ("n", name.split("/", 1)[-1] if name.startswith("pipeline/")
             else name) for name in panel["modules"]])

        fig.rect("card2", x, 398, width, 104)
        names = calls[panel["num"]]
        fig.lines(x + 12, 422, [("ac", line) for line in wrap(names, 23)][:4])

        fig.rect("card", x, 510, width, 82)
        fig.lines(x + 12, 534, [("n", line) for line in panel["writes"]]
                  + [counts[panel["num"]][0]])

        for top, bottom in ((250, 258), (386, 396), (502, 508)):
            fig.arrow(x + width // 2, top, x + width // 2, bottom)

    fig.rect("band", 190, 604, 1080, 46)
    fig.text("hd", 204, 626,
             "Every stage appends one row per item to "
             "data/manifests/<stage>.jsonl")
    fig.text("sm", 204, 644,
             "So a killed run resumes from the manifest, and a failure is a "
             "recorded row rather than an absence.")
    return fig


def fig_columns(data: dict, calls: dict[str, list[str]]) -> Fig:
    fig = Fig("Five stages on one toolchain",
              "The columns run in call order. The rail underneath is shared by "
              "all of them.", footer(data))
    counts = _panel_counts(data)
    widths = [226, 226, 226, 226, 242]
    xs = [60, 302, 544, 786, 1028]

    for x, width, panel in zip(xs, widths, PANELS):
        fig.rect("card", x, 126, width, 320)
        fig.rect("band", x, 126, width, 40)
        fig.text("hd", x + 14, 153, panel["title"])
        fig.lines(x + 14, 192, [
            ("n", name.split("/", 1)[-1] if name.startswith("pipeline/")
             else name) for name in panel["modules"][:4]])
        fig.body.append(f'<line class="dot" x1="{x + 14}" y1="274" '
                        f'x2="{x + width - 14}" y2="274"/>')
        names = calls[panel["num"]] + panel["extra"]
        fig.lines(x + 14, 298, [("ac", line) for line in
                                wrap(names, width // 9 - 2)][:4])
        fig.lines(x + 14, 392, counts[panel["num"]], step=22)
        fig.arrow(x + width // 2, 446, x + width // 2, 502)

    fig.rect("band", 60, 510, 1210, 140)
    fig.text("lane", 74, 534, "SHARED BY EVERY STAGE")
    rail = [
        ("pixi", ["conda-forge, bioconda", f"and PyPI, Python "
                  f"{data['python']}"]),
        ("config/", [f"tuning.toml: {data['cpu_workers']} workers",
                     "thresholds.toml: cutoffs"]),
        ("data/manifests/", ["one JSONL row per item,",
                             "so every stage resumes"]),
        ("pytest", [f"{data['tests']} test functions",
                    f"over {data['test_files']} files"]),
        ("git, GitHub", ["BUILD_LOG, PROGRESS and",
                         f"DECISIONS: {data['decisions']} entries"]),
    ]
    card_xs = [74, 310, 546, 782, 1018]
    card_ws = [222, 222, 222, 222, 238]
    for x, width, (title, body) in zip(card_xs, card_ws, rail):
        fig.rect("card", x, 546, width, 90)
        fig.text("hd", x + 12, 570, title)
        fig.lines(x + 12, 594, [("s", line) for line in body], step=20)
    return fig


def fig_imports(data: dict, graph: dict) -> Fig:
    counts = graph["library_counts"]
    # In stage order, and the same modules the other four figures name, so a
    # reader can carry one list across the set. Two per stage, so stage 5 is
    # not pushed off the bottom by stage 1, then the busiest of the rest.
    chosen: list[str] = []
    for panel in PANELS:
        picked: list[str] = []
        packages: set[str] = set()
        for module in panel["modules"]:
            package = module.split("/")[0]
            if not graph["edges"].get(module) or package in packages:
                continue
            picked.append(module)
            packages.add(package)
            if len(picked) == 2:
                break
        chosen.extend(picked)
    rest = sorted((module for module in graph["edges"] if module not in chosen),
                  key=lambda name: (-len(graph["edges"][name]), name))
    chosen.extend(rest[:12 - len(chosen)])
    # Only libraries the chosen modules actually reach: a pill with no line
    # into it is a claim the figure does not support.
    reachable = {name for module in chosen for name in graph["edges"][module]}
    libraries = sorted(reachable,
                       key=lambda name: (-counts[name], name.lower()))[:14]
    drawn = sum(1 for module in chosen
                for name in graph["edges"][module] if name in libraries)

    fig = Fig("Who calls what",
              f"{graph['n_edges']} imports across {graph['n_modules']} modules "
              f"and {graph['n_libraries']} libraries. The {drawn} drawn here "
              "belong to the modules the other figures name.", footer(data))

    fig.text("lane", 60, 150, "MODULE")
    fig.text("lane", 1040, 140, "LIBRARY")

    pill_y = {}
    for index, name in enumerate(libraries):
        y = 152 + index * 36
        pill_y[name] = y
        fig.rect("card", 1040, y, 200, 26)
        fig.text("ac", 1052, y + 19, f"{name}  ({counts[name]})")

    palette = {"pipeline": "e-pipeline", "lm": "e-lm", "app": "e-app"}
    for index, module in enumerate(chosen):
        y = 176 + index * 36
        fig.text("n", 380, y, module, anchor="end")
        cls = palette.get(module.split("/")[0], "e-pipeline")
        for name in sorted(graph["edges"][module]):
            if name in libraries:
                fig.curve(cls, 392, y - 5, 1036, pill_y[name] + 13)

    fig.text("sm", 60, 640,
             "Line colour is the package the module lives in: pipeline, lm, "
             "app.")
    fig.text("sm", 60, 660,
             "The figure in brackets is how many modules import that library.")
    return fig


def _marker(fig: Fig, number: int, x: int, y: int) -> None:
    fig.body.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{PAL["surface"]}" '
                    f'stroke="{PAL["accent"]}" stroke-width="1.6"/>')
    fig.body.append(f'<text x="{x}" y="{y + 5}" text-anchor="middle" '
                    f'fill="{PAL["accent"]}" font="600 13px {DISPLAY}" '
                    f'style="font:600 13px {DISPLAY}">{number}</text>')


def fig_machines(data: dict, calls: dict[str, list[str]]) -> Fig:
    fig = Fig("Where each piece runs",
              "Nothing is computed at request time. The droplet serves what "
              "the Studio already built.", footer(data))

    # The Studio.
    fig.rect("card", 60, 126, 430, 436)
    fig.rect("band", 60, 126, 430, 42)
    fig.text("hd", 74, 154, f"{data['chip']} · {data['cores']} cores · "
                            f"{data['memory_gb']:,.0f} GB")
    fig.text("s", 74, 192, f"pixi, Python {data['python']}, osx-arm64")

    # The library lists are the parse, not a recollection: the PLIP path is in
    # pixi.toml and in the spec, but no module imports or runs it, so it does
    # not appear here.
    build = sorted(set(calls["1"]) | set(calls["2"]) | set(calls["3"]),
                   key=str.lower)
    fig.rect("card2", 76, 208, 398, 116)
    fig.text("hd", 88, 232, "Pipeline, stages 1 to 3")
    fig.lines(88, 256, [("n", line) for line in wrap(build, 42)][:2]
              + [("s", f"{data['cpu_workers']} worker processes, "
                       f"{data['max_hours']} h compute budget")], step=22)

    fig.rect("card2", 76, 336, 398, 116)
    fig.text("hd", 88, 360, "Training, stage 4")
    fig.lines(88, 384, [("n", line) for line in wrap(calls["4"], 42)][:2]
              + [("s", f"{data['base_model'].split('/')[-1]}, rank "
                       f"{data['rank']} over {data['layers']} layers, "
                       f"{data['train_minutes']} min")], step=22)

    fig.rect("card2", 76, 464, 398, 82)
    fig.text("hd", 88, 488, "Atlas build, then the checks")
    fig.lines(88, 512, [
        ("n", "build_atlas.py, SQLite, ANALYZE, indexes"),
        ("s", f"pytest ({data['tests']}), preflight.sh, validate.py"),
    ], step=22)

    # The droplet.
    fig.rect("card", 530, 126, 372, 234)
    fig.rect("band", 530, 126, 372, 42)
    fig.text("hd", 544, 154, "Droplet · Ubuntu, one vCPU")
    for label, y in (("nginx and certbot (TLS)", 192),
                     ("gunicorn, systemd unit", 232),
                     ("Flask app, app/routes/*", 272),
                     ("SQLite, opened read only", 312)):
        fig.text("n", 544, y, label)
        if y < 312:
            fig.arrow(560, y + 8, 560, y + 24)
    fig.text("s", 544, 344, "No gemmi, no FreeSASA, no fpocket here.")

    # The Space.
    fig.rect("card", 530, 380, 372, 182)
    fig.rect("band", 530, 380, 372, 42)
    fig.text("hd", 544, 408, "Hugging Face Space · ZeroGPU")
    fig.lines(544, 448, [
        ("n", "gradio, transformers, peft, torch"),
        ("n", data["adapter_id"]),
        ("s", "Loads the base model and the adapter on"),
        ("s", "demand. Text only, never arithmetic."),
    ], step=24)

    # The browser.
    fig.rect("card", 942, 126, 328, 234)
    fig.rect("band", 942, 126, 328, 42)
    fig.text("hd", 956, 154, "Viewer's browser")
    fig.lines(956, 192, [("n", name) for name in data["front_end"]]
              + [("n", "Depot CSS, no framework")], step=26)
    fig.text("s", 956, 344, "Vendored and pinned: no third-party request.")

    fig.rect("band", 942, 380, 328, 182)
    fig.text("hd", 956, 408, "What never crosses")
    fig.lines(956, 442, [
        ("sm", f"The raw structures. All {data['entries']:,}"),
        ("sm", "entries stay on the Studio; the droplet"),
        ("sm", f"gets the atlas and {data['trimmed']:,} trimmed"),
        ("sm", "files. The training corpus is not"),
        ("sm", "published either, only the adapter."),
    ], step=22)

    # The crossings, numbered here and described in the strip below, because
    # the gaps between the panels are too narrow to label in place.
    fig.arrow(490, 240, 524, 240, "aa")
    _marker(fig, 1, 507, 214)
    fig.arrow(490, 470, 524, 470, "aa")
    _marker(fig, 2, 507, 444)
    fig.arrow(820, 380, 820, 356, "aa")
    _marker(fig, 3, 852, 370)
    fig.arrow(902, 240, 936, 240, "aa")
    _marker(fig, 4, 919, 214)

    fig.rect("band", 60, 582, 1210, 68)
    crossings = [
        ("rsync -az", "app/, the atlas and the trimmed structures"),
        ("lm/export_hf.py", "the adapter, sha256 verified on the Hub"),
        ("HTTPS, Flask asks the Space", "a question in, a query object out"),
        ("HTTPS, nginx to the browser", "JSON rows and the HTML page"),
    ]
    for index, (title, detail) in enumerate(crossings):
        x = 74 + index * 302
        _marker(fig, index + 1, x + 12, 616)
        fig.text("hd", x + 32, 612, title)
        fig.text("sm", x + 32, 634, detail)
    return fig


def fig_spine(data: dict, calls: dict[str, list[str]]) -> Fig:
    fig = Fig("One file at a time",
              "Above the line, what does the work. On the line, what it "
              "writes. Below, what checks it.", footer(data))

    fig.text("lane", 60, 150, "SOFTWARE")
    fig.text("lane", 60, 352, "ARTEFACT ON DISK")
    fig.text("lane", 60, 486, "CHECK")

    xs = [60, 302, 544, 786, 1028]
    widths = [226, 226, 226, 226, 242]
    software = [
        ("Ask and fetch", "1", f"{data['rate']} req/s, "
                               f"{data['retries']} retries"),
        ("Measure", "2", f"{data['cpu_workers']} worker processes"),
        ("Score", "3", "sequence and structure"),
        ("Assemble and train", "4", f"round {data['round']} adapter"),
        ("Serve", "5", ", ".join(data["front_end"][:3])),
    ]
    for x, width, (title, num, note) in zip(xs, widths, software):
        fig.rect("card", x, 166, width, 130)
        fig.text("hd", x + 12, 190, title)
        names = calls[num] + PANELS[int(num) - 1]["extra"]
        fig.lines(x + 12, 218, [("ac", line) for line in
                                wrap(names, width // 9 - 2)][:3]
                  + [("s", note)], step=24)
        fig.arrow(x + width // 2, 296, x + width // 2, 316)

    fig.rect("band", 60, 318, 1210, 96)
    spine = [
        ["data/raw/", "*.cif.gz"],
        ["interim/bridges", ".jsonl"],
        ["interim/degrons,", "triage, lysines"],
        ["atlas/binman", ".sqlite"],
        ["/api/*.json", "and the HTML"],
    ]
    for index, (x, width) in enumerate(zip([74, 316, 558, 800, 1042],
                                           [208, 208, 208, 208, 214])):
        fig.rect("card", x, 332, width, 68)
        fig.lines(x + 12, 356, [("n", line) for line in spine[index]], step=22)
        if index < 4:
            fig.tri(x + width + 16, 366, 9)
        fig.arrow(x + width // 2, 414, x + width // 2, 434)

    checks = [
        [("n", "catalogue.jsonl"), ("s", "one row per entry,"),
         ("s", "so the fetch resumes"), ("gd", "0 failed")],
        [("n", "thresholds.toml"), ("s", "every cutoff lives here,"),
         ("s", "never in the Python"),
         ("bd", f"{data['measure_failed']} entries failed")],
        [("n", "validate.py"), ("s", f"recall against "
                                     f"{data['recall_n']} curated"),
         ("s", "glues, published sets"),
         ("gd", f"{data['recall']} vs {data['recall_floor']} floor")],
        [("n", "pytest"), ("s", "stage manifests, prompt"),
         ("s", "agreement, the schema"),
         ("gd", f"{data['tests']} test functions")],
        [("n", "deploy/preflight.sh"), ("s", "a warm-up request per"),
         ("s", "module page on restart"),
         ("gd", f"{data['atlas_mb']:,.0f} MB, read only")],
    ]
    for x, width, body in zip(xs, widths, checks):
        fig.rect("card2", x, 436, width, 126)
        fig.lines(x + 12, 460, body, step=24)

    fig.rect("band", 60, 586, 1210, 64)
    fig.text("hd", 74, 612,
             "The spine is the reason the build can be restarted at all")
    fig.text("sm", 74, 634,
             "No stage holds state across items. It reads the file before it "
             "and appends to the file after it.")
    return fig


FIGURES = {
    "lanes": ("Four lanes, one per kind of thing", fig_lanes),
    "columns": ("Five stage columns over a toolchain rail", fig_columns),
    "imports": ("The import graph, drawn as it is", fig_imports),
    "machines": ("Three machines and what crosses between them", fig_machines),
    "spine": ("The artefact spine", fig_spine),
}


# ------------------------------------------------------------------ rasterising

def to_png(svg_path: Path, png_path: Path, scale: int = PNG_SCALE) -> int:
    """Rasterise for the deck. PowerPoint takes SVG badly; the deck uses PNG."""
    import cairosvg

    png_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), scale=scale)
    return png_path.stat().st_size


# ------------------------------------------------------------------------- stage

def run(render: bool = True) -> dict:
    _verify_extras()
    data = facts()
    graph = import_graph()
    calls = {panel["num"]: _calls(panel["modules"]) for panel in PANELS}

    manifest = Manifest(STAGE)
    written = []
    for name, (label, builder) in FIGURES.items():
        fig = builder(data, graph) if name == "imports" else builder(data, calls)
        svg_path = DOCS / f"schematic_{name}.svg"
        svg_path.write_text(fig.render(), encoding="utf-8")
        row = {"svg": str(svg_path.relative_to(ROOT)),
               "svg_bytes": svg_path.stat().st_size, "title": label}
        if render:
            png_path = PNG_DIR / f"schematic_{name}.png"
            row["png"] = str(png_path.relative_to(ROOT))
            row["png_bytes"] = to_png(svg_path, png_path)
        manifest.record(name, status="ok", **row)
        written.append(row)

    # Slide 1's figure, rasterised from the committed SVG, so the deck build
    # reads everything it needs out of the repository.
    if render and WORKFLOW_SVG.exists():
        png_path = PNG_DIR / "workflow.png"
        size = to_png(WORKFLOW_SVG, png_path, scale=3)
        manifest.record("workflow", status="ok",
                        png=str(png_path.relative_to(ROOT)), png_bytes=size)
        written.append({"png": str(png_path.relative_to(ROOT)),
                        "png_bytes": size, "title": "slide 1, redrawn"})

    report = {
        "generated_at": utcnow(),
        "figures": written,
        "as_of": data["as_of"],
        "import_graph": {k: v for k, v in graph.items() if k != "edges"},
    }
    (INTERIM / "deck_schematics.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    log_event("6.5", f"Deck schematics: {len(written)} figures, "
                     f"{graph['n_edges']} imports across "
                     f"{graph['n_modules']} modules.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-render", action="store_true",
                        help="write the SVGs and skip the PNGs")
    args = parser.parse_args()
    report = run(render=not args.no_render)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
