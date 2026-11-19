# Stage 3 — Portfolio evidence register and editorial release gate

Status: **Working draft. Not a claim-verification certificate.**
Scope: Abdoulie Fatty's public portfolio at `/portfolio/`.
Source hierarchy: published papers and attributable work; project source/technical documentation; public company product pages; existing portfolio claims. Marketing copy alone is not independent performance evidence.

## Current Stage 3 changes

- Added a short English/Traditional Chinese professional narrative that connects geotechnical engineering, AI research, PrimeStride AI, and HEINIU. This is deliberately high-level and preserves the existing visual identity.
- Restored one scholarly proceedings entry missing from the current portfolio: *Back Analysis Algorithm Based on Particle Swarm Optimization* (Abdoulie Fatty, A. J. Li), China–Europe Conference on Geotechnical Engineering, Springer proceedings, 2018, https://doi.org/10.1007/978-3-319-97115-5_125.
- Added existing public profile links (GitHub, ResearchGate, ORCID).

## EduSense deep-dive status (Stage 3, first full case-study pass)

A bilingual, dedicated, editorial case-study route now exists at `/portfolio/edusense/`. The original portfolio links to it.

**Included and grounded:** learner problem, four product-experience entry points (chaptering, notes, practice questions, source-aware answers), conservative engineering considerations, and a comparison of source types. The four-step visual is an explanatory model, not an application trace. Source links use the public PrimeStride product listing and a separately documented AI Tutor API README.

**Not yet asserted:** that the AI Tutor API implements EduSense as a whole; the full marketed nine-stage implementation as independently verified; learner analytics, dropout prediction, quantified performance, institutional adoption, proprietary data isolation, or detailed personal contribution. The public marketing site describes some of these, but independent product-run evidence is required.

**Pending design/evidence approval:** actual interface screenshots with permission, confirmed architectural diagram, scoped production release status, verified role and contribution, measurable test results, and bilingual visual/accessibility browser QA. No client data, NDA handover content, or unverified figures were copied.

## StrideBrain deep-dive status (Stage 3, second case-study pass)

A dedicated bilingual case study exists at `/portfolio/stridebrain/`, linked from the main StrideBrain flagship.

**Source-grounded:** public product constitution, v0.1 decision pack, technical architecture, and implementation-candidate documentation. Focus is Comparable Project Intelligence for Taiwan design/renovation teams: structured historical comparison, evidence authority, optional explanation, bounded internal review, and a controlled-demo boundary.

**Reconciled in Stage 3 draft:** portfolio flagship, conceptual diagram and deep-dive now use the product constitution's `KNOW → THINK → DO → LEARN` loop. Evidence verification and permission/human-approval checks remain engineering requirements at the Think-to-Do boundary. This change is not yet on production until PR #31 merges.

**Not asserted:** production general availability, real-customer deployment, tested performance figures or validated customer outcomes. The v0.1 documents describe L1 controlled-demo release gating, and some implementation pages carry candidate status. Successful implementation or passing tests do not by themselves grant production release.

**Still needed:** authorized real screenshots from the exact accepted build; release-gate and deployment evidence; personal contribution and team role; approved architecture diagram; current validated evaluation results; bilingual visual and accessibility QA.

## Published-research deep dive (2026-11-19)

- Added `/portfolio/building-extraction/` in English and Traditional Chinese, linked from the existing computer-vision flagship. The page follows the publisher's accessible 2023 online / 2024 volume record, names all three authors, and describes Mask R-CNN, PointRend, transfer learning and augmentation only at the level supported by the abstract. It explicitly marks the footprint diagram conceptual and **does not reproduce Springer figures** or invent precision/recall values.
- Added a documented personal role to the main portfolio research section: the **2020 open-access Applied Sciences paper's author-contribution statement** credits A. Fatty with all numerical analysis and shared discussion/drafting. See https://doi.org/10.3390/app10062012.
- Original building segmentation source: https://doi.org/10.1007/s11042-023-15905-w — article online 17 June 2023; journal volume 83 (2024), pages 61913–61928. Springer lists Abdoulie Fatty as corresponding author.
- Stage 3 CI now includes `tests/stage3_routes_qa.py` to exercise EduSense, StrideBrain and building extraction at 1440/834/390/320 px in English and Chinese (24 browser combinations), capture image evidence at 1440 and 390 px, check overflow, broken images, JavaScript exceptions, canonical tags and heading/skip targets. This does not substitute for editorial approval or a manual screenshot review.

**Still needed:** full original paper's method/metrics if quantitative extraction claims are desired; rights-cleared input/mask comparison visuals; confirmed detailed individual role in the 2024 study; human review of bilingual screenshots; client-approved evidence and deployment claims for other projects.

## Evidence and next assets

| Area | Current public presentation | Source to consult | Evidence/approval still required |
| --- | --- | --- | --- |
| Professional background | Engineer, PhD researcher, founder | Earlier portfolio `FATTY-BAMBA/fatty-bamba.io/index.html`, current portfolio and public company site | Confirm degree wording, preferred personal-brand identity, current title, biography and whether to publish a CV |
| EduSense | Lecture-to-chapters, notes, quizzes and source-grounded answers | `FATTY-BAMBA/primestride-web/src/content/products.ts`; related project implementation and public demo | Original application screenshots, actual feature coverage, user's contribution, approved customer reference, demo availability; do not conflate broader marketed roadmap (analytics, dropout risk) with verified deployed scope |
| StrideBrain | Knowledge/evidence/review workflow; v0.1 vertical slice | `FATTY-BAMBA/StrideBrain/README.md` and current versioned product/quality docs | Current release gate and demo status; workflow language standardized in Stage 3 draft; approved system screenshots, tests, architecture and release evidence still required. README may lag ongoing implementation |
| Consultation Coach | AI advisor preparation and coaching, presented as in production | Existing portfolio and system repos, subject to any client confidentiality agreement | Get written approval for customer identity, architecture, implementation, handover and metrics before publishing more. Do not reproduce NDA-marked source materials or client records |
| Building instance segmentation | Mask R-CNN + PointRend and transfer learning | https://doi.org/10.1007/s11042-023-15905-w | Actual aerial input, masks, evaluation values, data rights, and a clear statement of specific author contribution; no fabricated performance numbers |
| iOS slope applications | RNN-based assessment, published research | https://doi.org/10.1109/MCE.2022.3174334 | Approved app screenshots, documented evaluation metrics and scope of patent claims |
| Rock slope back analysis | 2020 paper + 2018 proceeding | https://doi.org/10.3390/app10062012 ; https://doi.org/10.1007/978-3-319-97115-5_125 | Figures with reproduction permission or new original diagrams |

## Claim discipline

- Distinguish **published result**, **demonstrated prototype**, **pilot**, **production deployment**, and **planned feature** explicitly.
- Never infer accuracy, adoption, latency, cost savings, or security outcomes from marketing claims alone.
- Any percentages or test counts need attributable report/commit/date/context before publication.
- Use anonymized screenshots for client systems; scrub names, internal documents, confidential architecture, customer data and access tokens.
- Do not describe conceptual portfolio diagrams as working software screenshots.
- Verify researcher publication metadata and direct contributions before adding quantitative claims.
- Do not expose non-public connected repository URLs or implementation specifics on the public website unless expressly approved.

## Next reviewable increments

1. Obtain approved real screenshots/media for EduSense, StrideBrain and research outputs.
2. Confirm exact deployed scope of each flagship project and distinguish it from marketing roadmap.
3. Build one substantial case-study page with Problem → Role → Architecture → Decisions → Validation → Results → Limitations, using only verified evidence.
4. Expand the publication list and downloadable CV only after checking authenticity, public rights and completeness.
5. Perform bilingual factual review, visual screenshot QA and accessibility review before merging Stage 3.

## Release safety

- Development branch: `codex/stage3-portfolio-evidence`
- Base: currently deployed `main`
- Stage 3 PR remains draft; no production merge or rollout without approval.
