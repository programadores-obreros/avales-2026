// site.ts — Site-wide config for the Lista 6 Multicolor (CTA La Matanza) campaign site.

/**
 * Election date/time, ISO 8601 with explicit Argentina offset (-03:00).
 * Day confirmed by the list (2026-09-27). The 08:00 opening time is still an assumption
 * used only by the countdown.
 */
export const ELECTION_DATE = '2026-11-03T08:00:00-03:00';

/** When false, any UI showing ELECTION_DATE must also show "fecha estimada — a confirmar". */
export const ELECTION_DATE_CONFIRMED = true;

export const LISTA_NUMERO = 6;
export const LISTA_NOMBRE = 'Lista 6 Multicolor';

/** Verbatim from the official ballot — do not paraphrase. */
export const SLOGAN_1 = 'En mayo recuperamos el SUTEBA, ahora recuperemos la CTA';
export const SLOGAN_2 =
  'Por una central independiente que enfrente la motosierra de Milei y el ajuste de Kicillof';

/** Verbatim from the official ballot. */
export const BOLETA_TITULO = 'Lxs candidatxs de la Lista 6 Multicolor La Matanza';

export const SITE_URL = 'https://ctamulticolor.com.ar';
export const SITE_TITLE = 'Lista 6 Multicolor — CTA La Matanza';
export const SITE_DESCRIPTION =
  'Lista 6 Multicolor en las elecciones de la CTA La Matanza. En mayo recuperamos el SUTEBA, ahora recuperemos la CTA.';

/** No real values yet — render as [PENDIENTE] wherever used, never invent handles. */
export const REDES = {
  instagram: null as string | null,
  facebook: null as string | null,
  twitter: null as string | null,
  whatsapp: null as string | null,
};

/** No real contact channel yet — render as [PENDIENTE]. */
export const CONTACTO_EMAIL: string | null = null;
