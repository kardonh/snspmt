import React, { createContext, useContext, useState, useEffect } from 'react';
import smmpanelApi from '../services/snspopApi';

const AuthContext = createContext();

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [showOrderMethodModal, setShowOrderMethodModal] = useState(false);

  // localStorage에서 사용자 정보 복원
  useEffect(() => {
    const restoreUserFromStorage = () => {
      try {
        const userData = localStorage.getItem('currentUser');
        if (userData) {
          const parsedUser = JSON.parse(userData);
          if (parsedUser && parsedUser.uid && typeof parsedUser.uid === 'string') {
            setCurrentUser(parsedUser);
            console.log('🔄 localStorage에서 사용자 정보 복원:', parsedUser);
          } else {
            console.log('❌ 유효하지 않은 사용자 데이터, localStorage 클리어');
            localStorage.removeItem('currentUser');
            localStorage.removeItem('userId');
            localStorage.removeItem('firebase_user_id');
            localStorage.removeItem('userEmail');
            setCurrentUser(null);
          }
        }
      } catch (error) {
        console.error('❌ localStorage 파싱 오류:', error);
        localStorage.removeItem('currentUser');
        localStorage.removeItem('userId');
        localStorage.removeItem('firebase_user_id');
        localStorage.removeItem('userEmail');
        setCurrentUser(null);
      }
    };

    restoreUserFromStorage();
  }, []);

  // 회원가입 (이메일/비밀번호)
  function signup(email, password, username, businessInfo = null) {
    return new Promise((resolve, reject) => {
      // 간단한 유효성 검사
      if (!email || !password || !username) {
        reject(new Error('모든 필드를 입력해주세요.'));
        return;
      }

      // 사용자 ID 생성 (간단한 UUID 형태)
      const userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      
          const userData = {
        uid: userId,
        email: email,
        displayName: username,
        photoURL: null,
        user_id: userId,
        name: username,
        phoneNumber: businessInfo?.phoneNumber || ''
          };
          
          if (businessInfo && businessInfo.accountType === 'business') {
            Object.assign(userData, {
              accountType: businessInfo.accountType,
              businessNumber: businessInfo.businessNumber,
              businessName: businessInfo.businessName,
              representative: businessInfo.representative,
          businessAddress: businessInfo.businessAddress
        });
      }

      // localStorage에 저장
      localStorage.setItem('currentUser', JSON.stringify(userData));
      localStorage.setItem('userId', userId);
      localStorage.setItem('firebase_user_id', userId);
      localStorage.setItem('userEmail', email);
      
      setCurrentUser(userData);
      resolve(userData);
    });
  }

  // 로그인 (이메일/비밀번호)
  function login(email, password) {
    return new Promise(async (resolve, reject) => {
      try {
        // 서버에서 로그인 인증
        const response = await fetch(`${window.location.origin}/api/auth/login`, {
                method: 'POST',
                headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email, password })
        });

        if (response.ok) {
          const result = await response.json();
          const userData = result.user;
          
          // localStorage에 저장
          localStorage.setItem('currentUser', JSON.stringify(userData));
          localStorage.setItem('userId', userData.uid);
          localStorage.setItem('firebase_user_id', userData.uid);
          localStorage.setItem('userEmail', email);
          
          setCurrentUser(userData);
          resolve(userData);
        } else {
          const errorData = await response.json();
          reject(new Error(errorData.error || '로그인에 실패했습니다.'));
        }
      } catch (error) {
        console.error('로그인 오류:', error);
        reject(new Error('로그인 중 오류가 발생했습니다.'));
        }
      });
  }

  // 구글 로그인
  function googleLogin() {
    return new Promise(async (resolve, reject) => {
      try {
        // 런타임에 서버에서 환경 변수 가져오기
        const response = await fetch(`${window.location.origin}/api/config`);
        const config = await response.json();
        
        const googleClientId = config.googleClientId || 
                              process.env.REACT_APP_GOOGLE_CLIENT_ID ||
                              '123456789-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com';
        
        if (!googleClientId) {
          reject(new Error('Google Client ID가 설정되지 않았습니다.'));
          return;
        }
        
        // 구글 로그인 팝업
        const googleAuthUrl = `https://accounts.google.com/oauth/authorize?client_id=${googleClientId}&redirect_uri=${encodeURIComponent(window.location.origin)}&response_type=code&scope=openid%20email%20profile`;
        
        const popup = window.open(googleAuthUrl, 'googleAuth', 'width=500,height=600');
        
        if (!popup) {
          reject(new Error('팝업이 차단되었습니다. 팝업 차단을 해제해주세요.'));
          return;
        }
        
        // COOP 정책으로 인해 window.closed 사용 불가
        // 팝업에서 메시지를 받는 방식으로 변경
        const messageHandler = (event) => {
          if (event.origin !== window.location.origin) return;
          
          if (event.data.type === 'GOOGLE_AUTH_SUCCESS') {
            window.removeEventListener('message', messageHandler);
            clearInterval(checkClosed);
            resolve(event.data.user);
          } else if (event.data.type === 'GOOGLE_AUTH_ERROR') {
            window.removeEventListener('message', messageHandler);
            clearInterval(checkClosed);
            reject(new Error(event.data.error || '구글 로그인 실패'));
          }
        };
        
        window.addEventListener('message', messageHandler);
        
        // 30초 후 타임아웃
        const checkClosed = setTimeout(() => {
          window.removeEventListener('message', messageHandler);
          reject(new Error('구글 로그인 시간이 초과되었습니다.'));
        }, 30000);
      } catch (error) {
        reject(new Error('구글 로그인 초기화 중 오류가 발생했습니다.'));
      }
    });
  }

  // 카카오 로그인
  function kakaoLogin() {
    return new Promise((resolve, reject) => {
      // 카카오 로그인은 서버에서 처리되므로 여기서는 에러 반환
      reject(new Error('카카오 로그인은 서버에서 처리됩니다.'));
    });
  }

  // 로그아웃
  function logout() {
    return new Promise((resolve) => {
      localStorage.removeItem('currentUser');
      localStorage.removeItem('userId');
      localStorage.removeItem('firebase_user_id');
      localStorage.removeItem('userEmail');
      setCurrentUser(null);
      resolve();
    });
  }

  // 사용자 프로필 업데이트
  function updateUserProfile(updates) {
    if (currentUser) {
      const updatedUser = { ...currentUser, ...updates };
      setCurrentUser(updatedUser);
      localStorage.setItem('currentUser', JSON.stringify(updatedUser));
    }
  }

  // 계정 삭제
  function deleteAccount() {
    return new Promise((resolve) => {
      localStorage.removeItem('currentUser');
        localStorage.removeItem('userId');
      localStorage.removeItem('firebase_user_id');
        localStorage.removeItem('userEmail');
      setCurrentUser(null);
      resolve();
    });
  }

  // 모달 관련 함수들
  const openLoginModal = () => {
    setAuthModalMode('login');
    setShowAuthModal(true);
  };

  const openSignupModal = () => {
    setAuthModalMode('signup');
    setShowAuthModal(true);
  };

  const closeAuthModal = () => {
    setShowAuthModal(false);
  };

  const openOrderMethodModal = () => {
    setShowOrderMethodModal(true);
  };

  const closeOrderMethodModal = () => {
    setShowOrderMethodModal(false);
  };


  const value = {
    currentUser,
    loading,
    signup,
    login,
    logout,
    googleLogin,
    kakaoLogin,
    updateUserProfile,
    deleteAccount,
    showAuthModal,
    setShowAuthModal,
    authModalMode,
    openLoginModal,
    openSignupModal,
    closeAuthModal,
    showOrderMethodModal,
    setShowOrderMethodModal,
    openOrderMethodModal,
    closeOrderMethodModal
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}