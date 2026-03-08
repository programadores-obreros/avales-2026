export interface Votante {
  tipo: string;
  documento: string;
  nombre: string;
  distrito_escuela: string;
  escuela_code: string;
  mesa_sede: number;
  zona: number;
  zona_nombre: string;
  escuela_sede: string;
  direccion: string;
  localidad_sede: string;
}

export interface Mesa {
  mesa: number;
  escuela_sede: string;
  direccion: string;
  localidad: string;
  mapa: string;
  lat: number;
  lng: number;
  zona: number;
  zona_nombre: string;
  votantes: number;
  escuelas: string[];
}

export interface Zona {
  zona: number;
  zona_nombre: string;
  votantes: number;
  mesas: number;
  escuelas: number;
}

export interface AppData {
  votantes: Votante[];
  mesas: Mesa[];
  zonas: Zona[];
}

export const SEARCH_MODE = {
  DNI: "dni",
  ZONA: "zona",
  SEDE: "sede",
  ESCUELA: "escuela",
} as const;

export type SearchMode = (typeof SEARCH_MODE)[keyof typeof SEARCH_MODE];
