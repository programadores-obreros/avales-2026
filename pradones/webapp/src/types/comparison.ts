export const COMPARISON_STATUS = {
  MANTIENE: "mantiene",
  NUEVA: "nueva",
  ELIMINADA: "eliminada",
} as const;

export type ComparisonStatus =
  (typeof COMPARISON_STATUS)[keyof typeof COMPARISON_STATUS];

export interface ComparisonEntry {
  id: number;
  establecimiento: string;
  direccion: string;
  mesa_2022: string | null;
  mesa_2026: string | null;
  estado: ComparisonStatus;
  lat: number | null;
  lng: number | null;
  localidad: string | null;
  zona_2022: number | null;
  zona_nombre_2022: string | null;
  cambio_mesa?: boolean;
  match_por?: string;
}

export interface ComparisonSummary {
  total_2022: number;
  total_2026: number;
  maintained: number;
  new_2026: number;
  removed: number;
  with_coords: number;
}

export interface ComparisonData {
  generated: string;
  summary: ComparisonSummary;
  entries: ComparisonEntry[];
}
