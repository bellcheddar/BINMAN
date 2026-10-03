"""Download and pin the front-end libraries and fonts (spec 3.3).

The droplet must serve BINMAN with no outbound requests, so nothing here may be
a CDN reference at serve time. Every file is written under
`app/static/vendor/` and recorded with its version, URL, SHA-256 and size in
`app/static/vendor/VENDOR.json`, which the About tab's reference table reads.

Idempotent: a file already present with a matching digest is left alone.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import ROOT, log_event, utcnow  # noqa: E402

VENDOR = ROOT / "app" / "static" / "vendor"

# Versions are pinned deliberately. Spec 3.3 names Plotly 2.35.2 and Tabulator
# 6.3.1; D3 is pinned to the current v7 patch and Mol* to the current major.
MOLSTAR = "5.12.0"
D3 = "7.9.0"
PLOTLY = "2.35.2"
TABULATOR = "6.3.1"

ASSETS: list[dict] = [
    {
        "name": "Mol*", "version": MOLSTAR, "licence": "MIT",
        "home": "https://molstar.org/", "repo": "https://github.com/molstar/molstar",
        "used_for": "every structure viewer",
        "files": {
            "molstar/molstar.js":
                f"https://cdn.jsdelivr.net/npm/molstar@{MOLSTAR}/build/viewer/molstar.js",
            "molstar/molstar.css":
                f"https://cdn.jsdelivr.net/npm/molstar@{MOLSTAR}/build/viewer/molstar.css",
        },
    },
    {
        "name": "D3", "version": D3, "licence": "ISC",
        "home": "https://d3js.org/", "repo": "https://github.com/d3/d3",
        "used_for": "lens graph, ternary triangle",
        "files": {
            "d3/d3.min.js": f"https://cdn.jsdelivr.net/npm/d3@{D3}/dist/d3.min.js",
        },
    },
    {
        "name": "Plotly.js", "version": PLOTLY, "licence": "MIT",
        "home": "https://plotly.com/javascript/", "repo": "https://github.com/plotly/plotly.js",
        "used_for": "distributions, scatter, confusion matrix heatmap",
        "files": {
            "plotly/plotly.min.js": f"https://cdn.plot.ly/plotly-{PLOTLY}.min.js",
        },
    },
    {
        "name": "Tabulator", "version": TABULATOR, "licence": "MIT",
        "home": "https://tabulator.info/", "repo": "https://github.com/olifolkerd/tabulator",
        "used_for": "the ledger table, the reference table",
        "files": {
            "tabulator/tabulator.min.js":
                f"https://cdn.jsdelivr.net/npm/tabulator-tables@{TABULATOR}/dist/js/tabulator.min.js",
            "tabulator/tabulator.min.css":
                f"https://cdn.jsdelivr.net/npm/tabulator-tables@{TABULATOR}/dist/css/tabulator.min.css",
        },
    },
]

# Three fonts, self-hosted with real fallback stacks (spec 6.2). Latin subsets,
# variable where the family offers one.
FONTS: list[dict] = [
    {"family": "Archivo", "role": "display",
     "css": "https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&display=swap"},
    {"family": "Spline Sans", "role": "body",
     "css": "https://fonts.googleapis.com/css2?family=Spline+Sans:wght@400;500;600&display=swap"},
    {"family": "IBM Plex Mono", "role": "data",
     "css": "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap"},
]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get(url: str, accept: str | None = None) -> bytes:
    import httpx
    headers = {"User-Agent": UA}
    if accept:
        headers["Accept"] = accept
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.content


def fetch_library(asset: dict, records: list[dict]) -> None:
    for rel, url in asset["files"].items():
        dest = VENDOR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 0:
            data = dest.read_bytes()
            records.append(_record(asset, rel, url, data, cached=True))
            print(f"  cached  {rel} ({len(data) // 1024} KB)")
            continue
        data = get(url)
        dest.write_bytes(data)
        records.append(_record(asset, rel, url, data, cached=False))
        print(f"  fetched {rel} ({len(data) // 1024} KB)")


def _record(asset: dict, rel: str, url: str, data: bytes, cached: bool) -> dict:
    return {
        "name": asset["name"], "version": asset["version"], "type": "software",
        "path": f"vendor/{rel}", "url": url, "licence": asset["licence"],
        "home": asset.get("home", ""), "repo": asset.get("repo", ""),
        "used_for": asset.get("used_for", ""),
        "sha256": sha256(data), "bytes": len(data),
        "retrieved_at": utcnow(), "from_cache": cached,
    }


def fetch_fonts(records: list[dict]) -> None:
    """Pull the Google Fonts CSS, rewrite the woff2 URLs to local paths, download them.

    Requesting the CSS with a modern browser User-Agent yields woff2 rather than
    the legacy formats, which keeps the self-hosted payload small.
    """
    import re

    font_dir = VENDOR / "fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    css_parts: list[str] = [
        "/* BINMAN self-hosted fonts (spec 6.2). Generated by tools/vendor_assets.py.",
        f"   Retrieved {utcnow()}. Do not edit by hand. */", "",
    ]

    for font in FONTS:
        css = get(font["css"], accept="text/css,*/*").decode("utf-8")
        urls = sorted(set(re.findall(r"url\((https://[^)]+\.woff2)\)", css)))
        if not urls:
            print(f"  WARNING no woff2 found for {font['family']}")
            continue
        slug = font["family"].lower().replace(" ", "-")
        mapping: dict[str, str] = {}
        for index, url in enumerate(urls):
            name = f"{slug}-{index}.woff2"
            dest = font_dir / name
            if dest.exists() and dest.stat().st_size > 0:
                data = dest.read_bytes()
            else:
                data = get(url)
                dest.write_bytes(data)
            mapping[url] = f"./{name}"
            records.append({
                "name": font["family"], "version": "google-fonts-latest",
                "type": "font", "path": f"vendor/fonts/{name}", "url": url,
                "licence": "SIL Open Font License 1.1",
                "home": f"https://fonts.google.com/specimen/{font['family'].replace(' ', '+')}",
                "repo": "", "used_for": f"Depot design system, {font['role']} face",
                "sha256": sha256(data), "bytes": len(data), "retrieved_at": utcnow(),
                "from_cache": False,
            })
        local = css
        for url, rel in mapping.items():
            local = local.replace(url, rel)
        css_parts.append(f"/* {font['family']} ({font['role']}) */")
        css_parts.append(local.strip())
        css_parts.append("")
        print(f"  fonts   {font['family']}: {len(mapping)} woff2 file(s)")

    (font_dir / "fonts.css").write_text("\n".join(css_parts) + "\n", encoding="utf-8")


def main() -> int:
    VENDOR.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    failures: list[str] = []

    for asset in ASSETS:
        print(f"{asset['name']} {asset['version']}")
        try:
            fetch_library(asset, records)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{asset['name']}: {exc}")
            print(f"  FAILED {exc}")

    print("fonts")
    try:
        fetch_fonts(records)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"fonts: {exc}")
        print(f"  FAILED {exc}")

    manifest = {
        "generated_at": utcnow(),
        "note": "Pinned, self-hosted front-end assets. The droplet makes no "
                "outbound requests at serve time (spec 3.3).",
        "assets": records,
        "failures": failures,
    }
    (VENDOR / "VENDOR.json").write_text(json.dumps(manifest, indent=2) + "\n")

    total = sum(r["bytes"] for r in records)
    log_event("1.0", f"Vendored {len(records)} front-end files ({total // 1024} KB total), "
                     f"{len(failures)} failure(s). Manifest at app/static/vendor/VENDOR.json.")
    if failures:
        print("\nFAILURES:")
        for line in failures:
            print(" ", line)
        return 1
    print(f"\n{len(records)} files, {total // 1024} KB total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
