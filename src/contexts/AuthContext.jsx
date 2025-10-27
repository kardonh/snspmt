import React, { createContext, useContext, useState, useEffect } from 'react';
import smmpanelApi from '../services/snspopApi';
import { auth } from '../firebase/config';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup,
  updateProfile
} from 'firebase/auth';

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

  // Firebase 인증 상태 감지
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        // Firebase 사용자 정보를 현재 사용자로 설정
        const userData = {
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
          photoURL: user.photoURL,
          provider: user.providerData[0]?.providerId || 'firebase'
        };
        
        setCurrentUser(userData);
        
        // localStorage에도 저장
        localStorage.setItem('currentUser', JSON.stringify(userData));
        localStorage.setItem('userId', user.uid);
        localStorage.setItem('firebase_user_id', user.uid);
        localStorage.setItem('userEmail', user.email);
        
        console.log('🔥 Firebase 사용자 로그인:', userData);
      } else {
        // 로그아웃 상태
        setCurrentUser(null);
        localStorage.removeItem('currentUser');
        localStorage.removeItem('userId');
        localStorage.removeItem('firebase_user_id');
        localStorage.removeItem('userEmail');
        
        console.log('🔥 Firebase 사용자 로그아웃');
      }
    });

    return () => unsubscribe();
  }, []);

  // 회원가입 (이메일/비밀번호)
  function signup(email, password, username, businessInfo = null) {
    return new Promise((resolve, reject) => {
      if (!email || !password || !username) {
        reject(new Error('모든 필드를 입력해주세요.'));
        return;
      }

      createUserWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
          const user = userCredential.user;
          
          // 사용자 프로필 업데이트
          return updateProfile(user, {
            displayName: username,
            photoURL: null
          }).then(() => {
            // 추가 사용자 정보를 localStorage에 저장
            const userData = {
              uid: user.uid,
              email: user.email,
              displayName: username,
              photoURL: null,
              provider: 'firebase',
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

            localStorage.setItem('currentUser', JSON.stringify(userData));
            localStorage.setItem('userId', user.uid);
            localStorage.setItem('firebase_user_id', user.uid);
            localStorage.setItem('userEmail', user.email);
            
            resolve(userData);
          });
        })
        .catch((error) => {
          console.error('회원가입 오류:', error);
          reject(new Error(error.message));
        });
    });
  }

  // 로그인 (이메일/비밀번호)
  function login(email, password) {
    return new Promise((resolve, reject) => {
      if (!email || !password) {
        reject(new Error('이메일과 비밀번호를 입력해주세요.'));
        return;
      }

      signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
          const user = userCredential.user;
          
          const userData = {
            uid: user.uid,
            email: user.email,
            displayName: user.displayName,
            photoURL: user.photoURL,
            provider: 'firebase'
          };

          localStorage.setItem('currentUser', JSON.stringify(userData));
          localStorage.setItem('userId', user.uid);
          localStorage.setItem('firebase_user_id', user.uid);
          localStorage.setItem('userEmail', user.email);
          
          resolve(userData);
        })
        .catch((error) => {
          console.error('로그인 오류:', error);
          reject(new Error(error.message));
        });
    });
  }

  // 구글 로그인
  function googleLogin() {
    return new Promise((resolve, reject) => {
      const provider = new GoogleAuthProvider();
      
      signInWithPopup(auth, provider)
        .then((result) => {
          const user = result.user;
          
          const userData = {
            uid: user.uid,
            email: user.email,
            displayName: user.displayName,
            photoURL: user.photoURL,
            provider: 'google.com'
          };

          localStorage.setItem('currentUser', JSON.stringify(userData));
          localStorage.setItem('userId', user.uid);
          localStorage.setItem('firebase_user_id', user.uid);
          localStorage.setItem('userEmail', user.email);
          
          resolve(userData);
        })
        .catch((error) => {
          console.error('구글 로그인 오류:', error);
          reject(new Error(error.message));
        });
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

  // 로그아웃
  function logout() {
    return new Promise((resolve) => {
      signOut(auth)
        .then(() => {
          localStorage.removeItem('currentUser');
          localStorage.removeItem('userId');
          localStorage.removeItem('firebase_user_id');
          localStorage.removeItem('userEmail');
          setCurrentUser(null);
          resolve();
        })
        .catch((error) => {
          console.error('로그아웃 오류:', error);
          // 에러가 있어도 로컬 상태는 정리
          localStorage.removeItem('currentUser');
          localStorage.removeItem('userId');
          localStorage.removeItem('firebase_user_id');
          localStorage.removeItem('userEmail');
          setCurrentUser(null);
          resolve();
        });
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