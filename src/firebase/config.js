// Firebase 설정
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getAnalytics } from 'firebase/analytics';

// Firebase 설정 - 환경 변수 우선, 없으면 기본값 사용
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyB8zSBVAJ1NsCxBaBClVBRlTt7k-uRebEg",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "snssmm-61f6c.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "snssmm-61f6c",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "snssmm-61f6c.appspot.com",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "474049215478",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:474049215478:web:d2460177482aaed45b65d7"
};

console.log('🔥 Firebase 설정:', {
  apiKey: firebaseConfig.apiKey ? `${firebaseConfig.apiKey.substring(0, 10)}...` : 'undefined',
  authDomain: firebaseConfig.authDomain,
  projectId: firebaseConfig.projectId
});

// Firebase 초기화
let app, auth, analytics;

try {
  app = initializeApp(firebaseConfig);
  auth = getAuth(app);
  
  // Analytics 초기화 (올바른 API 키로 정상 작동)
      analytics = getAnalytics(app);
  console.log('✅ Firebase 초기화 성공 (Analytics 포함)');
  } catch (error) {
  console.error('❌ Firebase 초기화 실패:', error);
  throw error;
}

export { app, analytics, auth };