"""Stage 3 Chromium smoke/visual evidence for bilingual case studies.

Run: python tests/stage3_routes_qa.py . evidence/stage3
CI collects 12 screenshots and a structured JSON report.
"""
import argparse
import functools
import json
import shutil
import threading
from contextlib import contextmanager
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


ROUTES = {
    "edusense": "portfolio/edusense/",
    "stridebrain": "portfolio/stridebrain/",
    "building": "portfolio/building-extraction/",
}
VIEWPORTS = [(1440, 900), (834, 1112), (390, 844), (320, 740)]


def inspect(page):
    return page.evaluate("""() => {
        const d = document.documentElement;
        const main = document.querySelector('main');
        const heading = document.querySelector('main h1');
        const visibleImages = [...document.querySelectorAll('main img')]
          .filter(i => i.getBoundingClientRect().width > 0);
        return {
            lang: d.lang,
            overflow: d.scrollWidth - d.clientWidth,
            hasMain: !!main, visibleHeading: !!heading && heading.getBoundingClientRect().width > 0,
            brokenImages: visibleImages.filter(i => i.complete && i.naturalWidth === 0).map(i => i.src),
            skipTarget: document.querySelector('a.skip')?.getAttribute('href') === '#main',
            hasCanonical: !!document.querySelector('link[rel="canonical"]'),
            languageButtons: [...document.querySelectorAll('.shell-languages [data-lang-choice]')]
                .map(b => ({lang:b.dataset.langChoice,pressed:b.getAttribute('aria-pressed')}))
        };
    }""")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("out", type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results = []
    with serve(args.root) as origin, sync_playwright() as playwright:
        executable = shutil.which("google-chrome") or shutil.which("chromium")
        browser = playwright.chromium.launch(executable_path=executable)
        for label, route in ROUTES.items():
            for width, height in VIEWPORTS:
                for lang in ("en", "zh"):
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        reduced_motion="reduce",
                    )
                    try:
                        page = context.new_page()
                        exceptions = []
                        page.on("pageerror", lambda err: exceptions.append(str(err)))
                        response = page.goto(f"{origin}/{route}?lang={lang}", wait_until="load")
                        page.locator("main h1").wait_for()
                        m = inspect(page)
                        expected = "en" if lang == "en" else "zh-Hant"
                        passed = (
                            response.status == 200 and m["lang"] == expected
                            and m["overflow"] == 0 and m["hasMain"] and m["visibleHeading"]
                            and m["skipTarget"] and m["hasCanonical"]
                            and not m["brokenImages"] and not exceptions
                        )
                        if width in (1440, 390):
                            page.screenshot(
                                path=args.out / f"{label}-{lang}-{width}.png",
                                animations="disabled",
                            )
                        results.append({
                            "route": route, "lang": lang, "width": width,
                            "passed": passed, "status": response.status,
                            "details": m, "pageErrors": exceptions,
                        })
                        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
                    finally:
                        context.close()
        browser.close()
    (args.out / "stage3-results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if not all(row["passed"] for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
