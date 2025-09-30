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

  function signup(email, password, username, businessInfo = null) {
    return createUserWithEmailAndPassword(auth, email, password)
      .then((userCredential) => {
        // 사용자 프로필에 사용자명 추가
        return updateProfile(userCredential.user, {
          displayName: username
        }).then(() => {
          // 비즈니스 정보가 있으면 추가 정보와 함께 저장
          const userData = {
            user_id: userCredential.user.uid,
            email: userCredential.user.email,
            name: username
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
    return signOut(auth);
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
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setCurrentUser(user);
      
      if (user) {
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
        
        // 사용자 정보 localStorage 저장
        
        try {
          // 사용자 정보 저장 (기본 정보만)
          await smmpanelApi.registerUser({
            user_id: user.uid,
            email: user.email,
            name: user.displayName || ''
          });
          
          // 활동 업데이트는 현재 백엔드에서 지원하지 않으므로 제거
          // 필요시 나중에 구현 예정
        } catch (error) {
          // 오프라인 모드에서는 에러를 무시하고 계속 진행
        }
      } else {
        // 로그아웃 시 localStorage 정리
        localStorage.removeItem('userId');
        localStorage.removeItem('userEmail');
        localStorage.removeItem('firebase_user_id');
        localStorage.removeItem('firebase_user_email');
        localStorage.removeItem('currentUser');
      }
      
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const value = {
    currentUser,
    loading,
    signup,
    login,
    logout,
    updateProfile: updateUserProfile,
    deleteAccount
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
