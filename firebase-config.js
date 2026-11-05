window.firebaseConfig = {
  apiKey: "AIzaSyB2mWSP7MhvPWJGc-6Jd2FaduIkefutx2M",
  authDomain: "empleados-cbf0b.firebaseapp.com",
  projectId: "empleados-cbf0b",
  storageBucket: "empleados-cbf0b.firebasestorage.app",
  messagingSenderId: "442268839211",
  appId: "1:442268839211:web:0245c5cbe0e99c3749696e",
  measurementId: "G-BTWSJ1837X"
};

if (window.firebase && !window.firebase.apps.length) {
  window.firebase.initializeApp(window.firebaseConfig);
}
