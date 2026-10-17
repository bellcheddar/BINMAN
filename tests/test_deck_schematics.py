"""The deck's schematics cannot drift from the code they describe.

A figure is the easiest thing in a project to leave behind: it is drawn once,
exported to an image, and then the code moves. These five are generated from
the manifests and from an `ast` parse of the repository, and these tests hold
that property rather than trusting it.

The second test is the one that found something. The spec's PLIP path
(openbabel, then PLIP, for interaction typing at each half-interface) is in
pixi.toml, in the reference table and in the README, and no module imports or
runs either tool: every `plip_types_a` in the atlas is null. `tenacity` and
`pydssp` are the same story, installed and credited and never called. A figure
drawn by hand would have printed all four names.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import deck_schematics as deck  # noqa: E402


def _svgs() -> list[Path]:
    return [ROOT / "docs" / f"schematic_{name}.svg" for name in deck.FIGURES]


def test_every_file_a_figure_names_is_in_the_repository():
    """_checked raises on a path that has been renamed away."""
    for panel in deck.PANELS:
        for module in panel["modules"]:
            assert deck._checked(module).exists()
    deck._verify_extras()


def test_no_figure_names_a_library_nothing_imports():
    """The claim each figure makes about the toolchain is the parse, so a
    library that no module reaches must not appear in any of them."""
    graph = deck.import_graph()
    used = set(graph["library_counts"])
    unused = [name for name in set(deck.LIBRARIES.values()) | set(deck.BINARIES.values())
              if name not in used]
    assert unused, "if everything in pixi.toml is imported, this test is moot"

    for path in _svgs():
        if not path.exists():
            pytest.skip("the schematics have not been generated")
        text = path.read_text(encoding="utf-8")
        named = [name for name in unused if name in text]
        assert not named, (
            f"{path.name} names {named}, which no module under pipeline/, lm/ "
            "or app/ imports or runs")


def test_the_committed_figures_match_what_the_generator_draws_now():
    """A stale SVG in docs/ is a figure describing a build that has moved."""
    for path in _svgs():
        if not path.exists():
            pytest.skip("the schematics have not been generated")

    data = deck.facts()
    graph = deck.import_graph()
    calls = {panel["num"]: deck._calls(panel["modules"]) for panel in deck.PANELS}
    for name, (_label, builder) in deck.FIGURES.items():
        drawn = (builder(data, graph) if name == "imports"
                 else builder(data, calls)).render()
        committed = (ROOT / "docs" / f"schematic_{name}.svg").read_text(
            encoding="utf-8")
        assert drawn == committed, (
            f"docs/schematic_{name}.svg is out of date: re-run "
            "pipeline/deck_schematics.py")


def test_the_canvas_is_the_slide():
    """The figures go on full bleed, so a canvas of the wrong shape would be
    stretched by PowerPoint rather than rejected."""
    assert (deck.WIDTH, deck.HEIGHT) == (1330, 698)
    for path in _svgs():
        if not path.exists():
            pytest.skip("the schematics have not been generated")
        assert f'viewBox="0 0 {deck.WIDTH} {deck.HEIGHT}"' in path.read_text(
            encoding="utf-8")
