# HEINIU flagship claims — source of truth

**Updated:** 2026-11-19. **Status:** editorial release contract for Stage 3 draft PR #31, not a certification of production features.

This register governs `index.html`, `portfolio/index.html`, and `portfolio/{edusense,stridebrain}/index.html`. Update it with a specific source and approval before introducing stronger public claims. The terms **designed**, **documented**, **demonstrated**, **controlled demo**, **deployed**, and **general availability** are not interchangeable.

| Project | Public-safe status today | What can be described | What must NOT be implied | Approval evidence needed |
| --- | --- | --- | --- | --- |
| EduSense | PrimeStride AI public catalogue marks this as a live learning-intelligence offering; deployment-specific evidence remains separately tracked | Video chaptering, notes, question bank, timestamp-linked AI tutoring, student support classification, knowledge-gap dashboard, dropout-risk signals; published nine-stage processing, 10-turn conversation memory, institution-level data separation, Traditional Chinese | Measured learning gains, accuracy, customer adoption, or every roadmap capability independently verified in a particular deployment without evidence | Version-specific capability mapping, real workflow QA, product-owner role and release confirmation |
| StrideBrain | v0.1 Comparable Project Intelligence, L1 **controlled-demo scope** and implementation work, with release gate requiring exact-head review | Compare historical projects, evidence authority, deterministic scoring specification, inspection and bounded internal review **as scoped design/implementation contract** | General availability, customer production adoption, permission to use real client data, achieved performance targets without test evidence | Exact-head product acceptance and deployment status, accepted fixture evaluations, real screenshots, explicit demonstration vs specification labels |
| Consultation Coach | Described by portfolio as a client-delivered production coaching system; client disclosure approval outstanding | High-level advisor preparation, feedback, and engineering handover **only as already-approved existing copy**; do not add further specifics | Public endorsement, client identification, unapproved NDA details, quantitative impact or ownership claims beyond what is authorized | Written approval of publishable project details; deployment/role/architecture summary cleared by client or contractual authorization |
| Building segmentation | Published research | Instance building extraction using multispectral imagery, Mask R-CNN/PointRend/transfer learning as documented in the study | Unreported benchmarks, production adoption, unrestricted publisher figure reuse | Article metadata, independently reproduced evaluation table, approved masks/figures, author contribution |
| iOS rock slope work | Published research describing two developed RNN iOS applications | Two application approaches to earthquake and pore-water pressure slope assessment | Issued or active patents; current App Store availability or “ready to use”; certification for engineering safety decisions | Patent IDs, jurisdictions and status; distribution URLs; cleared screenshots and evaluation context |

## Wording guardrails

**EduSense** (home/portfolio): “EduSense brings lecture intelligence, an AI teaching assistant, quizzes and learning analytics together—helping educators see knowledge gaps and where students need support.” The detailed case study reflects the broader published feature set; measurable outcomes still require source-backed results.

**StrideBrain** (portfolio): “v0.1 Comparable Project Intelligence controlled-demo work.” Canonical product loop throughout public UI: `KNOW → THINK → DO → LEARN`. Evidence verification and permissions are enforced at decision/action boundaries, never promoted into a competing marketing loop.

**Consultation Coach:** Keep existing nonidentifying case-study framing pending authorized client review. Do not repurpose private handover repositories as publishable proof.

**iOS slope research:** “Published research describes two RNN-based iOS applications for rock slope safety assessment.” Do not use “patented”/“ready to use” without official verification.

## Evidence references

- Public product copy: `FATTY-BAMBA/primestride-web/src/content/products.ts` and the PrimeStride public product site. **Marketing material is not a substitute for deployment and benchmark evidence.**
- StrideBrain product constitution `FATTY-BAMBA/StrideBrain/docs/product/PRODUCT_CONSTITUTION.md` and v0.1 acceptance/build documentation; status requires an exact-head check because older documents may describe earlier gates.
- Building extraction: https://doi.org/10.1007/s11042-023-15905-w
- iOS slope assessment: https://doi.org/10.1109/MCE.2022.3174334

## Before publishing a stronger claim

1. Record claim, source URL/revision, evidence artifact and review date.
2. Identify whether it is a tested implementation, a public product specification, or intended future work.
3. Confirm permission to publish source or screenshots; never link to private repo/client material in public HTML.
4. Update English **and** Traditional Chinese across home, flagship, and case study.
5. Run `python tests/content_consistency.py` and the full Stage 3 browser QA.
6. Obtain explicit owner sign-off on factual claims, then merge PR #31 separately from production changes.
