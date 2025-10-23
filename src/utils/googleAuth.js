// 구글 로그인 유틸리티 (Firebase 의존성 제거됨)
// 이 파일은 더 이상 사용되지 않습니다.
// AuthContext에서 직접 처리합니다.

class GoogleAuth {
  constructor() {
    console.warn('GoogleAuth는 더 이상 사용되지 않습니다. AuthContext를 사용하세요.');
  }

  async login() {
    throw new Error('GoogleAuth는 더 이상 사용되지 않습니다. AuthContext.googleLogin()을 사용하세요.');
  }

  async logout() {
    throw new Error('GoogleAuth는 더 이상 사용되지 않습니다. AuthContext.logout()을 사용하세요.');
  }

  getCurrentUser() {
    return null;
  }

  onAuthStateChanged(callback) {
    console.warn('GoogleAuth는 더 이상 사용되지 않습니다.');
    return () => {};
  }

  async getToken() {
    return null;
  }
}

const googleAuth = new GoogleAuth();
export default googleAuth;