// 카카오 로그인 유틸리티
class KakaoAuth {
  constructor() {
    this.isInitialized = false;
    // 카카오 개발자 콘솔에서 발급받은 JavaScript 키를 입력하세요
    // Vite에서는 import.meta.env를 사용합니다
    this.APP_KEY = import.meta.env.VITE_KAKAO_APP_KEY || '5a6e0106e9beafa7bd8199ab3c378ceb'; // JavaScript 키
  }


  // 카카오 SDK 로딩 대기
  async waitForKakaoSDK() {
    return new Promise((resolve, reject) => {
      let attempts = 0;
      const maxAttempts = 50; // 5초 대기
      
      const checkKakao = () => {
        attempts++;
        
        if (typeof window !== 'undefined' && window.Kakao) {
          console.log('카카오 SDK 로딩 완료');
          resolve();
        } else if (attempts >= maxAttempts) {
          console.error('카카오 SDK 로딩 실패:', { 
            window: typeof window, 
            Kakao: typeof window?.Kakao,
            attempts 
          });
          reject(new Error('카카오 SDK 로딩 시간 초과. 페이지를 새로고침해주세요.'));
        } else {
          setTimeout(checkKakao, 100);
        }
      };
      
      checkKakao();
    });
  }

  // 카카오 SDK 초기화
  async init() {
    if (this.isInitialized) return;
    
    // 카카오 SDK 로딩 대기
    await this.waitForKakaoSDK();
    
    if (!window.Kakao.isInitialized()) {
      window.Kakao.init(this.APP_KEY);
      this.isInitialized = true;
      console.log('카카오 SDK 초기화 완료');
    }
  }

  // 카카오 로그인
  async login() {
    try {
      await this.init();
      
      // 카카오 공식 문서에 따른 authorize 방식 사용
      // 이 방식은 리다이렉트를 통해 처리됩니다
      const redirectUri = window.location.origin + '/kakao-callback';
      console.log('카카오 로그인 Redirect URI:', redirectUri);
      
      // 카카오 로그인 페이지로 리다이렉트
      window.Kakao.Auth.authorize({
        redirectUri: redirectUri
      });
      
      // 리다이렉트가 시작되므로 여기서는 성공으로 처리
      console.log('카카오 로그인 리다이렉트 시작');
      return { success: true, message: '카카오 로그인 페이지로 이동합니다.' };
      
    } catch (error) {
      console.error('카카오 로그인 오류:', error);
      throw error;
    }
  }

  // 사용자 정보 가져오기
  async getUserInfo(accessToken) {
    try {
      await this.init();
      
      return new Promise((resolve, reject) => {
        window.Kakao.API.request({
          url: '/v2/user/me',
          success: (response) => {
            console.log('카카오 사용자 정보:', response);
            const userInfo = {
              id: response.id,
              email: response.kakao_account?.email,
              nickname: response.kakao_account?.profile?.nickname,
              profile_image: response.kakao_account?.profile?.profile_image_url,
              access_token: accessToken,
              provider: 'kakao'
            };
            resolve(userInfo);
          },
          fail: (err) => {
            console.error('카카오 사용자 정보 조회 실패:', err);
            reject(err);
          }
        });
      });
    } catch (error) {
      console.error('카카오 사용자 정보 조회 오류:', error);
      throw error;
    }
  }

  // 카카오 로그아웃
  async logout() {
    try {
      await this.init();
      
      if (window.Kakao.Auth.getAccessToken()) {
        window.Kakao.Auth.logout(() => {
          console.log('카카오 로그아웃 완료');
        });
      }
    } catch (error) {
      console.error('카카오 로그아웃 오류:', error);
    }
  }

  // 로그인 상태 확인
  async isLoggedIn() {
    try {
      await this.init();
      return !!window.Kakao.Auth.getAccessToken();
    } catch (error) {
      console.error('카카오 로그인 상태 확인 오류:', error);
      return false;
    }
  }
}

export default new KakaoAuth();
