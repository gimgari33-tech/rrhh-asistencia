// Copiá este archivo como firebase-config.js y completá los datos
// de configuración web de tu proyecto Firebase.
window.firebaseConfig = {
  apiKey: "REEMPLAZAR",
  authDomain: "REEMPLAZAR.firebaseapp.com",
  projectId: "REEMPLAZAR",
  storageBucket: "REEMPLAZAR.appspot.com",
  messagingSenderId: "REEMPLAZAR",
  appId: "REEMPLAZAR"
};

if (window.firebase && !window.firebase.apps.length) {
  window.firebase.initializeApp(window.firebaseConfig);
}
