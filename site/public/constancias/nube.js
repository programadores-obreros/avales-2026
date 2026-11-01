/* Acceso a datos de las constancias.
   - Con firebase-config.js completo: la clave inicia sesión en la cuenta única de Firebase Auth
     y la lista de fiscales vive en Firestore (las reglas solo responden a esa cuenta).
   - Sin configurar: MODO PRUEBA, todo queda en este navegador (localStorage). Solo para probar. */
import { FIREBASE_CONFIG, CUENTA } from './firebase-config.js';

const SDK = 'https://www.gstatic.com/firebasejs/10.14.1/';
export const modoPrueba = !FIREBASE_CONFIG || !FIREBASE_CONFIG.apiKey;

let auth, db, fs, fa, cargando = null;

async function cargarSdk(){
  if(fs) return;
  // una sola carga: la lista y los dos diseños la piden a la vez
  if(!cargando){
    cargando = (async () => {
      const [app, a, f] = await Promise.all([import(SDK + 'firebase-app.js'), import(SDK + 'firebase-auth.js'), import(SDK + 'firebase-firestore.js')]);
      const fb = app.initializeApp(FIREBASE_CONFIG);
      fa = a; fs = f;
      auth = a.getAuth(fb);
      // si el navegador no deja guardar la sesión (o se cuelga), se sigue igual: solo
      // habrá que poner la clave de nuevo al recargar
      try{ await conLimite(a.setPersistence(auth, a.browserLocalPersistence), 5000); }catch(e){}
      db = f.getFirestore(fb);
    })().catch(() => { cargando = null; throw errorRed(); });
  }
  return cargando;
}

// Un bloqueador de anuncios (o el wifi del colegio) puede cortar gstatic o firestore:
// en vez de quedarse colgado para siempre, se avisa con un error identificable.
function errorRed(){ const e = new Error('sin-conexion'); e.code = 'sin-conexion'; return e; }

// corta una promesa que se queda colgada (Firestore reintenta solo y nunca falla)
function conLimite(promesa, ms){
  let reloj;
  const tiempo = new Promise((_, mal) => { reloj = setTimeout(() => mal(errorRed()), ms); });
  return Promise.race([promesa, tiempo]).finally(() => clearTimeout(reloj));
}

// ---------- sesión ----------
export async function alCambiarSesion(cb){
  if(modoPrueba){ cb(sessionStorage.getItem('cta-prueba-ok') === '1'); return; }
  await cargarSdk();
  fa.onAuthStateChanged(auth, u => cb(!!u));
}
export async function entrar(clave){
  if(modoPrueba){ if(!clave) throw new Error('vacia'); sessionStorage.setItem('cta-prueba-ok', '1'); return; }
  await cargarSdk();
  try{ await conLimite(fa.signInWithEmailAndPassword(auth, CUENTA, clave), 25000); }
  catch(err){
    if(err && (err.code === 'sin-conexion' || err.code === 'auth/network-request-failed')) throw errorRed();
    throw err;
  }
}
export async function salir(){
  if(modoPrueba){ sessionStorage.removeItem('cta-prueba-ok'); return; }
  await fa.signOut(auth);
}

// ---------- fiscales ----------
const LS = 'cta-prueba-fiscales';
const LS_ULTIMA = 'cta-ultima-lista';
const leerLS = () => { try{ return JSON.parse(localStorage.getItem(LS)) || []; }catch(e){ return []; } };
const listenersLS = [];
function guardarLS(lista){ localStorage.setItem(LS, JSON.stringify(lista)); listenersLS.forEach(cb => cb(lista.slice())); }

// última lista que llegó bien: permite seguir imprimiendo si después se corta la conexión
function guardarUltima(lista){ try{ localStorage.setItem(LS_ULTIMA, JSON.stringify({ cuando:Date.now(), lista })); }catch(e){} }
export function leerUltima(){
  try{ const c = JSON.parse(localStorage.getItem(LS_ULTIMA)); return c && Array.isArray(c.lista) ? c : null; }catch(e){ return null; }
}

const documentos = snap => snap.docs.map(d => ({ id:d.id, ...d.data() }));
const ESCUCHA_MS = 6000, LEER_MS = 8000, ESCRIBIR_MS = 12000, SONDEO_MS = 15000;

/* Escucha la lista compartida.
   Devuelve la función para cortar.
   `avisar({estado})` informa cómo va la conexión:
     ok          → en vivo (onSnapshot)
     sondeo      → el canal en vivo está bloqueado, pero la consulta simple funciona:
                   se refresca cada 15 segundos
     sin-conexion→ no se pudo leer nada (bloqueador, wifi caído): se entrega la última
                   copia guardada en esta computadora, si existe */
export async function escucharFiscales(cb, avisar){
  const informe = avisar || (() => {});
  if(modoPrueba){ listenersLS.push(cb); cb(leerLS()); informe({ estado:'ok' }); return () => {}; }
  informe({ estado:'conectando' });
  await cargarSdk();
  const q = fs.query(fs.collection(db, 'fiscales'), fs.orderBy('creadoEn', 'asc'));
  // getDocsFromServer: la consulta normal puede responder desde la copia en memoria y
  // devolver una lista vacía como si todo estuviera bien
  const leer = () => conLimite(fs.getDocsFromServer(q).then(documentos), LEER_MS);

  let cancelar = null, sondeo = null, cortado = false;
  const entregar = lista => { if(cortado) return; guardarUltima(lista); cb(lista); };

  // 1) intento en vivo
  const enVivo = await new Promise(resolver => {
    let resuelto = false, yaAnduvo = false, reloj = null;
    const fin = ok => { if(!resuelto){ resuelto = true; clearTimeout(reloj); resolver(ok); } };
    reloj = setTimeout(() => fin(false), ESCUCHA_MS);
    try{
      cancelar = fs.onSnapshot(q,
        snap => {
          // un snapshot "fromCache" es la copia local, no el servidor: si el canal está
          // bloqueado puede llegar uno vacío y parecer que todo anda
          if(snap.metadata && snap.metadata.fromCache) return;
          if(sondeo) return; yaAnduvo = true; entregar(documentos(snap)); fin(true);
        },
        () => { if(yaAnduvo) informe({ estado:'sin-conexion' }); fin(false); });
    }catch(e){ fin(false); }
  });

  if(enVivo){
    informe({ estado:'ok' });
    return () => { cortado = true; try{ cancelar && cancelar(); }catch(e){} };
  }

  // 2) el canal en vivo no anda: probar una consulta simple (otra ruta de red)
  cortado = false;
  try{ cancelar && cancelar(); }catch(e){}
  try{
    entregar(await leer());
    informe({ estado:'sondeo' });
    sondeo = setInterval(async () => {
      if(cortado) return;
      try{ entregar(await leer()); informe({ estado:'sondeo' }); }
      catch(e){ informe({ estado:'sin-conexion' }); }
    }, SONDEO_MS);
    return () => { cortado = true; clearInterval(sondeo); };
  }catch(e){
    const copia = leerUltima();
    if(copia) entregar(copia.lista);
    informe({ estado:'sin-conexion', copia });
    return () => { cortado = true; };
  }
}

// escribe con límite: si el guardado no se confirma, avisa en vez de quedar colgado
const escribir = promesa => conLimite(promesa, ESCRIBIR_MS);

export async function agregarFiscal(datos){
  if(modoPrueba){ const l = leerLS(); l.push({ id:'p' + Date.now() + Math.random().toString(36).slice(2,6), ...datos, creadoEn:Date.now() }); guardarLS(l); return; }
  await escribir(fs.addDoc(fs.collection(db, 'fiscales'), { ...datos, creadoEn:fs.serverTimestamp() }));
}
export async function editarFiscal(id, datos){
  if(modoPrueba){ guardarLS(leerLS().map(f => f.id === id ? { ...f, ...datos } : f)); return; }
  await escribir(fs.updateDoc(fs.doc(db, 'fiscales', id), datos));
}
export async function borrarFiscal(id){
  if(modoPrueba){ guardarLS(leerLS().filter(f => f.id !== id)); return; }
  await escribir(fs.deleteDoc(fs.doc(db, 'fiscales', id)));
}

// ---------- padrón de afiliados (consulta de a un DNI) ----------
// Devuelve "Apellido Nombre" o null si no está. En modo prueba no hay padrón.
export async function buscarPadron(dni){
  if(modoPrueba) return null;
  await cargarSdk();
  const s = await conLimite(fs.getDoc(fs.doc(db, 'padron', dni)), LEER_MS);
  return s.exists() ? s.data().n : null;
}

// ---------- diseño compartido ----------
// un documento por formulario: config/diseno (N°3 mesa) y config/diseno-general (N°2)
const docDiseno = modelo => modelo === 'general' ? 'diseno-general' : 'diseno';
export async function leerDiseno(modelo){
  if(modoPrueba){ try{ return JSON.parse(localStorage.getItem('cta-prueba-' + docDiseno(modelo))); }catch(e){ return null; } }
  await cargarSdk();
  const s = await conLimite(fs.getDoc(fs.doc(db, 'config', docDiseno(modelo))), LEER_MS);
  return s.exists() ? JSON.parse(s.data().json) : null;
}
export async function guardarDiseno(diseno, modelo){
  const json = JSON.stringify(diseno);
  if(modoPrueba){ localStorage.setItem('cta-prueba-' + docDiseno(modelo), json); return; }
  await cargarSdk();
  await escribir(fs.setDoc(fs.doc(db, 'config', docDiseno(modelo)), { json, actualizado:fs.serverTimestamp() }));
}
