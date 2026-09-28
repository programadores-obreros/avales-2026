// historia.ts — Political history of the CTA, in four eras. Every fact below was
// verified by fetching its source URL on 2026-09-28 (see task T11). Do not add
// facts, numbers, quotes or claims beyond what is sourced here.

export interface Hito {
  id: string;
  /** ISO date, or YYYY-MM, or YYYY — as precise as the source allows. */
  fecha: string;
  fechaTexto: string;
  titulo: string;
  texto: string;
  fuente: { nombre: string; url: string };
  /** 'analisis' marks interpretation (e.g. a researcher's reading), not a bare fact. */
  tipo?: 'hecho' | 'analisis';
}

export interface Era {
  id: string;
  titulo: string;
  periodo: string;
  resumen: string;
  hitos: Hito[];
}

const FUENTE_FUNDACION = {
  nombre: 'CTA Autónoma',
  url: 'https://ctaa.org.ar/a-31-anos-de-la-fundacion-de-la-cta-para-que-nuestra-dignidad-se-ponga-en-marcha/',
};

const FUENTE_DIVISION_2014 = {
  nombre: 'Infobae',
  url: 'https://www.infobae.com/2014/10/04/1599496-el-ministerio-trabajo-avalo-el-divorcio-las-dos-cta/',
};

const FUENTE_DATAGREMIAL = {
  nombre: 'Datagremial',
  url: 'https://www.datagremial.com/informacion-general/recambio-en-la-cta-de-los-trabajadores-hugo-yasky-deja-la-conduccion-y-baradel-buscara-ser-su-sucesor-20269151010',
};

export const ERAS: Era[] = [
  {
    id: 'nacimiento',
    titulo: 'El nacimiento',
    periodo: '1991–1992',
    resumen:
      'Sindicatos estatales y docentes rompen con la CGT que acompañaba las privatizaciones de Menem y fundan una central nueva.',
    hitos: [
      {
        id: 'grito-burzaco',
        fecha: '1991-12-17',
        fechaTexto: '17 de diciembre de 1991',
        titulo: 'El Grito de Burzaco',
        texto:
          'Sindicatos encabezados por ATE y CTERA rompen con la CGT, que acompañaba las privatizaciones del gobierno de Carlos Menem, y lanzan la construcción de una nueva central.',
        fuente: FUENTE_FUNDACION,
      },
      {
        id: 'encuentro-rosario',
        fecha: '1992-04-04',
        fechaTexto: '4 de abril de 1992',
        titulo: 'Encuentro de Rosario',
        texto:
          '1.571 dirigentes de veinte provincias se reúnen para darle forma a la nueva organización.',
        fuente: FUENTE_FUNDACION,
      },
      {
        id: 'congreso-fundacional',
        fecha: '1992-11-14',
        fechaTexto: '14 de noviembre de 1992',
        titulo: 'Congreso fundacional en Parque Sarmiento',
        texto:
          'Más de 2.500 delegadxs fundan el Congreso de los Trabajadores Argentinos. La conducción provisoria la integran, entre otrxs, Víctor De Gennaro (ATE) y Mary Sánchez (CTERA). Su primera tarea: juntar un millón de firmas contra las jubilaciones privadas.',
        fuente: FUENTE_FUNDACION,
      },
    ],
  },
  {
    id: 'resistencia-90',
    titulo: 'Resistir los 90',
    periodo: '1994–2001',
    resumen: 'La CTA se vuelve la referencia de la resistencia al menemismo y a la crisis de 2001.',
    hitos: [
      {
        id: 'marcha-federal',
        fecha: '1994-07-06',
        fechaTexto: '6 de julio de 1994',
        titulo: 'Marcha Federal',
        texto:
          'Convocada por la CTA, el MTA y la CCC, más de 80.000 personas llegan a Plaza de Mayo contra la política económica del gobierno de Menem. Es la primera gran movilización multisectorial contra el menemismo.',
        fuente: { nombre: 'Ámbito', url: 'https://www.ambito.com/politica/la-marcha-federal-bisagra-los-noventa-n3990170' },
      },
      {
        id: 'nace-nombre-cta',
        fecha: '1996',
        fechaTexto: '1996',
        titulo: 'Nace el nombre: Central de Trabajadores de la Argentina',
        texto:
          'El primer Congreso Nacional de Delegados consolida la organización con su nombre actual, CTA.',
        fuente: FUENTE_FUNDACION,
      },
      {
        id: 'carpa-blanca',
        fecha: '1997-04-02',
        fechaTexto: '2 de abril de 1997 – 31 de diciembre de 1999',
        titulo: 'La Carpa Blanca',
        texto:
          'CTERA instala una carpa frente al Congreso durante 1.003 días; 1.500 docentes ayunan por turnos para reclamar una ley de financiamiento educativo.',
        fuente: { nombre: 'CTA de los Trabajadores', url: 'https://www.cta.org.ar/la-lucha-historica-de-la-carpa.html' },
      },
      {
        id: 'frenapo',
        fecha: '2001-12-14',
        fechaTexto: '14 al 17 de diciembre de 2001',
        titulo: 'Consulta popular del FRENAPO',
        texto:
          'Impulsada por la CTA, el Frente Nacional contra la Pobreza hace votar a más de tres millones de personas a favor de un seguro de empleo y formación para jefes y jefas de hogar desocupados, una asignación universal por hijx y un ingreso para mayores de 65 años sin jubilación.',
        fuente: { nombre: 'CTA Autónoma', url: 'https://ctaa.org.ar/a-veinte-anos-del-frenapo-ajuste-o-democracia/' },
      },
    ],
  },
  {
    id: 'ruptura',
    titulo: 'La ruptura',
    periodo: '2010–2014',
    resumen: 'Una elección interna escandalosa parte a la central en dos.',
    hitos: [
      {
        id: 'elecciones-2010',
        fecha: '2010-09',
        fechaTexto: 'Septiembre de 2010',
        titulo: 'Elecciones en disputa',
        texto:
          'Hugo Yasky (CTERA) y Pablo Micheli (ATE) se enfrentan por la conducción. El proceso termina con impugnaciones y denuncias cruzadas de fraude.',
        fuente: FUENTE_DIVISION_2014,
      },
      {
        id: 'analisis-autonomia',
        fecha: '2010',
        fechaTexto: 'Análisis',
        titulo: 'Dos formas de entender la autonomía',
        texto:
          'Según la investigadora María Belén Morris (revista Izquierdas, 2020), la ruptura enfrentó dos lecturas del principio de autonomía: una parte apostó a la acción sindical junto al gobierno de entonces; la otra, a la construcción independiente desde las bases.',
        fuente: { nombre: 'Morris, Izquierdas (2020)', url: 'https://www.redalyc.org/journal/3601/360174960016/html/' },
        tipo: 'analisis',
      },
      {
        id: 'division-formal',
        fecha: '2014-10-04',
        fechaTexto: '4 de octubre de 2014',
        titulo: 'La división se formaliza',
        texto:
          'Cuatro años después, el Ministerio de Trabajo avala la separación: la CTA de los Trabajadores, conducida por Yasky, y la CTA Autónoma, por Micheli.',
        fuente: FUENTE_DIVISION_2014,
      },
    ],
  },
  {
    id: '2026',
    titulo: '2026: la CTA en disputa',
    periodo: '2026',
    resumen: 'Con Milei en la Nación y ajuste salarial en la Provincia, la CTA de los Trabajadores cambia de conducción.',
    hitos: [
      {
        id: 'paro-docente-marzo',
        fecha: '2026-03-02',
        fechaTexto: '2 de marzo de 2026',
        titulo: 'Paro docente al inicio de clases',
        texto:
          'SUTEBA, FEB y otros gremios paran contra la oferta salarial del 3% del gobierno de Axel Kicillof.',
        fuente: {
          nombre: 'Infobae',
          url: 'https://www.infobae.com/politica/2026/02/21/suteba-se-suma-al-paro-contra-axel-kicillof-y-peligra-el-inicio-de-clases-en-la-provincia-de-buenos-aires/',
        },
      },
      {
        id: 'yasky-anuncia',
        fecha: '2026-04',
        fechaTexto: 'Abril de 2026',
        titulo: 'Yasky anuncia que no sigue',
        texto:
          'Después de 20 años al frente de la CTA de los Trabajadores, Hugo Yasky anuncia que no buscará otro mandato.',
        fuente: FUENTE_DATAGREMIAL,
      },
      {
        id: 'multicolor-recupera-suteba',
        fecha: '2026-05',
        fechaTexto: 'Mayo de 2026',
        titulo: 'La Multicolor recupera SUTEBA La Matanza',
        texto:
          'La lista Multicolor–Azul y Blanca gana la seccional más grande de la provincia por 2.297 a 2.135 votos frente a la Celeste-Violeta.',
        fuente: {
          nombre: 'La Izquierda Diario',
          url: 'https://www.laizquierdadiario.com/La-Multicolor-recupera-la-seccional-mas-grande-de-la-Provincia-desafia-a-la-burocracia-de-Baradel',
        },
      },
      {
        id: 'paro-docente-julio',
        fecha: '2026-07-01',
        fechaTexto: '1 al 8 de julio de 2026',
        titulo: 'Primer paro docente provincial en seis años',
        texto:
          'El Frente de Unidad Docente convoca a un paro para el 1 de julio y rechaza una oferta del 2,5%; el 8 de julio acuerda con el gobierno de Kicillof un aumento del 7% en dos cuotas.',
        fuente: {
          nombre: 'Infobae',
          url: 'https://www.infobae.com/politica/2026/07/08/el-gobierno-de-axel-kicillof-acordo-con-los-gremios-docentes-un-aumento-salarial-del-7/',
        },
      },
      {
        id: 'plan-lucha-cgt',
        fecha: '2026-07-22',
        fechaTexto: 'Desde el 22 de julio de 2026',
        titulo: 'Plan de lucha con la CGT',
        texto:
          'La CGT y las dos CTA coordinan marchas contra el endeudamiento familiar y contra el proyecto de "inviolabilidad de la propiedad privada", y acompañan la marcha de jubiladxs al Congreso. El quinto paro general sigue sin fecha.',
        fuente: {
          nombre: 'Infobae',
          url: 'https://www.infobae.com/politica/2026/09/17/la-cgt-y-las-cta-hicieron-un-balance-del-plan-de-lucha-contra-milei-que-pasara-con-el-paro-general/',
        },
      },
      {
        id: 'baradel-candidato',
        fecha: '2026-09',
        fechaTexto: 'Septiembre de 2026',
        titulo: 'Baradel, candidato del oficialismo',
        texto: 'Roberto Baradel deja la conducción de SUTEBA y encabeza la lista oficialista para suceder a Yasky.',
        fuente: {
          nombre: 'LeTrap',
          url: 'https://www.letrap.com.ar/politica/desgastado-su-cercania-axel-kicillof-baradel-deja-el-suteba-y-busca-reemplazar-yasky-la-cta-n5426578',
        },
      },
      {
        id: 'elecciones-cta-2026',
        fecha: '2026-11-03',
        fechaTexto: '3 de noviembre de 2026',
        titulo: 'Elecciones en la CTA',
        texto:
          'La CTA de los Trabajadores elige nueva conducción, que pone fin a 20 años de Yasky. En La Matanza se vota también la conducción de la regional.',
        fuente: FUENTE_DATAGREMIAL,
      },
    ],
  },
];

/** The three founding principles of the CTA. Source: same founding article. */
export const PRINCIPIOS: { titulo: string; texto: string }[] = [
  {
    titulo: 'Autonomía',
    texto: 'Independiente del Estado, de los gobiernos, de las patronales y de los partidos políticos.',
  },
  {
    titulo: 'Afiliación directa',
    texto: 'Cada trabajador y trabajadora se afilia de forma directa a la central, no solo a través de su sindicato.',
  },
  {
    titulo: 'Voto directo',
    texto: 'Lxs afiliadxs eligen a sus dirigentes con su voto.',
  },
];

export const PRINCIPIOS_FUENTE = FUENTE_FUNDACION;
