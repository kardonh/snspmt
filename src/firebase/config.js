// Firebase 설정
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getAnalytics } from 'firebase/analytics';

// Firebase 설정
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyB8zSBVAJ1NsCxBaBCIVBRITt7k-uRebEg",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "snssmm-61f6c.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "snssmm-61f6c",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "snssmm-61f6c.appspot.com",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "474049215478",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:474049215478:web:d2460177482aaed45b65d7"
};

// Firebase 초기화
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const analytics = getAnalytics(app);

export { app, analytics, auth };