// share.ts — WhatsApp share copy for Lista 6 Multicolor, CTA La Matanza.
// Edit the strings in SHARE_TEXTS to update campaign share copy; each URL in
// SHARE_URLS is appended after the text (one space) when building a wa.me link.
// Used by ShareModal.astro (every page) and boleta.astro.
import { SITE_URL, SLOGAN_1, SLOGAN_2 } from './site';

export const SHARE_TEXTS = {
  boleta: `Esta es la boleta de la Lista 6 Multicolor para la CTA La Matanza. El 3 de noviembre votamos Lista 6. ${SLOGAN_2}.`,
  sitio: `Lista 6 Multicolor — CTA La Matanza. ${SLOGAN_1}. Conocé la lista, la historia de la CTA y cómo votar:`,
  fecha: `El 3 de noviembre de 2026 son las elecciones de la CTA La Matanza. Votamos Lista 6 Multicolor. Toda la info para votar:`,
  lista: `Buscá a tus compañerxs en la Lista 6 Multicolor para la CTA La Matanza: 106 candidaturas, con buscador.`,
  sumate: `Sumate a la campaña de la Lista 6 Multicolor en la CTA La Matanza:`,
} as const;

export type ShareKey = keyof typeof SHARE_TEXTS;

export const SHARE_URLS: Record<ShareKey, string> = {
  boleta: `${SITE_URL}/boleta`,
  sitio: `${SITE_URL}/`,
  fecha: `${SITE_URL}/como-votar`,
  lista: `${SITE_URL}/lista`,
  sumate: `${SITE_URL}/sumate`,
};

/** Builds a wa.me link with the share text followed by its URL (one space between them). */
export function waLink(key: ShareKey): string {
  const text = `${SHARE_TEXTS[key]} ${SHARE_URLS[key]}`;
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

/** Ballot asset paths. */
export const BOLETA_JPG_PATH = '/boleta/boleta-lista-6-multicolor-cta-la-matanza.jpg';
/** Full-size WebP for the /boleta page display (900×1200). */
export const BOLETA_WEBP_PATH = '/boleta/boleta-lista-6-multicolor-cta-la-matanza.webp';
/** Small WebP (240×320) for the share modal thumbnail — avoids downloading the
 * full-size image just to show a ~112px-tall preview. */
export const BOLETA_THUMB_WEBP_PATH = '/boleta/boleta-lista-6-multicolor-cta-la-matanza-thumb.webp';
export const BOLETA_JPG_FILENAME = 'boleta-lista-6-multicolor.jpg';
