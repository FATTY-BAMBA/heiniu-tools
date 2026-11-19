# Stage 3 — Final release readiness and QA record

**Checked:** 2026-11-19 (Asia/Taipei)  
**Scope:** PR #31, `codex/stage3-portfolio-evidence` against `main`  
**Production status:** No Stage 3 merge or deployment promotion performed.

## Completed

- Stage 1 and Stage 2 are already on production `main`.
- Stage 3 adds bilingual deep dives for EduSense, StrideBrain and the published building extraction research; an About section, publication and attributable research contribution; a claim register; and consistent product-ready home/portfolio language.
- StrideBrain positioning is the operating-intelligence layer for project-based businesses with four connected capabilities and `KNOW → THINK → DO → LEARN`. Comparable Project Intelligence remains the controlled v0.1 slice, not the whole product. Continuous autonomous agents are not represented as a released v0.1 feature.
- EduSense is presented as the broader learning-intelligence offering described in PrimeStride's public catalogue; no invented numerical user or outcome metrics.
- HEINIU browser utilities are presented with ready-to-use calls to action.
- Authentic product screenshots are explicitly **deferred by owner** to a later release; the site retains accessible workflow and research diagrams without repetitive warnings.
- Canonical metadata and existing HEINIU hero social-preview image were added to the homepage and main portfolio.

## Automated verification

- `tests/content_consistency.py`: guards canonical StrideBrain loop and vision, v0.1 scope, EduSense's broader capabilities, private-repository references, unverified patent/availability claims, bilingual markup parity and research citations.
- `tests/stage3_routes_qa.py`: covers the homepage, portfolio and three case studies, each in English and Traditional Chinese at widths **1440, 834, 390 and 320** (5 × 2 × 4 = **40 route/locale/viewport combinations**).
- The browser suite checks loading, headings, skip links, broken images, JavaScript exceptions and horizontal overflow. On 1440px/390px runs it additionally exercises English/Chinese language control switching and captures responsive screenshots (20 images).
- Last observed green exact-head check before this record: GitHub Actions run [44460861750](https://github.com/FATTY-BAMBA/heiniu-tools/actions/runs/44460861750), commit `687f72748dee19d4717f191ae600306eeaf86535`; both jobs on that commit succeeded. 
- Existing Stage 2 tool feature tests were previously successful, but **not freshly repeated for every utility on this Stage 3 branch**. Source changes in Stage 3 center on portfolio and homepage content.
- Vercel's corresponding branch deployment must be READY on the exact final PR commit before promotion. Vercel build readiness is not an independent live domain smoke test.

## Manual review / owner gates

1. **Rendered visuals:** CI screenshots are attached as a GitHub Actions artifact, but a manual art-direction review of those rendered screenshots and actual devices is not yet independently recorded. The audit did not directly inspect their pixels.
2. **Consultation Coach client authorization:** Confirm the existing public production, personal-role, transfer and architectural detail claims are permitted for publication. Never publish customer data or NDA-restricted content.
3. **Exact product release scope:** Owner to sign off that the published EduSense feature set matches the current offered product and that StrideBrain's product vision vs v0.1 controlled demonstration is correctly expressed.
4. **Patent status:** iOS applications are described as published research without an unverified patent or current-distribution claim. Patent identifiers can be added later if approved.
5. **External links and devices:** Internal static navigation previously passed source audit and main CI. A full independent live check of every external URL, mobile physical device and public-domain deployment remains open.
6. **Release approval:** Mark PR #31 ready and merge only after owner explicitly confirms the release. Verify `fattybamba.com` and `/portfolio/` on the actual production deployment.

## Decision

**Automated checks: PASS.**  
**Content/visual/client-release approval: PENDING.**  
**Recommendation:** Keep PR #31 in draft until the human approval gates above are resolved. No need to wait for authentic screenshots.
