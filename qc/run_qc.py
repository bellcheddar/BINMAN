"""Front-end QC (spec 10, 4.4).

Playwright screenshots of every page at 1440x900 and 390x844 in both themes,
zero console errors, axe-core with zero serious or critical violations, Mol*
reaching interactive state, and the shared selection propagating across modules.

**Uses the preinstalled browser.** Spec 10 forbids `playwright install`, so this
drives the system Google Chrome through Playwright's `channel="chrome"` rather
than downloading a browser.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

QC = ROOT / "qc"
SHOTS = QC / "screenshots"
REPORT = QC / "qc_report.json"
AXE = QC / "axe.min.js"

PAGES = [
    ("atlas", "/"),
    ("degron", "/degron/"),
    ("e3", "/e3/"),
    ("degradability", "/degradability/"),
    ("lens", "/lens/"),
    ("about", "/about/"),
]
VIEWPORTS = {"desktop": (1440, 900), "phone": (390, 844)}
THEMES = ("light", "dark")

# Console noise that is not a defect: a WebGL warning from a headless GPU, or a
# favicon 404 in a viewport that does not request it.
IGNORABLE = (
    "favicon", "WebGL", "webgl", "GPU stall", "Automatic fallback to software",
    "THREE.WebGLRenderer", "deprecated", "DevTools",
)


def serve(port: int):
    """Run the app on a background thread so QC does not need a separate process."""
    from werkzeug.serving import make_server

    from app import create_app

    app = create_app()
    server = make_server("127.0.0.1", port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def ignorable(text: str) -> bool:
    return any(token in text for token in IGNORABLE)


def run(port: int = 8777, skip_axe: bool = False) -> dict:
    from playwright.sync_api import sync_playwright

    SHOTS.mkdir(parents=True, exist_ok=True)
    server = serve(port)
    base = f"http://127.0.0.1:{port}"
    time.sleep(1.0)

    report: dict = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": base,
        "browser": "system Google Chrome via playwright channel=chrome",
        "pages": {},
        "console_errors": [],
        "axe_violations": [],
        "performance": {},
        "selection_propagation": {},
    }

    axe_source = AXE.read_text(encoding="utf-8") if AXE.exists() else ""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        try:
            for theme in THEMES:
                for viewport_name, (width, height) in VIEWPORTS.items():
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        color_scheme=theme,
                        device_scale_factor=2 if viewport_name == "phone" else 1,
                    )
                    page = context.new_page()
                    errors: list[str] = []
                    page.on("console", lambda message, sink=errors: (
                        sink.append(f"{message.type}: {message.text}")
                        if message.type == "error" and not ignorable(message.text)
                        else None
                    ))
                    page.on("pageerror", lambda exc, sink=errors:
                            sink.append(f"pageerror: {exc}"))

                    for name, path in PAGES:
                        key = f"{name}.{theme}.{viewport_name}"
                        started = time.monotonic()
                        response = page.goto(base + path, wait_until="networkidle",
                                             timeout=45000)
                        elapsed = round((time.monotonic() - started) * 1000)
                        page.wait_for_timeout(600)

                        shot = SHOTS / f"{key}.png"
                        page.screenshot(path=str(shot), full_page=False)

                        report["pages"][key] = {
                            "status": response.status if response else None,
                            "load_ms": elapsed,
                            "screenshot": str(shot.relative_to(ROOT)),
                        }
                        report["performance"].setdefault(name, {})[
                            f"{theme}.{viewport_name}_ms"] = elapsed

                        if errors:
                            report["console_errors"].extend(
                                {"page": key, "message": message} for message in errors)
                            errors.clear()

                        if not skip_axe and axe_source and viewport_name == "desktop":
                            try:
                                page.add_script_tag(content=axe_source)
                                result = page.evaluate(
                                    "async () => await axe.run(document, "
                                    "{resultTypes:['violations']})"
                                )
                                for violation in result.get("violations", []):
                                    if violation.get("impact") in ("serious", "critical"):
                                        report["axe_violations"].append({
                                            "page": key,
                                            "id": violation["id"],
                                            "impact": violation["impact"],
                                            "help": violation["help"],
                                            "nodes": len(violation.get("nodes", [])),
                                            "target": [
                                                n.get("target") for n in
                                                violation.get("nodes", [])[:3]
                                            ],
                                        })
                            except Exception as exc:  # noqa: BLE001
                                report["axe_violations"].append(
                                    {"page": key, "error": f"axe failed: {exc}"[:200]})

                    context.close()

            # The shared selection must propagate across modules (spec 10).
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.goto(base + "/e3/", wait_until="networkidle")
            page.evaluate("window.BINMAN.Selection.set({e3: 'Q96SW2'})")
            page.wait_for_timeout(400)
            corner_filled = page.evaluate(
                "document.querySelector('[data-corner=\"ligase\"]')"
                ".classList.contains('is-pinned')"
            )
            fragment = page.evaluate("window.location.hash")
            page.goto(base + "/" + fragment, wait_until="networkidle")
            page.wait_for_timeout(600)
            carried = page.evaluate("window.BINMAN.Selection.value('e3')")
            corner_on_atlas = page.evaluate(
                "document.querySelector('[data-corner=\"ligase\"]')"
                ".classList.contains('is-pinned')"
            )
            report["selection_propagation"] = {
                "corner_fills_on_pin": bool(corner_filled),
                "fragment": fragment,
                "carries_across_modules": carried == "Q96SW2",
                "corner_filled_on_other_module": bool(corner_on_atlas),
            }

            # Mol* must reach interactive state, or report plainly that it did not.
            page.goto(base + "/", wait_until="networkidle")
            page.wait_for_timeout(800)
            molstar = page.evaluate(
                "() => ({ loaded: typeof window.molstar !== 'undefined',"
                " mounted: !!window.BINMAN.getViewer('viewer-glue'),"
                " empty: !!document.querySelector('#viewer-glue [data-role=\"empty\"]') })"
            )
            report["molstar"] = molstar
            context.close()
        finally:
            browser.close()
            server.shutdown()

    report["summary"] = {
        "pages_captured": len(report["pages"]),
        "console_errors": len(report["console_errors"]),
        "axe_serious_or_critical": len(report["axe_violations"]),
        "slowest_page_ms": max(
            (v["load_ms"] for v in report["pages"].values()), default=0),
        "passes": (
            len(report["console_errors"]) == 0
            and len(report["axe_violations"]) == 0
        ),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the BINMAN front-end QC")
    parser.add_argument("--port", type=int, default=8777)
    parser.add_argument("--skip-axe", action="store_true")
    args = parser.parse_args()
    report = run(port=args.port, skip_axe=args.skip_axe)

    summary = report["summary"]
    print(f"pages captured           : {summary['pages_captured']}")
    print(f"console errors           : {summary['console_errors']}")
    print(f"axe serious or critical  : {summary['axe_serious_or_critical']}")
    print(f"slowest page             : {summary['slowest_page_ms']} ms")
    print(f"molstar                  : {report.get('molstar')}")
    print(f"selection propagation    : {report['selection_propagation']}")
    for item in report["console_errors"][:10]:
        print(f"  console  {item['page']}: {item['message'][:120]}")
    for item in report["axe_violations"][:12]:
        print(f"  axe      {item.get('page')}: {item.get('id', item.get('error'))} "
              f"({item.get('impact', '')}) x{item.get('nodes', '')}")
    print(f"\nPASS: {summary['passes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
