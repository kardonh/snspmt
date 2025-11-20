import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../supabase/client';

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

  // 사용자 세션 처리 및 백엔드 동기화
  const handleUserSession = async (user) => {
    try {
      const userData = {
        uid: user.id,
        email: user.email,
        displayName: user.user_metadata?.display_name || user.user_metadata?.full_name || user.email?.split('@')[0] || '사용자',
        photoURL: user.user_metadata?.avatar_url || null,
        provider: user.app_metadata?.provider || 'email'
      };

      setCurrentUser(userData);
      
      // localStorage에 저장
      localStorage.setItem('currentUser', JSON.stringify(userData));
      localStorage.setItem('userId', user.id);
      localStorage.setItem('userEmail', user.email);
      
      // 백엔드에 사용자 정보 동기화
      try {
        const session = await supabase.auth.getSession();
        const accessToken = session.data?.session?.access_token;
        
        // 전화번호, 추천인 코드, 가입 경로 정보 추출
        const phoneNumber = user.user_metadata?.phone_number || user.user_metadata?.contactPhone || null;
        const referralCode = user.user_metadata?.referral_code || null;
        const signupSource = user.user_metadata?.signup_source || null;
        
        const response = await fetch('/api/users/sync', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(accessToken && { 'Authorization': `Bearer ${accessToken}` })
          },
          body: JSON.stringify({
            user_id: user.id,
            email: user.email,
            username: user.user_metadata?.display_name || user.user_metadata?.full_name || user.email?.split('@')[0] || '사용자',
            phone_number: phoneNumber,
            referral_code: referralCode,
            signup_source: signupSource,
            metadata: user.user_metadata
          })
        });
        
        if (response.ok) {
          const result = await response.json();
          console.log('✅ 백엔드 사용자 동기화 성공:', result);
        } else {
          const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
          console.warn('⚠️ 백엔드 사용자 동기화 실패:', response.status, errorData);
          // 동기화 실패해도 로그인은 계속 진행 (Supabase 인증은 성공했으므로)
        }
      } catch (syncError) {
        console.warn('⚠️ 백엔드 사용자 동기화 오류 (계속 진행):', syncError);
        // 동기화 실패해도 로그인은 계속 진행
      }
      
      setLoading(false);
      console.log('✅ 사용자 세션 설정 완료:', userData);
    } catch (error) {
      console.error('❌ 사용자 세션 처리 오류:', error);
      setLoading(false);
    }
  };

  // Supabase 인증 상태 감지
  useEffect(() => {
    let mounted = true;
    
    // 초기 세션 확인 (타임아웃 포함)
    const checkInitialSession = async () => {
      try {
        // 타임아웃 설정: 3초 내에 응답이 없으면 로딩 종료
        let timeoutId;
        const timeoutPromise = new Promise((_, reject) => {
          timeoutId = setTimeout(() => reject(new Error('세션 확인 타임아웃')), 3000);
        });
        
        const sessionPromise = supabase.auth.getSession().then((result) => {
          if (timeoutId) clearTimeout(timeoutId);
          return result;
        });
        
        let sessionResult;
        try {
          sessionResult = await Promise.race([sessionPromise, timeoutPromise]);
        } catch (timeoutError) {
          // 타임아웃 발생
          console.warn('⚠️ 세션 확인 타임아웃:', timeoutError.message);
          // 타임아웃 시 localStorage 확인
          const storedUser = localStorage.getItem('currentUser');
          if (storedUser) {
            try {
              const userData = JSON.parse(storedUser);
              console.log('📦 타임아웃: localStorage 사용자 정보 사용', userData);
              if (mounted) {
                setCurrentUser(userData);
                setLoading(false);
              }
              return;
            } catch (e) {
              console.error('❌ localStorage 파싱 오류:', e);
            }
          }
          if (mounted) {
            setCurrentUser(null);
            setLoading(false);
          }
          return;
        }
        
        const { data: { session }, error } = sessionResult || { data: { session: null }, error: null };
        
        if (error) {
          console.error('❌ 세션 확인 오류:', error);
          if (mounted) {
            // 오류 시 localStorage 확인
            const storedUser = localStorage.getItem('currentUser');
            if (storedUser) {
              try {
                const userData = JSON.parse(storedUser);
                console.log('📦 오류: localStorage 사용자 정보 사용', userData);
                setCurrentUser(userData);
              } catch (e) {
                setCurrentUser(null);
              }
            } else {
              setCurrentUser(null);
            }
            setLoading(false);
          }
          return;
        }
        
        if (mounted) {
          if (session?.user) {
            console.log('✅ 초기 세션 발견:', session.user.id);
            await handleUserSession(session.user);
          } else {
            console.log('ℹ️ 초기 세션 없음 - 로그아웃 상태로 설정');
            // Supabase 세션이 없으면 localStorage 정보도 무시하고 정리
            const storedUser = localStorage.getItem('currentUser');
            if (storedUser) {
              console.log('📦 저장된 사용자 정보 발견, 하지만 Supabase 세션 없음 - 정리');
              localStorage.removeItem('currentUser');
              localStorage.removeItem('userId');
              localStorage.removeItem('userEmail');
              localStorage.removeItem('supabase_access_token');
            }
            setCurrentUser(null);
            setLoading(false);
          }
        }
      } catch (error) {
        console.error('❌ 초기 세션 확인 오류:', error);
        if (mounted) {
          // 오류 시 localStorage 확인
          const storedUser = localStorage.getItem('currentUser');
          if (storedUser) {
            try {
              const userData = JSON.parse(storedUser);
              console.log('📦 오류: localStorage 사용자 정보 사용', userData);
              setCurrentUser(userData);
            } catch (e) {
              setCurrentUser(null);
            }
          } else {
            setCurrentUser(null);
          }
          setLoading(false);
        }
      }
    };
    
    checkInitialSession();

    // 인증 상태 변경 감지
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('🔐 Supabase Auth 상태 변경:', event, session?.user?.id);
        
        if (!mounted) return;
        
        if (session?.user) {
          console.log('✅ 로그인 감지:', session.user.id);
          await handleUserSession(session.user);
        } else {
          console.log('❌ 로그아웃 감지');
          // 로그아웃 상태
          setCurrentUser(null);
          localStorage.removeItem('currentUser');
          localStorage.removeItem('userId');
          localStorage.removeItem('userEmail');
          localStorage.removeItem('supabase_access_token');
          setLoading(false);
        }
      }
    );

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  // 회원가입 (이메일/비밀번호)
  function signup(email, password, username, businessInfo = null) {
    return new Promise(async (resolve, reject) => {
      if (!email || !password || !username) {
        reject(new Error('모든 필드를 입력해주세요.'));
        return;
      }

      try {
        // Supabase에 사용자 생성
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              display_name: username,
              full_name: username,
              phone_number: businessInfo?.phoneNumber || businessInfo?.contactPhone || null,
              referral_code: businessInfo?.referralCode || null,
              signup_source: businessInfo?.signupSource || null,
              ...(businessInfo && {
                account_type: businessInfo.accountType,
                business_number: businessInfo.businessNumber,
                business_name: businessInfo.businessName,
                representative: businessInfo.representative,
                business_address: businessInfo.businessAddress
              })
            }
          }
        });

        if (error) {
          console.error('회원가입 오류:', error);
          reject(new Error(error.message));
          return;
        }

        if (data.user) {
          // 이메일 확인이 필요한 경우 안내
          if (data.user.email_confirmed_at === null) {
            console.log('⚠️ 이메일 확인이 필요합니다. 가입 시 발송된 이메일을 확인해주세요.');
          }
          
          // handleUserSession을 호출하여 일관된 사용자 데이터 처리
          await handleUserSession(data.user);
          
          const userData = {
            uid: data.user.id,
            email: data.user.email,
            displayName: username,
            photoURL: null,
            provider: 'email',
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

          resolve(userData);
        } else {
          reject(new Error('사용자 생성에 실패했습니다.'));
        }
      } catch (error) {
        console.error('회원가입 오류:', error);
        reject(new Error(error.message || '회원가입에 실패했습니다.'));
      }
    });
  }

  // 로그인 (이메일/비밀번호)
  function login(email, password) {
    return new Promise(async (resolve, reject) => {
      if (!email || !password) {
        reject(new Error('이메일과 비밀번호를 입력해주세요.'));
        return;
      }

      try {
        console.log('🔐 로그인 시도:', email);
        
        const { data, error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password: password
        });

        if (error) {
          console.error('❌ 로그인 오류:', error);
          console.error('❌ 오류 코드:', error.status);
          console.error('❌ 오류 메시지:', error.message);
          
          // 이메일 확인 오류 처리
          if (error.message === 'Email not confirmed' || error.message.includes('email_not_confirmed')) {
            reject(new Error('이메일 인증이 완료되지 않았습니다. 가입 시 발송된 이메일을 확인해주세요.'));
            return;
          }
          
          // 잘못된 로그인 정보 오류 처리
          if (error.message === 'Invalid login credentials' || error.message.includes('invalid_credentials')) {
            reject(new Error('이메일 또는 비밀번호가 올바르지 않습니다. 다시 확인해주세요.'));
            return;
          }
          
          // 기타 오류
          reject(new Error(error.message || '로그인에 실패했습니다.'));
          return;
        }

        if (data.user) {
          // 세션 확인 및 저장
          const { data: sessionData } = await supabase.auth.getSession();
          if (sessionData?.session?.access_token) {
            localStorage.setItem('supabase_access_token', sessionData.session.access_token);
          }
          
          // handleUserSession을 호출하여 일관된 사용자 데이터 처리
          await handleUserSession(data.user);
          
          const userData = {
            uid: data.user.id,
            email: data.user.email,
            displayName: data.user.user_metadata?.display_name || data.user.user_metadata?.full_name || data.user.email?.split('@')[0] || '사용자',
            photoURL: data.user.user_metadata?.avatar_url || null,
            provider: 'email'
          };
          
          console.log('✅ 로그인 성공:', userData);
          resolve(userData);
        } else {
          console.error('❌ 로그인 실패: user 데이터 없음');
          reject(new Error('로그인에 실패했습니다.'));
        }
      } catch (error) {
        console.error('로그인 오류:', error);
        reject(new Error(error.message || '로그인에 실패했습니다.'));
      }
    });
  }

  // 구글 로그인
  function googleLogin() {
    return new Promise(async (resolve, reject) => {
      try {
        const { data, error } = await supabase.auth.signInWithOAuth({
          provider: 'google',
          options: {
            redirectTo: `${window.location.origin}/auth/callback`
          }
        });

        if (error) {
          console.error('구글 로그인 오류:', error);
          reject(new Error(error.message));
          return;
        }

        // OAuth는 리다이렉트되므로 여기서는 성공으로 처리
        resolve({ success: true, message: '구글 로그인 페이지로 이동합니다.' });
      } catch (error) {
        console.error('구글 로그인 오류:', error);
        reject(new Error('구글 로그인 초기화 중 오류가 발생했습니다.'));
      }
    });
  }

  // 카카오 로그인
  function kakaoLogin() {
    return new Promise(async (resolve, reject) => {
      try {
        // Supabase는 카카오를 직접 지원하지 않으므로, 기존 카카오 로그인 로직 유지
        // 또는 Supabase의 커스텀 OAuth 설정 필요
        if (!window.Kakao || !window.Kakao.Auth) {
          reject(new Error('카카오 SDK가 로드되지 않았습니다.'));
          return;
        }

        const redirectUri = window.location.origin + '/kakao-callback';
        window.Kakao.Auth.authorize({
          redirectUri: redirectUri
        });

        resolve({ success: true, message: '카카오 로그인 페이지로 이동합니다.' });
      } catch (error) {
        console.error('카카오 로그인 오류:', error);
        reject(new Error('카카오 로그인 초기화 중 오류가 발생했습니다.'));
      }
    });
  }

  // 로그아웃
  function logout() {
    return new Promise(async (resolve, reject) => {
      try {
        console.log('🔐 로그아웃 시작...');
        
        // 먼저 로컬 상태 정리 (즉시 UI 반영)
        setCurrentUser(null);
        setLoading(false);
        localStorage.removeItem('currentUser');
        localStorage.removeItem('userId');
        localStorage.removeItem('userEmail');
        localStorage.removeItem('supabase_access_token');
        
        // Supabase 세션 종료
        const { error } = await supabase.auth.signOut();
        
        if (error) {
          console.error('❌ Supabase 로그아웃 오류:', error);
          // 오류가 발생해도 로컬 상태는 이미 정리됨
          // reject하지 않고 성공으로 처리 (로컬 상태는 이미 정리됨)
          console.log('⚠️ Supabase 로그아웃 오류 발생했지만 로컬 상태는 정리됨');
        }
        
        // 세션 확인 (확인용)
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          console.warn('⚠️ 세션이 아직 존재함, 강제 정리 시도');
          // 세션이 남아있으면 다시 시도
          await supabase.auth.signOut();
        }
        
        console.log('✅ 로그아웃 완료');
        resolve();
      } catch (error) {
        console.error('❌ 로그아웃 오류:', error);
        // 오류가 발생해도 로컬 상태는 정리
        setCurrentUser(null);
        setLoading(false);
        localStorage.removeItem('currentUser');
        localStorage.removeItem('userId');
        localStorage.removeItem('userEmail');
        localStorage.removeItem('supabase_access_token');
        // 오류가 있어도 로컬 상태는 정리되었으므로 성공으로 처리
        resolve();
      }
    });
  }

  // 사용자 프로필 업데이트
  function updateUserProfile(updates) {
    return new Promise(async (resolve, reject) => {
      try {
        const { data, error } = await supabase.auth.updateUser({
          data: updates
        });

        if (error) {
          reject(error);
          return;
        }

        if (currentUser) {
          const updatedUser = { ...currentUser, ...updates };
          setCurrentUser(updatedUser);
          localStorage.setItem('currentUser', JSON.stringify(updatedUser));
        }

        resolve(data.user);
      } catch (error) {
        reject(error);
      }
    });
  }

  // 계정 삭제
  function deleteAccount() {
    return new Promise(async (resolve, reject) => {
      try {
        // Supabase에서는 사용자 삭제를 위해 관리자 권한이 필요하므로
        // 백엔드 API를 통해 처리하는 것이 좋습니다
        const { error } = await supabase.auth.signOut();
        if (error) {
          reject(error);
          return;
        }

        localStorage.removeItem('currentUser');
        localStorage.removeItem('userId');
        localStorage.removeItem('userEmail');
        setCurrentUser(null);
        resolve();
      } catch (error) {
        reject(error);
      }
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
