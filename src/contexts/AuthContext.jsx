import React, { createContext, useContext, useState, useEffect } from 'react';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged,
  updateProfile,
  deleteUser
} from 'firebase/auth';
import { auth } from '../firebase/config';
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
  const [loading, setLoading] = useState(true);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [showOrderMethodModal, setShowOrderMethodModal] = useState(false);

  function signup(email, password, username, businessInfo = null) {
    return createUserWithEmailAndPassword(auth, email, password)
      .then((userCredential) => {
        // 사용자 프로필에 사용자명 추가
        return updateProfile(userCredential.user, {
          displayName: username
        }).then(() => {
          // 사용자 정보 저장
          const userData = {
            user_id: userCredential.user.uid,
            email: userCredential.user.email,
            name: username || userCredential.user.email.split('@')[0] || '사용자',
            phoneNumber: businessInfo?.phoneNumber || '' // 개인/비즈니스 계정 모두 전화번호 저장
          };
          
          if (businessInfo && businessInfo.accountType === 'business') {
            Object.assign(userData, {
              accountType: businessInfo.accountType,
              businessNumber: businessInfo.businessNumber,
              businessName: businessInfo.businessName,
              representative: businessInfo.representative,
              contactPhone: businessInfo.contactPhone,
              contactEmail: businessInfo.contactEmail
            });
          }

          // 추천인 코드가 있으면 추가
          if (businessInfo && businessInfo.referralCode) {
            userData.referralCode = businessInfo.referralCode;
          }
          
          return smmpanelApi.registerUser(userData).then(() => {
            // 추천인 코드가 있으면 5% 할인 쿠폰 발급
            if (businessInfo && businessInfo.referralCode) {
              return fetch('/api/referral/issue-coupon', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  user_id: userCredential.user.uid,
                  referral_code: businessInfo.referralCode
                })
              }).then(response => {
                if (response.ok) {
                  return response.json();
                } else {
                  return response.json().then(errorData => {
                    throw new Error(`쿠폰 발급 실패: ${errorData.error || '알 수 없는 오류'}`);
                  });
                }
              }).catch(error => {
                // 쿠폰 발급 실패해도 회원가입은 계속 진행
                return Promise.resolve();
              });
            }
          });
        });
      })
      .catch(error => {
        if (error.code === 'auth/email-already-in-use') {
          throw new Error('이미 사용 중인 이메일입니다.');
        } else if (error.code === 'auth/weak-password') {
          throw new Error('비밀번호가 너무 약합니다. 6자 이상 입력해주세요.');
        } else if (error.code === 'auth/invalid-email') {
          throw new Error('유효하지 않은 이메일입니다.');
        } else if (error.code === 'auth/too-many-requests') {
          throw new Error('너무 많은 요청으로 인해 일시적으로 차단되었습니다.');
        } else if (error.code === 'auth/network-request-failed') {
          throw new Error('네트워크 연결을 확인해주세요.');
        } else {
          throw new Error('회원가입 중 오류가 발생했습니다: ' + error.message);
        }
      });
  }

  function login(email, password) {
    return signInWithEmailAndPassword(auth, email, password)
      .then((userCredential) => {
        return userCredential;
      })
      .catch(error => {
        
        // 오프라인 모드에서 네트워크 오류 처리
        if (error.code === 'auth/network-request-failed') {
          // 로컬에서 테스트용 더미 사용자 생성
          const dummyUser = {
            uid: 'dummy-user-id',
            email: email,
            displayName: '테스트 사용자'
          };
          setCurrentUser(dummyUser);
          return Promise.resolve({ user: dummyUser });
        }
        
        // Firebase 인증 오류 처리
        if (error.code === 'auth/user-not-found') {
          throw new Error('등록되지 않은 이메일입니다.');
        } else if (error.code === 'auth/wrong-password') {
          throw new Error('잘못된 비밀번호입니다.');
        } else if (error.code === 'auth/invalid-email') {
          throw new Error('유효하지 않은 이메일입니다.');
        } else if (error.code === 'auth/too-many-requests') {
          throw new Error('너무 많은 로그인 시도로 인해 일시적으로 차단되었습니다.');
        } else {
          throw new Error('로그인 중 오류가 발생했습니다.');
        }
      });
  }

  function logout() {
    // localStorage 정리
    localStorage.removeItem('userId');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('firebase_user_id');
    localStorage.removeItem('firebase_user_email');
    localStorage.removeItem('currentUser');
    
    // 사용자 상태 초기화
    setCurrentUser(null);
    
    // Firebase 로그아웃
    return signOut(auth);
  }

  // 카카오 로그인 함수
  async function kakaoLogin(kakaoUserInfo) {
    try {
      const response = await fetch(`${window.location.origin}/api/auth/kakao-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          kakaoId: kakaoUserInfo.id,
          email: kakaoUserInfo.email,
          nickname: kakaoUserInfo.nickname,
          profileImage: kakaoUserInfo.profile_image,
          accessToken: kakaoUserInfo.access_token
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          // 카카오 로그인 성공 시 사용자 정보 설정
          setCurrentUser(data.user);
          return data.user;
        } else {
          throw new Error(data.message || '카카오 로그인에 실패했습니다.');
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.message || '카카오 로그인에 실패했습니다.');
      }
    } catch (error) {
      console.error('카카오 로그인 오류:', error);
      throw error;
    }
  }

  // 구글 로그인 함수
  async function googleLogin(googleUserInfo) {
    try {
      console.log('구글 로그인 요청 시작:', googleUserInfo);
      
      const response = await fetch('/api/auth/google-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          googleId: googleUserInfo.uid,
          email: googleUserInfo.email,
          displayName: googleUserInfo.displayName,
          photoURL: googleUserInfo.photoURL,
          emailVerified: googleUserInfo.emailVerified,
          accessToken: googleUserInfo.accessToken
        }),
      });

      console.log('구글 로그인 응답 상태:', response.status, response.statusText);

      // 응답 텍스트를 먼저 확인
      const responseText = await response.text();
      console.log('구글 로그인 응답 텍스트:', responseText);

      if (response.ok) {
        try {
          const data = JSON.parse(responseText);
          if (data.success) {
            // 구글 로그인 성공 시 사용자 정보 설정
            setCurrentUser(data.user);
            return data.user;
          } else {
            throw new Error(data.message || '구글 로그인에 실패했습니다.');
          }
        } catch (parseError) {
          console.error('JSON 파싱 오류:', parseError);
          throw new Error('서버 응답을 처리할 수 없습니다.');
        }
      } else {
        try {
          const errorData = JSON.parse(responseText);
          throw new Error(errorData.message || `구글 로그인에 실패했습니다. (${response.status})`);
        } catch (parseError) {
          console.error('오류 응답 JSON 파싱 오류:', parseError);
          throw new Error(`구글 로그인에 실패했습니다. (${response.status}: ${response.statusText})`);
        }
      }
    } catch (error) {
      console.error('구글 로그인 오류:', error);
      throw error;
    }
  }

  function updateUserProfile(updates) {
    if (!currentUser) {
      throw new Error('사용자가 로그인되지 않았습니다.');
    }
    return updateProfile(currentUser, updates);
  }

  function deleteAccount() {
    if (!currentUser) {
      throw new Error('사용자가 로그인되지 않았습니다.');
    }
    return deleteUser(currentUser);
  }

  useEffect(() => {
    let isInitialized = false;
    
    // 페이지 로드 시 localStorage에서 사용자 정보 복원
    const restoreUserFromStorage = () => {
      try {
        const storedUser = localStorage.getItem('currentUser');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          console.log('🔄 localStorage에서 사용자 정보 복원:', userData);
          setCurrentUser(userData);
          setLoading(false);
          isInitialized = true;
          return true;
        }
      } catch (error) {
        console.error('사용자 정보 복원 실패:', error);
      }
      return false;
    };

    // 먼저 localStorage에서 사용자 정보 복원 시도
    const userRestored = restoreUserFromStorage();

    // Firebase 인증 상태 변경 리스너
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      // 이미 localStorage에서 복원된 경우 Firebase 상태 변경 무시
      if (isInitialized && userRestored) {
        console.log('🔄 localStorage에서 이미 복원됨, Firebase 상태 변경 무시');
        return;
      }
      
      if (user) {
        // Firebase 인증된 사용자 정보로 업데이트
        setCurrentUser(user);
        
        // 사용자 정보를 localStorage에 저장
        localStorage.setItem('userId', user.uid);
        localStorage.setItem('userEmail', user.email);
        localStorage.setItem('firebase_user_id', user.uid);
        localStorage.setItem('firebase_user_email', user.email);
        localStorage.setItem('currentUser', JSON.stringify({
          uid: user.uid,
          email: user.email,
          displayName: user.displayName
        }));
        
        try {
          // 사용자 정보 저장 (기본 정보만)
          await smmpanelApi.registerUser({
            user_id: user.uid,
            email: user.email,
            name: user.displayName || user.email.split('@')[0] || '사용자'
          });
        } catch (error) {
          // 오프라인 모드에서는 에러를 무시하고 계속 진행
        }
      } else {
        // Firebase 인증이 없을 때만 로그아웃 처리
        if (!userRestored) {
          setCurrentUser(null);
          // 로그아웃 시 localStorage 정리
          localStorage.removeItem('userId');
          localStorage.removeItem('userEmail');
          localStorage.removeItem('firebase_user_id');
          localStorage.removeItem('firebase_user_email');
          localStorage.removeItem('currentUser');
        }
      }
      
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const openSignupModal = () => {
    setAuthModalMode('signup');
    setShowAuthModal(true);
  };

  const openLoginModal = () => {
    setAuthModalMode('login');
    setShowAuthModal(true);
  };

  const value = {
    currentUser,
    loading,
    signup,
    login,
    logout,
    kakaoLogin,
    googleLogin,
    updateProfile: updateUserProfile,
    deleteAccount,
    showAuthModal,
    setShowAuthModal,
    authModalMode,
    openSignupModal,
    openLoginModal,
    showOrderMethodModal,
    setShowOrderMethodModal
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
