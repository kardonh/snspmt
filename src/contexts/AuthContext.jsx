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
import { snspopApi } from '../services/snspopApi';

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
            userId: userCredential.user.uid,
            email: userCredential.user.email,
            displayName: username
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
          
          return snspopApi.registerUser(userData);
        });
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
          await snspopApi.registerUser({
            userId: user.uid,
            email: user.email,
            displayName: user.displayName || ''
          });
          
          // 로그인 기록
          await smmkingsApi.userLogin(user.uid);
          
          // 주기적으로 활동 업데이트 (30분마다로 최적화)
          const activityInterval = setInterval(async () => {
            try {
              await smmkingsApi.updateUserActivity(user.uid);
            } catch (error) {
              console.error('활동 업데이트 실패:', error);
            }
          }, 30 * 60 * 1000); // 30분으로 최적화
          
          // 컴포넌트 언마운트 시 인터벌 정리
          return () => clearInterval(activityInterval);
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
