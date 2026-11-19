#!/usr/bin/env python3
"""Release guard for public HEINIU portfolio claims.

Static consistency checks intentionally fail when a risky wording pattern is
reintroduced. This is NOT a fact-checker or a replacement for human review.
Run from repo root: python tests/content_consistency.py
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
PAGES = [
    "index.html",
    "portfolio/index.html",
    "portfolio/edusense/index.html",
    "portfolio/stridebrain/index.html",
    "portfolio/building-extraction/index.html",
]
content = {path: (ROOT / path).read_text(encoding="utf-8") for path in PAGES}
failures = []


def check(condition, issue):
    if not condition:
        failures.append(issue)


home = content["index.html"]
portfolio = content["portfolio/index.html"]
edu = content["portfolio/edusense/index.html"]
stride = content["portfolio/stridebrain/index.html"]
building = content["portfolio/building-extraction/index.html"]

# The canonical product loop must be uniform, including the visual's node labels.
check("KNOW</span><b>→</b><span>THINK</span><b>→</b><span>DO</span><b>→</b><span>LEARN" in portfolio,
      "Flagship StrideBrain loop differs from product constitution")
check("<small>03 / DO</small>" in portfolio and "<small>04 / LEARN</small>" in portfolio,
      "Flagship conceptual nodes do not match canonical loop")
check("KNOW → THINK → VERIFY → DO" not in portfolio + stride,
      "Superseded workflow is shown on a public portfolio page")
check("An earlier portfolio graphic uses" not in stride,
      "Internal workflow reconciliation is exposed publicly")

# These phrases require primary patent/distribution or release evidence.
for name, text in content.items():
    for regex, reason in [
        (r"patented iOS applications|two patented|取得專利|已取得專利", "unverified patents"),
        (r"complete and ready to use|可供使用的 iOS", "unverified app distribution"),
        (r"Working learning tool|working learning tool|可實際使用的學習工具", "unversioned EduSense live claim"),
    ]:
        check(re.search(regex, text, flags=re.I) is None,
              f"{name}: {reason}")

# No visitor should be sent to a private source or shown internal owner-only repo identity.
for name, text in content.items():
    check("LC-ai-tutor-api" not in text and "classgenius-handover-lccnet" not in text,
          f"{name}: private repository reference")
check("controlled-demo" in portfolio and "controlled-demo" in stride,
      "StrideBrain release boundary is missing from flagship or deep dive")
check("site-content-consistency-audit" not in edu,
      "Internal editorial audit leaked into public-facing EduSense story")

# Bilingual markup in new case studies should be structurally paired.
for name in ("portfolio/edusense/index.html", "portfolio/stridebrain/index.html", "portfolio/building-extraction/index.html"):
    text = content[name]
    zh = len(re.findall(r"<span data-lang-zh>", text))
    en = len(re.findall(r'<span data-lang-en lang="en" hidden>', text))
    check(zh == en and zh > 30, f"{name}: bilingual span mismatch ({zh} zh / {en} en)")
    check('href="#main"' in text and 'id="main"' in text,
          f"{name}: missing skip-link target")
    check("workflow" in text.lower() or "schematic" in text.lower() or "diagram" in text.lower(),
          f"{name}: diagram lacks a recognizable description")

# The research case must cite the correct paper and never borrow metrics or imagery.
check("10.1007/s11042-023-15905-w" in building,
      "Building extraction case missing original paper DOI")
check("2024 journal volume" in building and "17 June 2023" in building,
      "Building publication chronology is not clearly distinguished")
check("instance segmentation schematic" in building.lower()
      and 'role="img"' in building,
      "Building illustration must remain identified as a schematic and accessible as an image")
check('href="./building-extraction/"' in portfolio,
      "Main portfolio does not link to the research deep dive")

if failures:
    print("FAIL: public content consistency check")
    for issue in failures:
        print(" -", issue)
    raise SystemExit(1)

print("PASS: portfolio content consistency guardrails")
print("Checked", len(content), "public pages and all case studies.")
