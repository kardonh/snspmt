// 구글 로그인 유틸리티 (Firebase Auth 사용)
import { 
  signInWithPopup, 
  GoogleAuthProvider, 
  signOut,
  onAuthStateChanged 
} from 'firebase/auth';
import { auth } from '../firebase/config';

class GoogleAuth {
  constructor() {
    this.provider = new GoogleAuthProvider();
    this.isInitialized = false;
  }

  // 구글 로그인
  async login() {
    try {
      console.log('구글 로그인 시작...');
      
      // 구글 로그인 팝업 실행
      const result = await signInWithPopup(auth, this.provider);
      const user = result.user;
      
      console.log('구글 로그인 성공:', user);
      
      // 사용자 정보 추출
      const userInfo = {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        photoURL: user.photoURL,
        emailVerified: user.emailVerified,
        accessToken: await user.getIdToken()
      };
      
      return userInfo;
    } catch (error) {
      console.error('구글 로그인 오류:', error);
      
      // 구체적인 오류 메시지 제공
      let errorMessage = '구글 로그인 중 오류가 발생했습니다.';
      
      if (error.code === 'auth/popup-closed-by-user') {
        errorMessage = '구글 로그인이 취소되었습니다.';
      } else if (error.code === 'auth/popup-blocked') {
        errorMessage = '팝업이 차단되었습니다. 팝업을 허용해주세요.';
      } else if (error.code === 'auth/network-request-failed') {
        errorMessage = '네트워크 연결을 확인해주세요.';
      } else if (error.code === 'auth/too-many-requests') {
        errorMessage = '너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.';
      }
      
      throw new Error(errorMessage);
    }
  }

  // 구글 로그아웃
  async logout() {
    try {
      await signOut(auth);
      console.log('구글 로그아웃 완료');
    } catch (error) {
      console.error('구글 로그아웃 오류:', error);
      throw error;
    }
  }

  // 현재 사용자 정보 가져오기
  getCurrentUser() {
    return auth.currentUser;
  }

  // 인증 상태 변경 감지
  onAuthStateChanged(callback) {
    return onAuthStateChanged(auth, callback);
  }

  // 사용자 토큰 가져오기
  async getToken() {
    try {
      const user = auth.currentUser;
      if (user) {
        return await user.getIdToken();
      }
      return null;
    } catch (error) {
      console.error('토큰 가져오기 오류:', error);
      return null;
    }
  }
}

const googleAuth = new GoogleAuth();
export default googleAuth;
