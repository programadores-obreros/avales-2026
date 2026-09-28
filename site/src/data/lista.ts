// Transcribed from the official ballot image:
// eleccionesSUTEBA2026/cta/lista_oficial.jpeg (1080x1440)
// "Lxs candidatxs de la Lista 6 Multicolor - La Matanza"
//
// Accuracy note: `nombre` is kept EXACTLY as printed on the ballot (word
// order, accents, capitalization), including apparent inconsistencies such
// as 'Farias YAnina' or 'Castillo sergio'. `cargo` (secretariado only) uses
// proper casing/expansion per the agreed contract, e.g. the printed
// "Sec. De Formación, Investigación, Proyectos y Estadísticas" is expanded
// to "Secretaría de Formación, Investigación, Proyectos y Estadísticas".

export type Bloque = 'secretariado' | 'vocales' | 'revisora' | 'congresales-titulares' | 'congresales-suplentes';

export interface Candidatura {
  id: string;        // `${bloque}-${orden}`, e.g. 'secretariado-1', 'congresales-titulares-60'
  bloque: Bloque;
  orden: number;     // 1-based position within its bloque (for secretariado: reading order described above)
  nombre: string;    // EXACTLY as printed (keep the ballot's word order, accents, capitalization; normalize only obvious OCR-like spacing)
  cargo?: string;    // secretariado only, with proper casing
  foto?: string;     // leave absent
}

export const BLOQUES: { id: Bloque; titulo: string }[] = [
  { id: 'secretariado', titulo: 'Secretariado' },
  { id: 'vocales', titulo: 'Vocales' },
  { id: 'revisora', titulo: 'Comisión Revisora de Cuentas' },
  { id: 'congresales-titulares', titulo: 'Congresales provinciales titulares' },
  { id: 'congresales-suplentes', titulo: 'Congresales provinciales suplentes' },
];

export const CANDIDATURAS: Candidatura[] = [
  // ── Secretariado (11) — left column top→bottom, then right column top→bottom ──
  { id: 'secretariado-1', bloque: 'secretariado', orden: 1, cargo: 'Secretario General', nombre: 'Juan Emiliano Romero', foto: '/images/candidatos/juan-romero.webp' },
  { id: 'secretariado-2', bloque: 'secretariado', orden: 2, cargo: 'Secretaria Adjunta', nombre: 'Coronel Valeria Ramona', foto: '/images/candidatos/valeria-coronel.webp' },
  { id: 'secretariado-3', bloque: 'secretariado', orden: 3, cargo: 'Secretaria Gremial', nombre: 'Lorena Barbuto', foto: '/images/candidatos/lorena-barbuto.webp' },
  { id: 'secretariado-4', bloque: 'secretariado', orden: 4, cargo: 'Secretaria de Organización', nombre: 'Aldana Belén Rojas', foto: '/images/candidatos/aldana-rojas.webp' },
  { id: 'secretariado-5', bloque: 'secretariado', orden: 5, cargo: 'Secretaría de Finanzas', nombre: 'Nancy Decoud' },
  { id: 'secretariado-6', bloque: 'secretariado', orden: 6, cargo: 'Secretaría de Comunicación', nombre: 'Settembrini Ernesto', foto: '/images/candidatos/ernesto-settembrini.webp' },
  { id: 'secretariado-7', bloque: 'secretariado', orden: 7, cargo: 'Secretaria Administrativa y de Actas', nombre: 'Petrungaro Duilio V.', foto: '/images/candidatos/duilio-petrungaro.webp' },
  { id: 'secretariado-8', bloque: 'secretariado', orden: 8, cargo: 'Secretaría de Seguridad Social', nombre: 'María Verónica Barrera', foto: '/images/candidatos/ma-veronica-barrera.webp' },
  { id: 'secretariado-9', bloque: 'secretariado', orden: 9, cargo: 'Secretaría de Derechos Humanos', nombre: 'Silvia Martín', foto: '/images/candidatos/silvia-martin.webp' },
  { id: 'secretariado-10', bloque: 'secretariado', orden: 10, cargo: 'Secretaria de Géneros e Igualdad de Oportunidades', nombre: 'Rosana Ester Espada', foto: '/images/candidatos/rosana-espada.webp' },
  { id: 'secretariado-11', bloque: 'secretariado', orden: 11, cargo: 'Secretaría de Formación, Investigación, Proyectos y Estadísticas', nombre: 'Garbarino Sandra', foto: '/images/candidatos/sandra-garbarino.webp' },

  // ── Vocales (9) ──
  { id: 'vocales-1', bloque: 'vocales', orden: 1, nombre: 'Molina Sabrina', foto: '/images/candidatos/sabrina-molina.webp' },
  { id: 'vocales-2', bloque: 'vocales', orden: 2, nombre: 'Nancy Farias', foto: '/images/candidatos/nancy-farias.webp' },
  { id: 'vocales-3', bloque: 'vocales', orden: 3, nombre: 'Jesica Lazarte' },
  { id: 'vocales-4', bloque: 'vocales', orden: 4, nombre: 'Giuliana Agustina Rojas', foto: '/images/candidatos/giuliana-rojas.webp' },
  { id: 'vocales-5', bloque: 'vocales', orden: 5, nombre: 'Manuel Roberto Andrés Machuca Gallegos', foto: '/images/candidatos/andres-machuca.webp' },
  { id: 'vocales-6', bloque: 'vocales', orden: 6, nombre: 'Melian Anabella', foto: '/images/candidatos/anabella-melian.webp' },
  { id: 'vocales-7', bloque: 'vocales', orden: 7, nombre: 'Luaces Mario', foto: '/images/candidatos/mario-luaces.webp' },
  { id: 'vocales-8', bloque: 'vocales', orden: 8, nombre: 'Sofía Antonella Vega', foto: '/images/candidatos/sofia-vega.webp' },
  { id: 'vocales-9', bloque: 'vocales', orden: 9, nombre: 'Gabriela Zaragoza', foto: '/images/candidatos/gabriela-zaragoza.webp' },

  // ── Comisión Revisora de Cuentas (6) ──
  { id: 'revisora-1', bloque: 'revisora', orden: 1, nombre: 'Torres Fabiana', foto: '/images/candidatos/fabiana-torres.webp' },
  { id: 'revisora-2', bloque: 'revisora', orden: 2, nombre: 'Garcia Maria Paula', foto: '/images/candidatos/paula-garcia.webp' },
  { id: 'revisora-3', bloque: 'revisora', orden: 3, nombre: 'Laura Elizalde', foto: '/images/candidatos/laura-elizalde.webp' },
  { id: 'revisora-4', bloque: 'revisora', orden: 4, nombre: 'Susana Barraza', foto: '/images/candidatos/susana-barraza.webp' },
  { id: 'revisora-5', bloque: 'revisora', orden: 5, nombre: 'Giocoli Martin' },
  { id: 'revisora-6', bloque: 'revisora', orden: 6, nombre: 'Vicentela Mario Ezequiel', foto: '/images/candidatos/ezequiel-vicentela.webp' },

  // ── Candidatos a Congresales Provinciales Titulares (60) ──
  { id: 'congresales-titulares-1', bloque: 'congresales-titulares', orden: 1, nombre: 'Acuña Carmen', foto: '/images/candidatos/carmen-acuna.webp' },
  { id: 'congresales-titulares-2', bloque: 'congresales-titulares', orden: 2, nombre: 'Coronel Valeria Ramona', foto: '/images/candidatos/valeria-coronel.webp' },
  { id: 'congresales-titulares-3', bloque: 'congresales-titulares', orden: 3, nombre: 'Lorena Barbuto', foto: '/images/candidatos/lorena-barbuto.webp' },
  { id: 'congresales-titulares-4', bloque: 'congresales-titulares', orden: 4, nombre: 'Aldana Belén Rojas', foto: '/images/candidatos/aldana-rojas.webp' },
  { id: 'congresales-titulares-5', bloque: 'congresales-titulares', orden: 5, nombre: 'Néstor Eduardo Souza', foto: '/images/candidatos/nestor-souza.webp' },
  { id: 'congresales-titulares-6', bloque: 'congresales-titulares', orden: 6, nombre: 'Brito Sonia', foto: '/images/candidatos/sonia-brito.webp' },
  { id: 'congresales-titulares-7', bloque: 'congresales-titulares', orden: 7, nombre: 'Petrungaro Duilio Vicente', foto: '/images/candidatos/duilio-petrungaro.webp' },
  { id: 'congresales-titulares-8', bloque: 'congresales-titulares', orden: 8, nombre: 'María Verónica Barrera', foto: '/images/candidatos/ma-veronica-barrera.webp' },
  { id: 'congresales-titulares-9', bloque: 'congresales-titulares', orden: 9, nombre: 'Silvia Martín', foto: '/images/candidatos/silvia-martin.webp' },
  { id: 'congresales-titulares-10', bloque: 'congresales-titulares', orden: 10, nombre: 'Juan Bautista Rojas Leotus', foto: '/images/candidatos/juan-bautista-rojas.webp' },
  { id: 'congresales-titulares-11', bloque: 'congresales-titulares', orden: 11, nombre: 'Farias YAnina', foto: '/images/candidatos/yanina-farias.webp' },
  { id: 'congresales-titulares-12', bloque: 'congresales-titulares', orden: 12, nombre: 'Luaces Mario', foto: '/images/candidatos/mario-luaces.webp' },
  { id: 'congresales-titulares-13', bloque: 'congresales-titulares', orden: 13, nombre: 'Jesica Lazarte' },
  { id: 'congresales-titulares-14', bloque: 'congresales-titulares', orden: 14, nombre: 'Giuliana Agustina Rojas', foto: '/images/candidatos/giuliana-rojas.webp' },
  { id: 'congresales-titulares-15', bloque: 'congresales-titulares', orden: 15, nombre: 'Manuel Roberto Andrés Machuca G.', foto: '/images/candidatos/andres-machuca.webp' },
  { id: 'congresales-titulares-16', bloque: 'congresales-titulares', orden: 16, nombre: 'Signorello Paula' },
  { id: 'congresales-titulares-17', bloque: 'congresales-titulares', orden: 17, nombre: 'Almiron Sergio', foto: '/images/candidatos/sergio-almiron.webp' },
  { id: 'congresales-titulares-18', bloque: 'congresales-titulares', orden: 18, nombre: 'Larramendi Antonio' },
  { id: 'congresales-titulares-19', bloque: 'congresales-titulares', orden: 19, nombre: 'Gabriela Zaragoza', foto: '/images/candidatos/gabriela-zaragoza.webp' },
  { id: 'congresales-titulares-20', bloque: 'congresales-titulares', orden: 20, nombre: 'Marcos Emanuel Sánchez' },
  { id: 'congresales-titulares-21', bloque: 'congresales-titulares', orden: 21, nombre: 'Ugarte Maria Teresa', foto: '/images/candidatos/teresa-ugarte.webp' },
  { id: 'congresales-titulares-22', bloque: 'congresales-titulares', orden: 22, nombre: 'Ayala Elizabeth Solange', foto: '/images/candidatos/elizabeth-ayala.webp' },
  { id: 'congresales-titulares-23', bloque: 'congresales-titulares', orden: 23, nombre: 'Sofía Vega', foto: '/images/candidatos/sofia-vega.webp' },
  { id: 'congresales-titulares-24', bloque: 'congresales-titulares', orden: 24, nombre: 'Carina Vallejo' },
  { id: 'congresales-titulares-25', bloque: 'congresales-titulares', orden: 25, nombre: 'Riquelme Patricia', foto: '/images/candidatos/patricia-riquelme.webp' },
  { id: 'congresales-titulares-26', bloque: 'congresales-titulares', orden: 26, nombre: 'Caminos Veronica', foto: '/images/candidatos/veronica-caminos.webp' },
  { id: 'congresales-titulares-27', bloque: 'congresales-titulares', orden: 27, nombre: 'Pizzi Adriano Mauro' },
  { id: 'congresales-titulares-28', bloque: 'congresales-titulares', orden: 28, nombre: 'Aldana Recine' },
  { id: 'congresales-titulares-29', bloque: 'congresales-titulares', orden: 29, nombre: 'Nora Rosana Vallejo' },
  { id: 'congresales-titulares-30', bloque: 'congresales-titulares', orden: 30, nombre: 'Conde Silvia Cristina' },
  { id: 'congresales-titulares-31', bloque: 'congresales-titulares', orden: 31, nombre: 'Largente Nemiña Federico', foto: '/images/candidatos/federico-largente.webp' },
  { id: 'congresales-titulares-32', bloque: 'congresales-titulares', orden: 32, nombre: 'Leiva Dominguez Francisco Javier', foto: '/images/candidatos/francisco-leiva.webp' },
  { id: 'congresales-titulares-33', bloque: 'congresales-titulares', orden: 33, nombre: 'Sofía Candela Perez', foto: '/images/candidatos/sofia-perez.webp' },
  { id: 'congresales-titulares-34', bloque: 'congresales-titulares', orden: 34, nombre: 'Elizabeth del Valle Guanca' },
  { id: 'congresales-titulares-35', bloque: 'congresales-titulares', orden: 35, nombre: 'Robles Edith Isabel' },
  { id: 'congresales-titulares-36', bloque: 'congresales-titulares', orden: 36, nombre: 'Vazquez Diego', foto: '/images/candidatos/diego-vazquez.webp' },
  { id: 'congresales-titulares-37', bloque: 'congresales-titulares', orden: 37, nombre: 'Cardozo Edgardo Tristan' },
  { id: 'congresales-titulares-38', bloque: 'congresales-titulares', orden: 38, nombre: 'Estevez Ariel' },
  { id: 'congresales-titulares-39', bloque: 'congresales-titulares', orden: 39, nombre: 'Gabriela Paez' },
  { id: 'congresales-titulares-40', bloque: 'congresales-titulares', orden: 40, nombre: 'Diaz Ivana' },
  { id: 'congresales-titulares-41', bloque: 'congresales-titulares', orden: 41, nombre: 'Rueda Adriana Isabel' },
  { id: 'congresales-titulares-42', bloque: 'congresales-titulares', orden: 42, nombre: 'Bernal Raquel Ivon' },
  { id: 'congresales-titulares-43', bloque: 'congresales-titulares', orden: 43, nombre: 'Míriam Andrea Amaya' },
  { id: 'congresales-titulares-44', bloque: 'congresales-titulares', orden: 44, nombre: 'Paola Alejandra Lopez' },
  { id: 'congresales-titulares-45', bloque: 'congresales-titulares', orden: 45, nombre: 'Heredia Analia' },
  { id: 'congresales-titulares-46', bloque: 'congresales-titulares', orden: 46, nombre: 'Pelliza Florencia' },
  { id: 'congresales-titulares-47', bloque: 'congresales-titulares', orden: 47, nombre: 'Ibrahim Miriam Karina' },
  { id: 'congresales-titulares-48', bloque: 'congresales-titulares', orden: 48, nombre: 'Alberto Alejandro Cáceres' },
  { id: 'congresales-titulares-49', bloque: 'congresales-titulares', orden: 49, nombre: 'Silvia Cisnero' },
  { id: 'congresales-titulares-50', bloque: 'congresales-titulares', orden: 50, nombre: 'Andrada Sabrina', foto: '/images/candidatos/sabrina-andrada.webp' },
  { id: 'congresales-titulares-51', bloque: 'congresales-titulares', orden: 51, nombre: 'Nuñez Silvia', foto: '/images/candidatos/silvia-nunez.webp' },
  { id: 'congresales-titulares-52', bloque: 'congresales-titulares', orden: 52, nombre: 'Sosa Rocio Eliana' },
  { id: 'congresales-titulares-53', bloque: 'congresales-titulares', orden: 53, nombre: 'Carolina Anabel Elizalde' },
  { id: 'congresales-titulares-54', bloque: 'congresales-titulares', orden: 54, nombre: 'Hille Daiana' },
  { id: 'congresales-titulares-55', bloque: 'congresales-titulares', orden: 55, nombre: 'Vergara Ivana' },
  { id: 'congresales-titulares-56', bloque: 'congresales-titulares', orden: 56, nombre: 'Romero Rodrigo', foto: '/images/candidatos/rodrigo-romero.webp' },
  { id: 'congresales-titulares-57', bloque: 'congresales-titulares', orden: 57, nombre: 'Rodriguez Juan Jose', foto: '/images/candidatos/juan-jose-rodriguez.webp' },
  { id: 'congresales-titulares-58', bloque: 'congresales-titulares', orden: 58, nombre: 'José Luis Flores' },
  { id: 'congresales-titulares-59', bloque: 'congresales-titulares', orden: 59, nombre: 'Diego Gaston Martinez' },
  { id: 'congresales-titulares-60', bloque: 'congresales-titulares', orden: 60, nombre: 'Ledesma Victor', foto: '/images/candidatos/victor-ledesma.webp' },

  // ── Candidatos a Congresales Provinciales Suplentes (20) ──
  { id: 'congresales-suplentes-1', bloque: 'congresales-suplentes', orden: 1, nombre: 'Manoukian Marta' },
  { id: 'congresales-suplentes-2', bloque: 'congresales-suplentes', orden: 2, nombre: 'Castillo sergio' },
  { id: 'congresales-suplentes-3', bloque: 'congresales-suplentes', orden: 3, nombre: 'Karina Verónica Rodriguez' },
  { id: 'congresales-suplentes-4', bloque: 'congresales-suplentes', orden: 4, nombre: 'Urso Claudia' },
  { id: 'congresales-suplentes-5', bloque: 'congresales-suplentes', orden: 5, nombre: 'Gonzalez Rebeca', foto: '/images/candidatos/rebeca-gonzalez.webp' },
  { id: 'congresales-suplentes-6', bloque: 'congresales-suplentes', orden: 6, nombre: 'Rizzo Claudia' },
  { id: 'congresales-suplentes-7', bloque: 'congresales-suplentes', orden: 7, nombre: 'Segovia Giselle Natalia', foto: '/images/candidatos/giselle-segovia.webp' },
  { id: 'congresales-suplentes-8', bloque: 'congresales-suplentes', orden: 8, nombre: 'Alba Álvarez' },
  { id: 'congresales-suplentes-9', bloque: 'congresales-suplentes', orden: 9, nombre: 'Torres Joana' },
  { id: 'congresales-suplentes-10', bloque: 'congresales-suplentes', orden: 10, nombre: 'Metola Leandro Federico' },
  { id: 'congresales-suplentes-11', bloque: 'congresales-suplentes', orden: 11, nombre: 'Fons Fabian Gonzalo' },
  { id: 'congresales-suplentes-12', bloque: 'congresales-suplentes', orden: 12, nombre: 'Robles Rocio Jimena', foto: '/images/candidatos/jimena-robles.webp' },
  { id: 'congresales-suplentes-13', bloque: 'congresales-suplentes', orden: 13, nombre: 'José Brizuela' },
  { id: 'congresales-suplentes-14', bloque: 'congresales-suplentes', orden: 14, nombre: 'Garcia Lorena' },
  { id: 'congresales-suplentes-15', bloque: 'congresales-suplentes', orden: 15, nombre: 'Silva Juan' },
  { id: 'congresales-suplentes-16', bloque: 'congresales-suplentes', orden: 16, nombre: 'Grillo Susana' },
  { id: 'congresales-suplentes-17', bloque: 'congresales-suplentes', orden: 17, nombre: 'Battaglia Veronica Alejandra' },
  { id: 'congresales-suplentes-18', bloque: 'congresales-suplentes', orden: 18, nombre: 'Silvina Faingold' },
  { id: 'congresales-suplentes-19', bloque: 'congresales-suplentes', orden: 19, nombre: 'Santiesteban Erica' },
  { id: 'congresales-suplentes-20', bloque: 'congresales-suplentes', orden: 20, nombre: 'Chamorro Maria del Carmen' },
];

// Dev-time sanity check (not enforced at runtime):
// CANDIDATURAS.length === 106
// CANDIDATURAS.filter(c => c.bloque === 'secretariado').length === 11
// CANDIDATURAS.filter(c => c.bloque === 'vocales').length === 9
// CANDIDATURAS.filter(c => c.bloque === 'revisora').length === 6
// CANDIDATURAS.filter(c => c.bloque === 'congresales-titulares').length === 60
// CANDIDATURAS.filter(c => c.bloque === 'congresales-suplentes').length === 20
// Every bloque's `orden` sequence is 1..N with no gaps or duplicates.
