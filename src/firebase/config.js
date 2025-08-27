// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";
import { getAuth, connectAuthEmulator } from "firebase/auth";

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Analytics 초기화 (오프라인 모드 지원)
let analytics = null;
const initializeAnalytics = async () => {
  try {
    const analyticsSupported = await isSupported();
    if (analyticsSupported) {
      analytics = getAnalytics(app);
    }
  } catch (error) {
    console.log('Analytics 초기화 실패 (오프라인 모드):', error.message);
  }
};

// 개발 환경에서 Firebase Auth 에뮬레이터 연결 (선택사항)
if (import.meta.env.DEV && window.location.hostname === 'localhost') {
  try {
    // connectAuthEmulator(auth, 'http://localhost:9099');
    console.log('Firebase Auth 에뮬레이터 연결 준비됨 (포트 9099)');
  } catch (error) {
    console.log('Firebase Auth 에뮬레이터 연결 실패:', error.message);
  }
}

// Analytics 초기화
initializeAnalytics();

export { app, analytics, auth };
