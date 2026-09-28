# ctamulticolor-site — Campaign site for Lista 6 Multicolor, CTA La Matanza

- **Repo / branch:** `/home/manjarodesktop/2025/po/cta` (worktree), branch `CTA`
- **Site folder:** `site/` (Astro project), Firebase config at worktree root
- **Domain:** `ctamulticolor.com.ar` (DNS managed in Cloudflare)
- **Engram mirror:** `odd/ctamulticolor-site/tasks`

## Objective

Mobile-first campaign site for **Lista 6 Multicolor** in the **CTA La Matanza** election,
built on the proven stack of the SUTEBA sites (Gesell, `web_multi`) but only with
sections the real material justifies — inspired by, not copied from, Gesell.

## Problem / why

After winning SUTEBA La Matanza in May, the list runs for the local CTA. The political
axis (from the official ballot): *"En mayo recuperamos el SUTEBA, ahora recuperemos la
CTA"* and *"Por una central independiente que enfrente la motosierra de Milei y el
ajuste de Kicillof"*. Supporters need, from their phones: who the candidates are
(and find themselves among 80 congresales), when/how to vote, and how to join.

## Sources (read before building)

- `../eleccionesSUTEBA2026/cta/lista_oficial.jpeg` — official ballot, **source of truth**
  for all 106 candidacies: 11 secretarías, 9 vocales, 6 Comisión Revisora, 60
  congresales provinciales titulares, 20 suplentes.
- `../eleccionesSUTEBA2026/cta/La Matanza (2).xlsx` — CTA 2026 padrón upload sheet
  (PII, gitignored). **Not used by the site.** Aggregates only, kept internal.
- `../../web_multi/site/` — Multi SUTEBA Matanza site: 90 candidate photos
  (`public/images/candidatas/{num}.webp`, 600×600 WebP) mapped by `num` in
  `src/components/Candidatas.astro`.
- `../../gesell/villa-gesell/site/` — stack/structure reference (Astro 6 static,
  Tailwind v4 `@theme`, sitemap, BottomNav mobile, Firebase hosting headers).

## Scope

In: Home, La Lista (with search), Por qué la CTA, Cómo votar, Sumate/Contacto,
Nav + BottomNav + Footer, SEO/OG, Firebase project + hosting, domain hookup.

Out (for now): DNI/mesa lookup (mesas not assigned yet — later phase, CTERA pattern:
server-side rate limit, never a public padrón); padrón composition percentages
(user decision: not published for now); agenda, news blog, normativas, and every
SUTEBA-teacher-specific section (ESI, estatuto docente, actos, concursos).

## Constraints

- Astro 6 static, Tailwind v4 CSS-first tokens, `@astrojs/sitemap`, **pnpm only**.
- Same palette as Gesell (user decision): primary `#C41E2A`, secondary `#2E7D32`,
  accent `#E91E8E`, dark `#1A1A1A`, light `#FAFAFA` + multicolor gradient utilities.
- Mobile-first: base classes = phone, BottomNav `md:hidden`, safe-area insets.
- No invented content: missing texts go as visible `[PENDIENTE]` markers.
- No PII in the repo or the site: only the published ballot's names + public photos.
- Delivery: work-unit commit per task on branch `CTA`; push/PR/deploy to production
  only with explicit user approval.

## Open decisions / pending inputs

- [x] **Election date** — **3 Nov 2026 confirmed by the user** (2026-09-27); `ELECTION_DATE_CONFIRMED=true`.
  The 08:00 opening time used by the countdown is still an assumption.
- [ ] Secretariat photo missing: **Nancy Decoud** (10/11 have photo). 45 photos total.
- [x] Confirmed by the user: "Sofía Antonella Vega" (vocales-8) IS the same person as the web_multi #79 flyer
  ("SOFÍA VEGA — CONGRESAL", currently used for congresales-titulares-23 "Sofía Vega")?
- [ ] Review all 45 photos together with the user (`odd/data/foto_matches_v2.json`).
- [ ] Propuestas, "Por qué la CTA" body, requisitos para votar, redes, contacto → `[PENDIENTE]`.
- [x] Firebase project `cta-multicolor-2026` created by the user; hosting live.
- [x] Cloudflare DNS + Firebase custom domains done by the user (2026-09-28): apex A
  199.36.158.100 + TXT, `www` CNAME; both serve 200 with their own certificates. `www` serves
  the site (not a redirect); canonical tag points to the apex.

## Verification mode

TDD: **off** (static content site, no existing test runner in this worktree; source:
no project config). Functional checks per task: `pnpm build` passes + real-browser
check at 360px and desktop (claude-in-chrome, served over local HTTP).

## Tasks

- [x] **T1 — Scaffold.** Astro 7 static + Tailwind v4 `@theme` + sitemap, pnpm 11
  (`allowBuilds.esbuild`), `@astrojs/check` (TS ^6). Route: delegated writer. Commit `1014620e`.
- [x] **T2 — Data.** `lista.ts` 106 candidacies, counts 11/9/6/60/20 verified against
  the ballot (delegated transcriber). `site.ts` date + slogans. Commit `1014620e`.
- [x] **T3 — Photos.** 45 × 400×400 WebP, matched by the **name printed on each flyer**
  (numbering in web_multi was wrong for 11/26). Commit `72c9a912`.
- [x] **T4 — Home.** White hero (rainbow wordmark only reads on white), countdown,
  secretariat, CTAs. Commits `1014620e`, `ba86992f`.
- [x] **T5 — La Lista.** Grouped 106 + accent/case-insensitive search + swipeable
  bloque chips (`role=group`, `aria-pressed`). Checked in real Chrome.
- [x] **T6 — Por qué la CTA.** Slogans + `[PENDIENTE]` body.
- [x] **T7 — Cómo votar.** Date, "¿dónde voto?" note, requisitos `[PENDIENTE]`.
- [x] **T8 — Navigation & closing.** Nav (Escape, `aria-expanded`), BottomNav, Sumate, Footer, 404.
- [x] **T9 — Firebase.** `firebase.json` (security headers, 300 s HTML incl. clean URLs,
  immutable `_astro`, 1 day images, real 404), `.firebaserc`. Deployed to
  https://cta-multicolor-2026.web.app (goal authorized deploy). Commits `4e06d716`, `8dcb70e5`.
  Custom domains https://ctamulticolor.com.ar and www live (2026-09-28).
- [x] **T10 — QA.** Production: all pages 200, real 404, headers verified with curl;
  Chrome interaction pass, 0 console errors, 0 broken images; Lighthouse mobile (lh6):
  Home 100/100/100/100 (LCP 1.7 s), Lista 94/100/100/100 (LCP 3.1 s simulated; observed
  subparts ≈ 0.54 s — cost of the 106-card HTML), Por qué / Cómo votar / Sumate
  100/100/100/100. Commit `ba86992f`.

## Progress

- 2026-09-27: T1–T10 done and deployed. `astro check` 0 errors, `pnpm install
  --frozen-lockfile` OK.
- 2026-09-28: date confirmed, Sofía Vega photo on both cards, branch pushed, custom domain live.

## Next step

User inputs: Decoud photo, photo review, campaign texts (propuestas, por qué la CTA,
requisitos, redes, contacto).
Tech debt (postponed by user): geocoded Leaflet map of workplaces — Engram
`deuda/mapa-geocodificado-cta-lugares`.
