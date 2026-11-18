"""Compare the Stage 1 and Stage 2 public pages in real Chromium viewports."""
import argparse
import functools
import json
import shutil
import threading
from contextlib import ExitStack, contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


@contextmanager
def serve(root):
    handler = functools.partial(QuietHandler, directory=str(root))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()


METRICS = """() => {
  const root = document.documentElement;
  const elements = [...document.querySelectorAll('h1,h2,h3,main img')]
    .filter(e => e.getBoundingClientRect().width > 0);
  return {
    viewport: innerWidth, overflow: root.scrollWidth - root.clientWidth, lang: root.lang,
    missing: [...document.images].filter(i => i.complete && !i.naturalWidth).map(i => i.alt),
    geometry: elements.map(e => {
      const r = e.getBoundingClientRect();
      return [e.tagName, (e.innerText || e.alt).trim(), r.x, r.y + scrollY, r.width, r.height];
    })
  };
}"""


def capture(browser, origin, stage, route, lang, width, height, output):
    context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
    try:
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.on("console", lambda msg: errors.append(f"{msg.location.get('url', '')}: {msg.text}") if msg.type == "error" and
                msg.location.get("url", "").startswith(origin) else None)
        page.goto(f"{origin}/{route}?lang={lang}", wait_until="load")
        page.evaluate("document.fonts.ready")
        page.locator("h1:visible").wait_for()
        # Scroll the lazy-loaded project media into view before checking image dimensions.
        for img in page.locator("main img:visible").all():
            img.scroll_into_view_if_needed()
            img.evaluate("img => img.decode().catch(() => {})")
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        name = f"{stage}-{'portfolio' if route else 'home'}-{lang}-{width}"
        page.screenshot(path=output / f"{name}.jpg", type="jpeg", quality=78, animations="disabled")
        metrics = page.evaluate(METRICS)
        metrics["errors"] = errors
        if route:
            page.locator("#edusense").scroll_into_view_if_needed()
            page.screenshot(path=output / f"{name}-edusense.jpg", type="jpeg", quality=75)
        else:
            page.locator('nav a[href="#tools"]:visible').first.click()
            page.wait_for_function("location.hash === '#tools'")
        return metrics
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    with ExitStack() as stack, sync_playwright() as pw:
        origins = [stack.enter_context(serve(path)) for path in (args.baseline, args.candidate)]
        browser = pw.chromium.launch(executable_path=shutil.which("google-chrome") or shutil.which("chromium"))
        for width, height in [(1440, 900), (834, 1112), (390, 844), (320, 740)]:
            for route in ("", "portfolio/"):
                for lang in ("zh", "en"):
                    before, after = [capture(browser, origin, stage, route, lang, width, height, args.output)
                                     for stage, origin in zip(("stage1", "stage2"), origins)]
                    differences = []
                    if len(before["geometry"]) != len(after["geometry"]):
                        differences.append("Visible heading/image count changed")
                    for old, new in zip(before["geometry"], after["geometry"]):
                        if old[:2] != new[:2] or any(abs(a - b) > 2 for a, b in zip(old[2:], new[2:])):
                            differences.append({"before": old, "after": new})
                    passed = (after["viewport"] == width and after["overflow"] == 0 and
                              after["lang"] == ("en" if lang == "en" else "zh-Hant") and
                              not after["missing"] and not after["errors"] and not differences)
                    row = dict(width=width, height=height, route=route or "/", lang=lang, passed=passed,
                               overflow=after["overflow"], missing=after["missing"], errors=after["errors"],
                               compared_elements=len(after["geometry"]), geometry_changes=differences)
                    results.append(row)
                    print(json.dumps(row, ensure_ascii=False), flush=True)
                    (args.output / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
        browser.close()
    if not all(row["passed"] for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
