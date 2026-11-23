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
# StrideBrain is an operating-intelligence platform; historical comparison is one slice.
for page, body in [("homepage", home), ("portfolio", portfolio), ("case study", stride)]:
    check("operating intelligence" in body.lower() or "operating-intelligence" in body.lower(),
          f"StrideBrain {page} undersells platform-level positioning")
check(all("every project makes the company smarter" in page.lower()
          for page in (home, portfolio, stride)),
      "StrideBrain company-level compounding promise missing")
for phrase in ("Run the project happening now", "Make company knowledge usable",
               "Turn experience into better decisions", "Delegate recurring work to governed AI agents"):
    check(phrase in stride, f"StrideBrain platform case missing {phrase}")
check("continuous agents are part of the vision" in stride,
      "StrideBrain must distinguish future continuous-agent direction from v0.1 demo")
check("24/7 autonomous agents" not in (home + portfolio + stride).lower(),
      "Unproven autonomous-agent availability claim")
# Keep EduSense's publicly described educator-intelligence capabilities visible.
for phrase in ("Student classification", "Knowledge-gap dashboard", "Dropout-risk signals",
               "AI teaching assistant", "nine-stage processing pipeline"):
    check(phrase.lower() in edu.lower(), f"EduSense case study omits {phrase}")
check(("student support" in home.lower() or "students need support" in home.lower())
      and "learning analytics" in home.lower(),
      "EduSense homepage understates its learning-intelligence offering")
check("student support" in portfolio.lower() and "learning analytics" in portfolio.lower(),
      "EduSense flagship understates its learning-intelligence offering")
check("Ready to use." in home and "Use now" in home,
      "HEINIU browser tools do not have ready-to-use calls to action")
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

# The technology stack lists only tools the claim register can source, and every row
# must point at published research or at work that exists on the page.
stack_section = re.search(r'<section[^>]*id="stack".*?</section>', portfolio, flags=re.S)
check(stack_section is not None, "Portfolio technology stack section is missing")
stack = stack_section.group(0) if stack_section else ""
for doi in ("10.1007/s11042-023-17445-9", "10.1080/02533839.2020.1719899", "10.3390/app10062012"):
    check(doi in stack, f"Technology stack research row missing source {doi}")
for anchor in re.findall(r'href="#([^"]+)"', stack):
    check(f'id="{anchor}"' in portfolio, f"Technology stack links to missing section #{anchor}")
check(len(re.findall(r'<dd class="stack-where">\s*</dd>', stack)) == 0
      and stack.count('class="stack-where"') == stack.count("<dt>") > 0,
      "Technology stack row has no linked work")
check(re.search(r"Pinecone|\bAWS\b|Amazon Web Services|Gaussian process|support vector|LiDAR|Core ML|Swift",
                stack, flags=re.I) is None,
      "Technology stack lists a tool held back in docs/portfolio-claim-register.md")
check(re.search(r"\bexpert|\badvanced\b|years of experience|精通|專家", stack, flags=re.I) is None,
      "Technology stack asserts proficiency instead of documented use")
portfolio_zh = len(re.findall(r"<span data-lang-zh>", portfolio))
portfolio_en = len(re.findall(r'<span data-lang-en lang="en" hidden>', portfolio))
check(portfolio_zh == portfolio_en,
      f"portfolio/index.html: bilingual span mismatch ({portfolio_zh} zh / {portfolio_en} en)")

if failures:
    print("FAIL: public content consistency check")
    for issue in failures:
        print(" -", issue)
    raise SystemExit(1)

print("PASS: portfolio content consistency guardrails")
print("Checked", len(content), "public pages and all case studies.")
