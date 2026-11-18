# HEINIU website — consistency, source and release audit

**Audit date:** 2026-11-18 (Asia/Taipei)  
**Compared:** production `main` at `329bc8f`; Stage 3 draft branch `codex/stage3-portfolio-evidence` (PR #31).  
**Scope:** The 16 HTML website routes in `heiniu-tools`, their statically referenced internal assets/fragment anchors, product/academic claims, source visibility, bilingual copy conventions, and Stage 3 content. Also consulted available original project documentation and third-party sources where noted. This is a **source audit**, not a substitute for browser/device QA, automated security scanning, or legal sign-off.

## Baseline results

- 16 website `index.html` route files enumerated from the exact Stage 3 Git tree.
- 272 local `href`/`src`/`poster` references checked against that Git tree and intra-site fragment targets; **no missing local files/fragment targets found** in this static pass. Dynamic URLs and external embeds are not covered by this count.
- 39 distinct external HTTP(S) URL targets identified; not all were live-tested.
- Bilingual `data-lang-zh` and `data-lang-en` element-count parity confirmed in primary portfolio (83/83) and both deep dives (EduSense 48/48; StrideBrain 44/44). Count parity alone does not prove translation accuracy or browser rendering.
- Prior Stage 2 suite passed on production-release commit before Stage 3. Stage 3 pages do **not** yet have complete browser/visual E2E acceptance.

## Confirmed fixes made on Stage 3 draft branch — not yet production

| Issue | Resolution |
| --- | --- |
| Conflicting StrideBrain loops in flagship and case study | Standardized public flagship copy and four-node conceptual diagram to the **product constitution's `KNOW → THINK → DO → LEARN`**. Removed the public-facing explanation comparing the two competing diagrams. Kept evidence verification and approval as engineering principles before consequential actions. |
| Public EduSense link to a **private** repository (a non-public AI Tutor repository) | Removed link and private-repository exposition from the public EduSense page. Replaced with a clear request for approved deployment/implementation evidence. Public PrimeStride overview remains as the public product-description source. |

These issues were found by comparing the Stage 3 draft against the accessible source-repository visibility and StrideBrain's `docs/product/PRODUCT_CONSTITUTION.md`. The StrideBrain repository itself is public; related private repositories and other client handover repositories are private. Private client materials are not approved public references.

## Remaining substantive issues

| Priority | Surface | Issue / evidence | Required resolution |
| --- | --- | --- | --- |
| **P1 / Release gate** | Stage 3 EduSense and StrideBrain | No actual product screenshots, independently reviewed metrics, precise personal-contribution breakdown, or rendered bilingual/mobile acceptance yet. Case studies currently rely on conceptual illustrations and source-level claims. | Get approved, anonymized product media and documented proof, then browser QA at 1440/834/390/320px; do not merge PR #31 before sign-off. |
| **P1 / Claim verification** | Homepage and portfolio's slope iOS work | Text calls the two iOS applications **patented** and **ready to use**. The 2024 IEEE paper substantiates that two apps were developed (earthquake vs pore-water-pressure), but the sources checked here do not establish the patent numbers, jurisdictions, legal status or present availability. | Confirm official patent numbers/status and app distribution; otherwise say **published research describing two developed iOS applications** without patent/availability claims. |
| **P1 / Claim verification** | Portfolio Consultation Coach | `IN PRODUCTION`, independent authorship, client-specific architecture, migration and verified callbacks are asserted on public site; private client-related source material has NDA boundaries. | Approve public-safe description and permission-cleared evidence; redact client identity/data and avoid disclosing any additional private source details. |
| **P1 / Status consistency** | Homepage + portfolio EduSense vs Stage 3 EduSense case study | Homepage/portfolio assert **working learning tool** with chaptering, quizzes and grounded Q&A; company product page labels EduSense **live**, plus broader analytics. Stage 3 case study says exact release scope and effectiveness are **under source review**. These aren't inherently false, but public wording is not aligned to a single versioned evidence record. | Establish one product-status matrix: implemented, demonstrated, released, planned; specify documented features, screenshot/test evidence and versions. Then harmonize wording on homepage, flagship and deep dive. |
| **P2 / Status consistency** | StrideBrain | Main portfolio describes v0.1 **built to production standards**; constitution and product decisions target an **L1 controlled demo**, with explicit release gates. Current public claims should be tied to exact approved head/deployment and acceptance evidence. | Confirm current L1 release-gate result, actual working slice, tested outputs and version; keep synthetic demo and non-GA boundaries explicit. |
| **P2 / Editorial** | Stage 3 case studies | Pages spend significant space explaining what is **not independently verified**. Appropriate during review, but too many disclaimers can weaken the professional story. | After obtaining approved evidence, replace meta-commentary with concise **Scope / Evidence / Limitations** sections, demonstrated outcomes, authentic screenshots and personal decisions. |
| **P2 / Accuracy maintenance** | Chinese Claude 11-chapter tutorial, salary tool | Chinese guide includes dated, detailed 2026 plan/model/feature and price claims; salary tool uses explicit **2026** labor/insurance rates and approximation rules. Dynamic facts need recurrent review. English course intentionally has more generic plan wording, so the two editions differ in specificity. | Verify against current official vendor and Taiwan government documentation; add last-verified dates / maintenance tests; avoid unsupported futureproof wording. |
| **P2 / Privacy and attribution** | Portfolio media and client projects | Real product screenshots and research figures may contain identifiable students/clients or publisher-controlled illustrations; public reuse rights are not currently documented. | Use cleared/anonymized screenshots, own recreations from evidence where appropriate, and documented publication figure permissions. |
| **P2 / SEO** | Site-wide | Main home/portfolio lack a consistent canonical / social preview image strategy; new deep dives have canonical tags but no Open Graph image. | Establish a cross-page metadata policy and create approved social sharing visuals; test link previews. |
| **P3 / Content depth** | Computer vision and iOS research | Published work is linked but still lacks original examples, your contributions, ablations, evaluation values and limitations. | Build a dedicated research case study using verified paper details and rights-cleared model outputs. |

## Source references / evidence locations

- GitHub website: `FATTY-BAMBA/heiniu-tools`, `main` and Stage 3 PR #31.
- StrideBrain public product constitution: `FATTY-BAMBA/StrideBrain/docs/product/PRODUCT_CONSTITUTION.md`; also its v0.1 decision pack and acceptance/architecture documents. Source-defined loop: `KNOW → THINK → DO → LEARN`.
- PrimeStride public EduSense product listing: `https://www.primestrideai.com/zh/products` (marketing descriptions are not independent metrics).
- Published building segmentation: `https://doi.org/10.1007/s11042-023-15905-w` (2024 volume).
- Published iOS slope study: `https://doi.org/10.1109/MCE.2022.3174334` (2024 volume).
- Original portfolio and bibliography: `FATTY-BAMBA/fatty-bamba.io`.
- Source-only cross-reference: private repositories are accessible to project owner but **must not be linked as public documentation** or be quoted without publication approval.
- Claude official pricing: `https://claude.com/pricing`.

## Recommended finish order

1. **Close confirmed content inconsistencies** in PR #31 (loop and private reference fixed on branch); add product-owner approval for patent, Consultation Coach, EduSense status and StrideBrain release boundaries.
2. **Evidence-gathering**: screenshots, synthetic-safe demos, individual role, architecture, benchmark/test evidence, and consent/rights.
3. **One editorial pass** across homepage, portfolio flagship, and deep dives so product status/terms and EN/ZH narratives agree exactly.
4. **Complete research case studies** with verifiable citations and authorized imagery.
5. **Full browser/functional/visual QA** of 16 routes, emphasizing new deep dives; keyboard/screen-reader, bilingual navigation, 320/390/834/1440px, external links, real-device smoke tests.
6. **Metadata/social and final publication review**; confirm no private-source references and no unsupported numbers.
7. Only then approve PR #31, merge to `main`, verify Vercel production and smoke-test live public routes.

## Limits and outstanding validation

- Static link checks do not prove public external links still work or that a page responds in a protected browser session.
- External links have been inventoried; some checked individually, but **not all 39** fully verified.
- Equal EN/ZH span counts do not certify translations; browser visual and native-language review are still needed.
- A green Vercel build proves compilation/deployment, not page behavior or factual correctness.
- This audit cannot certify patent ownership, a client's publication consent, or production status without primary documents.
