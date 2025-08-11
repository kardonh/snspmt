// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyB8zSBVAJ1NsCxBaBClVBRlTt7k-uRebEg",
  authDomain: "snssmm-61f6c.firebaseapp.com",
  projectId: "snssmm-61f6c",
  storageBucket: "snssmm-61f6c.firebasestorage.app",
  messagingSenderId: "474049215478",
  appId: "1:474049215478:web:d2460177482aaed45b65d7",
  measurementId: "G-B577DN4V9Y"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = typeof window !== 'undefined' ? getAnalytics(app) : null;
const auth = getAuth(app);

export { app, analytics, auth };
