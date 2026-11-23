# HEINIU flagship claims — source of truth

**Updated:** 2026-11-24 (technology stack section added; flagship entries last reviewed 2026-11-19). **Status:** editorial release contract for Stage 3 draft PR #31, not a certification of production features.

This register governs `index.html`, `portfolio/index.html`, and `portfolio/{edusense,stridebrain}/index.html`. Update it with a specific source and approval before introducing stronger public claims. The terms **designed**, **documented**, **demonstrated**, **controlled demo**, **deployed**, and **general availability** are not interchangeable.

| Project | Public-safe status today | What can be described | What must NOT be implied | Approval evidence needed |
| --- | --- | --- | --- | --- |
| EduSense | PrimeStride AI public catalogue marks this as a live learning-intelligence offering; deployment-specific evidence remains separately tracked | Video chaptering, notes, question bank, timestamp-linked AI tutoring, student support classification, knowledge-gap dashboard, dropout-risk signals; published nine-stage processing, 10-turn conversation memory, institution-level data separation, Traditional Chinese | Measured learning gains, accuracy, customer adoption, or every roadmap capability independently verified in a particular deployment without evidence | Version-specific capability mapping, real workflow QA, product-owner role and release confirmation |
| StrideBrain | **AI operating-intelligence layer** for project-based businesses; the v0.1 Comparable Project Intelligence work is its first L1 controlled-demo slice | Company-wide vision: live-project context, connected organizational knowledge, decision intelligence using historical evidence, and governed AI agents; v0.1 emphasis: explainable comparable projects, evidence review and bounded internal actions | That 24/7/continuous autonomous agents, all planned workflows, or general customer availability are already released or validated in v0.1 | Exact-head acceptance/deployment proof for v0.1; subsequent independently tested agent/action release gates; approved product demos and roles |
| Consultation Coach | Described by portfolio as a client-delivered production coaching system; client disclosure approval outstanding | High-level advisor preparation, feedback, and engineering handover **only as already-approved existing copy**; do not add further specifics | Public endorsement, client identification, unapproved NDA details, quantitative impact or ownership claims beyond what is authorized | Written approval of publishable project details; deployment/role/architecture summary cleared by client or contractual authorization |
| Building segmentation | Published research | Instance building extraction using multispectral imagery, Mask R-CNN/PointRend/transfer learning as documented in the study | Unreported benchmarks, production adoption, unrestricted publisher figure reuse | Article metadata, independently reproduced evaluation table, approved masks/figures, author contribution |
| iOS rock slope work | Published research describing two developed RNN iOS applications | Two application approaches to earthquake and pore-water pressure slope assessment | Issued or active patents; current App Store availability or “ready to use”; certification for engineering safety decisions | Patent IDs, jurisdictions and status; distribution URLs; cleared screenshots and evaluation context |

## Wording guardrails

**EduSense** (home/portfolio): “EduSense brings lecture intelligence, an AI teaching assistant, quizzes and learning analytics together—helping educators see knowledge gaps and where students need support.” The detailed case study reflects the broader published feature set; measurable outcomes still require source-backed results.

**StrideBrain** (home/portfolio): “An AI operating-intelligence layer for project-based businesses that connects live project context, company knowledge, accumulated experience and governed AI workflows. Every project makes the company smarter.” Canonical loop: `KNOW → THINK → DO → LEARN`. **Current v0.1 controlled demo** specifically covers Comparable Project Intelligence and human-reviewed actions. Specialized and continuously operating agents belong to the longer-term product vision—not a claim of current autonomous operation.

**Consultation Coach:** Keep existing nonidentifying case-study framing pending authorized client review. Do not repurpose private handover repositories as publishable proof.

**iOS slope research:** “Published research describes two RNN-based iOS applications for rock slope safety assessment.” Do not use “patented”/“ready to use” without official verification.

## Technology stack section

**Added:** 2026-11-24. **Scope:** `portfolio/index.html#stack`. **Status:** draft pull request; owner sign-off pending.

The section says what the listed work was **built with**. A tool or method appears only when a published paper, a public repository or already-approved portfolio copy documents its use, and every row links to the work it belongs to. It does not assert proficiency, scale, or the configuration of any current client deployment.

| Row | Listed | Source and revision |
| --- | --- | --- |
| Machine learning & optimization | XGBoost, genetic algorithms | https://doi.org/10.1007/s11042-023-17445-9 (genetic-algorithm-tuned XGBoost, 2024 volume) |
| | Extreme learning machine | https://doi.org/10.1080/02533839.2020.1719899. DOI taken from the reference list of the 2024 XGBoost paper; open it once before merge |
| | Particle swarm optimization, genetic algorithms | https://doi.org/10.3390/app10062012 and https://doi.org/10.1007/978-3-319-97115-5_125 |
| Deep learning & computer vision | Mask R-CNN, PointRend, transfer learning | https://doi.org/10.1007/s11042-023-15905-w |
| | Recurrent neural networks | https://doi.org/10.1109/MCE.2022.3174334 |
| Speech recognition & OCR | faster-whisper, PaddleOCR, EasyOCR, PyTorch, OpenCV, FFmpeg | Public repository `FATTY-BAMBA/Class_Genuis` at `1b60adc` (2026-02-24): `requirements.txt`, `Dockerfile`, `app/video_processing.py`. This is the lecture pipeline under EduSense's earlier name |
| LLM applications | OpenAI API | `Class_Genuis` at `1b60adc`: `requirements.txt` |
| | Gemini API | Public repository `FATTY-BAMBA/StrideBrain` at `1fe84af` (2026-11-23); Consultation Coach approved copy |
| | Vector retrieval | Consultation Coach approved copy (separate vector indexes per department) |
| Backend & data | Python, Flask, Celery, Redis | `Class_Genuis` at `1b60adc`: `requirements.txt`, `docker-compose.yml` |
| | FastAPI | Consultation Coach approved copy |
| | PostgreSQL, Prisma | `StrideBrain` at `1fe84af`: `package.json`, `prisma/` |
| | Supabase | `StrideBrain` at `1fe84af`: `docs/development/TEST_SITE.md`; public repository `FATTY-BAMBA/primestride-kms` at `96ce9ee` (2026-06-06): `package.json` |
| Frontend | Next.js, React, TypeScript | `StrideBrain` at `1fe84af`: `package.json` |
| | Tailwind CSS, Vite | `primestride-kms` at `96ce9ee` and public repository `FATTY-BAMBA/geofield-site` at `c0b2a33` (2026-08-20): `package.json` |
| Infrastructure & deployment | Docker, NVIDIA CUDA, RunPod GPU, Linux | `Class_Genuis` at `1b60adc`: `Dockerfile`, `app/runpod_client.py` |
| | Google Cloud | Consultation Coach approved copy |
| | Vercel, GitHub Actions | This repository (`vercel.json`, `.github/workflows/`); `StrideBrain` at `1fe84af` |
| Testing & AI tooling | Playwright | This repository: `tests/` |
| | Vitest | `StrideBrain` at `1fe84af`: `package.json` |
| | Claude skills & plugins, Claude Code | This repository: `plugins/heiniu-video-editor`, `/edit/` |
| | Codex | This repository: Stage 3 development branch `codex/stage3-portfolio-evidence` |

**Held back until a public source or written owner approval exists:** Pinecone and AWS (documented only in private repositories); Gaussian process regression (manuscript not yet published); support vector regression (paper metadata not verified); LiDAR point-cloud work (employer project); the iOS toolchain behind the slope applications; any client name.

**Wording guardrails:** Keep the heading and intro to "built with" and "used in". Do not add proficiency words such as expert or advanced, years of experience, or data volumes. Consultation Coach contributes only the tools already named in its approved copy. Link rows to on-page work or DOIs, never to a private repository. A repository revision records what was true at that commit; re-check it when the product changes.

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
