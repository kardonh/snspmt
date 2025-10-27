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

  // localStorage 기반 인증 상태 복원
  useEffect(() => {
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
      try {
        const userData = JSON.parse(savedUser);
        setCurrentUser(userData);
        console.log('✅ 사용자 정보 복원:', userData);
      } catch (error) {
        console.error('❌ 사용자 정보 파싱 오류:', error);
        localStorage.removeItem('currentUser');
      }
    }
  }, []);

  // 회원가입 (이메일/비밀번호) - localStorage 기반
  function signup(email, password, username, businessInfo = null) {
    return new Promise((resolve, reject) => {
      if (!email || !password || !username) {
        reject(new Error('모든 필드를 입력해주세요.'));
        return;
      }

      // 간단한 사용자 ID 생성
      const userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      const userData = {
        uid: userId,
        email: email,
        displayName: username,
        photoURL: null,
        provider: 'local',
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

  // 로그인 (이메일/비밀번호) - localStorage 기반
  function login(email, password) {
    return new Promise((resolve, reject) => {
      if (!email || !password) {
        reject(new Error('이메일과 비밀번호를 입력해주세요.'));
        return;
      }

      // 간단한 사용자 ID 생성 (실제로는 서버에서 검증해야 함)
      const userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      const userData = {
        uid: userId,
        email: email,
        displayName: email.split('@')[0], // 이메일에서 사용자명 추출
        photoURL: null,
        provider: 'local'
      };

      localStorage.setItem('currentUser', JSON.stringify(userData));
      localStorage.setItem('userId', userId);
      localStorage.setItem('firebase_user_id', userId);
      localStorage.setItem('userEmail', email);
      
      setCurrentUser(userData);
      resolve(userData);
    });
  }

  // 구글 로그인 - 팝업 기반
  function googleLogin() {
    return new Promise((resolve, reject) => {
      try {
        // 구글 로그인 팝업 열기
        const popup = window.open(
          `https://accounts.google.com/oauth/authorize?client_id=${process.env.REACT_APP_GOOGLE_CLIENT_ID}&redirect_uri=${encodeURIComponent(window.location.origin + '/api/auth/google-callback')}&response_type=code&scope=email profile`,
          'google-login',
          'width=500,height=600,scrollbars=yes,resizable=yes'
        );

        if (!popup) {
          reject(new Error('팝업이 차단되었습니다. 팝업 차단을 해제해주세요.'));
          return;
        }

        // 팝업에서 메시지 수신 대기
        const messageHandler = (event) => {
          if (event.origin !== window.location.origin) return;
          
          if (event.data.type === 'GOOGLE_LOGIN_SUCCESS') {
            const userData = event.data.user;
            
            localStorage.setItem('currentUser', JSON.stringify(userData));
            localStorage.setItem('userId', userData.uid);
            localStorage.setItem('firebase_user_id', userData.uid);
            localStorage.setItem('userEmail', userData.email);
            
            setCurrentUser(userData);
            window.removeEventListener('message', messageHandler);
            popup.close();
            resolve(userData);
          } else if (event.data.type === 'GOOGLE_LOGIN_ERROR') {
            window.removeEventListener('message', messageHandler);
            popup.close();
            reject(new Error(event.data.error));
          }
        };

        window.addEventListener('message', messageHandler);

        // 팝업 타임아웃
        setTimeout(() => {
          window.removeEventListener('message', messageHandler);
          if (!popup.closed) {
            popup.close();
            reject(new Error('로그인 시간이 초과되었습니다.'));
          }
        }, 60000); // 60초

      } catch (error) {
        console.error('구글 로그인 오류:', error);
        reject(new Error('구글 로그인 초기화 중 오류가 발생했습니다.'));
      }
    });
  }

  // 카카오 로그인
  function kakaoLogin() {
    return new Promise((resolve, reject) => {
      try {
        // 카카오 SDK가 로드되었는지 확인
        if (!window.Kakao || !window.Kakao.Auth) {
          reject(new Error('카카오 SDK가 로드되지 않았습니다.'));
          return;
        }

        // 카카오 로그인 페이지로 리다이렉트
        const redirectUri = window.location.origin + '/kakao-callback';
        window.Kakao.Auth.authorize({
          redirectUri: redirectUri
        });

        // 리다이렉트가 시작되므로 성공으로 처리
        resolve({ success: true, message: '카카오 로그인 페이지로 이동합니다.' });
      } catch (error) {
        console.error('카카오 로그인 오류:', error);
        reject(new Error('카카오 로그인 초기화 중 오류가 발생했습니다.'));
      }
    });
  }

  // 로그아웃 - localStorage 기반
  function logout() {
    return new Promise((resolve) => {
      // localStorage 정리
      localStorage.removeItem('currentUser');
      localStorage.removeItem('userId');
      localStorage.removeItem('firebase_user_id');
      localStorage.removeItem('userEmail');
      
      // 상태 초기화
      setCurrentUser(null);
      
      console.log('✅ 로그아웃 완료');
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
    setCurrentUser,
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