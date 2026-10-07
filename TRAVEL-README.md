# 主揪救星 — review prototype

Route: `/travel/`. Evergreen Taiwan group-trip planner, with an explicitly labelled 2026-10-10–11 Kaohsiung editorial example.

## What works without credentials

Trip constraints, 1–8 friends, wishes/dislikes, budget and date validation, sample itinerary, per-person matches and compromises, unknown-cost display, Maps search links, copy/native share, text download and print/PDF. No persistent storage or analytics were added. Editing conditions clears stale results. A missing AI service returns an honest error, never a canned itinerary disguised as generated output.

The example is not a verified holiday booking: all event/date-specific schedules, accommodation, seat availability and actual prices require fresh checks. NT$6,500 is a target. NT$4,730 is the previous planning reference excluding accommodation, leaving a NT$1,770/person accommodation ceiling; a ceiling is not a hotel quote. The Oct24–25 fried-chicken festival is deliberately excluded.

## Server connection

`api/travel.js` uses AI SDK 7 structured output and Gateway Perplexity search. Blank destination returns three candidates; selecting one requests a complete plan. JSON inputs, dates, adult counts, itinerary chronology, earliest departure and six budget categories are checked. Source links are filtered against URLs returned by this request's search tool. This establishes source provenance, not claim-level verification. Model errors preserve the form and do not expose provider response contents.

Vercel target: existing `heiniu-tools` project (`prj_CBquE1lvGvsYuSQw9qR5cYIzIS7y`), team `prime-stride-ai` (`team_lsOlaUCkesHjAqz22LGxtFMe`). Keep this on a review branch / protected Preview until verified.

The connected Vercel API denied team-scoped settings access with HTTP 403. No credentials, spend limits, team access or production deployment were changed. There is no local Vercel CLI credential or Gateway key. Live inference is therefore not yet verified.

Configure in Vercel Preview (never in browser code):

- `AI_GATEWAY_MODEL`: `openai/gpt-6-luna`, present in the live Gateway catalog checked 2026-10-07; override to another supported text/tool/structured-output model if desired.
- Vercel OIDC authentication is used automatically, or configure `AI_GATEWAY_API_KEY` securely for local development.
- `TRAVEL_AI_ENABLED=true` only after Gateway access and a project spend budget are configured.

Before enabling publicly: set a project Gateway budget and platform rate limit / bot controls; the endpoint currently has request-size and generation limits, **not a durable per-user quota**. Run a protected live test for both destination comparison and itinerary generation and check actual date-specific citations. Review cancellation and timeout costs (client cancellation does not guarantee provider cancellation). Once approved, update the homepage's “AI 規劃功能準備中” text.

Homepage privacy language was corrected: new AI generation sends trip preferences/nicknames to Gateway and search providers; the existing local tools remain local.

## Local work

Node24: `npm ci`, `npm test`, `npm run check`, `npm run dev`; open `http://localhost:4173/travel/`.

Dependencies are locked. TypeScript6 is used for a portable JavaScript type checker: the native TypeScript7 binary cannot execute in this restricted workspace. This does not downgrade the AI SDK.

## Video proof after live AI verification

1. Four friends' wishes, one must-have and one dislike each.
2. The actual returned itinerary, with a distinct experience for each friend.
3. Actual budget uncertainty and any real compromise.
4. Copy a compact summary into a blank draft (do not send to anyone during testing).

Only call the website a working AI planner in published content after the live endpoint has passed. Keep the editorial sample label visible in any prototype footage.
