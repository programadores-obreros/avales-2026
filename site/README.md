# ctamulticolor.com.ar

Campaign site for Lista 6 Multicolor — CTA La Matanza. Astro (static) + Tailwind v4, mobile-first.

## Commands (pnpm only)

| Command | What it does |
| --- | --- |
| `pnpm install` | Install dependencies |
| `pnpm dev` | Dev server at `localhost:4321` |
| `pnpm build` | Build to `dist/` |
| `pnpm astro check` | Type-check `.astro` and `.ts` files |
| `pnpm preview` | Serve the built site locally |

## Deploy (Firebase Hosting)

Config lives one level up (`../firebase.json`, project `cta-multicolor-2026`).

```sh
pnpm build
cd .. && pnpm dlx firebase-tools deploy --only hosting
```

## Content

- `src/data/lista.ts` — the 106 candidacies, transcribed from the official ballot. Photos in
  `public/images/candidatos/` were matched to people by the name printed on each source
  flyer (not by any numbering) and cropped to remove the May campaign captions.
- `src/data/site.ts` — election date (`ELECTION_DATE_CONFIRMED` stays `false` until confirmed),
  slogans, links. Missing copy is rendered as visible `[PENDIENTE]` markers on purpose.
