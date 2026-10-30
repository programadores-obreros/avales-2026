// Configuración web de Firebase (proyecto cta-multicolor-2026). Son datos públicos por diseño:
// la seguridad la dan Firebase Auth + las reglas de Firestore (firestore.rules), no ocultar esto.
// Mientras FIREBASE_CONFIG esté vacío, la app funciona en MODO PRUEBA (todo local en el navegador).
export const FIREBASE_CONFIG = {
  apiKey: 'AIzaSyBnSWiJXMTLTjwlQKOjt7ARmD82dGgC5Co',
  authDomain: 'cta-multicolor-2026.firebaseapp.com',
  projectId: 'cta-multicolor-2026',
  storageBucket: 'cta-multicolor-2026.firebasestorage.app',
  messagingSenderId: '538150728820',
  appId: '1:538150728820:web:990af46ef1c6c2a0ef4d21'
};

// Cuenta única: la clave que escriben los docentes es la contraseña de esta cuenta.
export const CUENTA = 'constancias@ctamulticolor.com.ar';
