/* Acceso a datos de las constancias.
   - Con firebase-config.js completo: la clave inicia sesión en la cuenta única de Firebase Auth
     y la lista de fiscales vive en Firestore (las reglas solo responden a esa cuenta).
   - Sin configurar: MODO PRUEBA, todo queda en este navegador (localStorage). Solo para probar. */
import { FIREBASE_CONFIG, CUENTA } from './firebase-config.js';

const SDK = 'https://www.gstatic.com/firebasejs/10.14.1/';
export const modoPrueba = !FIREBASE_CONFIG || !FIREBASE_CONFIG.apiKey;

let auth, db, fs, fa;

async function cargarSdk(){
  if(fs) return;
  const [app, a, f] = await Promise.all([import(SDK + 'firebase-app.js'), import(SDK + 'firebase-auth.js'), import(SDK + 'firebase-firestore.js')]);
  const fb = app.initializeApp(FIREBASE_CONFIG);
  fa = a; fs = f;
  auth = a.getAuth(fb);
  await a.setPersistence(auth, a.browserLocalPersistence);
  db = f.getFirestore(fb);
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
  await fa.signInWithEmailAndPassword(auth, CUENTA, clave);
}
export async function salir(){
  if(modoPrueba){ sessionStorage.removeItem('cta-prueba-ok'); return; }
  await fa.signOut(auth);
}

// ---------- fiscales ----------
const LS = 'cta-prueba-fiscales';
const leerLS = () => { try{ return JSON.parse(localStorage.getItem(LS)) || []; }catch(e){ return []; } };
const listenersLS = [];
function guardarLS(lista){ localStorage.setItem(LS, JSON.stringify(lista)); listenersLS.forEach(cb => cb(lista.slice())); }

export async function escucharFiscales(cb){
  if(modoPrueba){ listenersLS.push(cb); cb(leerLS()); return () => {}; }
  await cargarSdk();
  const q = fs.query(fs.collection(db, 'fiscales'), fs.orderBy('creadoEn', 'asc'));
  return fs.onSnapshot(q, snap => cb(snap.docs.map(d => ({ id:d.id, ...d.data() }))));
}
export async function agregarFiscal(datos){
  if(modoPrueba){ const l = leerLS(); l.push({ id:'p' + Date.now() + Math.random().toString(36).slice(2,6), ...datos, creadoEn:Date.now() }); guardarLS(l); return; }
  await fs.addDoc(fs.collection(db, 'fiscales'), { ...datos, creadoEn:fs.serverTimestamp() });
}
export async function editarFiscal(id, datos){
  if(modoPrueba){ guardarLS(leerLS().map(f => f.id === id ? { ...f, ...datos } : f)); return; }
  await fs.updateDoc(fs.doc(db, 'fiscales', id), datos);
}
export async function borrarFiscal(id){
  if(modoPrueba){ guardarLS(leerLS().filter(f => f.id !== id)); return; }
  await fs.deleteDoc(fs.doc(db, 'fiscales', id));
}

// ---------- padrón de afiliados (consulta de a un DNI) ----------
// Devuelve "Apellido Nombre" o null si no está. En modo prueba no hay padrón.
export async function buscarPadron(dni){
  if(modoPrueba) return null;
  await cargarSdk();
  const s = await fs.getDoc(fs.doc(db, 'padron', dni));
  return s.exists() ? s.data().n : null;
}

// ---------- diseño compartido ----------
const LS_DISENO = 'cta-prueba-diseno';
export async function leerDiseno(){
  if(modoPrueba){ try{ return JSON.parse(localStorage.getItem(LS_DISENO)); }catch(e){ return null; } }
  await cargarSdk();
  const s = await fs.getDoc(fs.doc(db, 'config', 'diseno'));
  return s.exists() ? JSON.parse(s.data().json) : null;
}
export async function guardarDiseno(diseno){
  const json = JSON.stringify(diseno);
  if(modoPrueba){ localStorage.setItem(LS_DISENO, json); return; }
  await cargarSdk();
  await fs.setDoc(fs.doc(db, 'config', 'diseno'), { json, actualizado:fs.serverTimestamp() });
}
