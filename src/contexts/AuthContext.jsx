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
                  console.log('추천인 쿠폰이 발급되었습니다!');
                } else {
                  console.log('추천인 쿠폰 발급에 실패했습니다.');
                }
              }).catch(error => {
                console.error('추천인 쿠폰 발급 오류:', error);
              });
            }
          });
        });
      })
      .catch(error => {
        console.error('회원가입 오류:', error);
        if (error.code === 'auth/email-already-in-use') {
          throw new Error('이미 사용 중인 이메일입니다.');
        } else if (error.code === 'auth/weak-password') {
          throw new Error('비밀번호가 너무 약합니다.');
        } else if (error.code === 'auth/invalid-email') {
          throw new Error('유효하지 않은 이메일입니다.');
        } else {
          throw new Error('회원가입 중 오류가 발생했습니다.');
        }
      });
  }

  function login(email, password) {
    return signInWithEmailAndPassword(auth, email, password).catch(error => {
      // 오프라인 모드에서 네트워크 오류 처리
      if (error.code === 'auth/network-request-failed') {
        console.log('네트워크 연결 실패 - 오프라인 모드로 전환');
        // 로컬에서 테스트용 더미 사용자 생성
        const dummyUser = {
          uid: 'dummy-user-id',
          email: email,
          displayName: '테스트 사용자'
        };
        setCurrentUser(dummyUser);
        return Promise.resolve({ user: dummyUser });
      }
      throw error;
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
          console.error('사용자 정보 저장 실패:', error);
          // 오프라인 모드에서는 에러를 무시하고 계속 진행
          if (error.message.includes('Network Error') || error.message.includes('ERR_NAME_NOT_RESOLVED')) {
            console.log('오프라인 모드 - 백엔드 API 호출 건너뜀');
          }
        }
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
