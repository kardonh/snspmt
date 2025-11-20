import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabase/client';

const AuthCallback = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // URL에서 세션 정보 추출
        const { data: { session }, error } = await supabase.auth.getSession();
        
        if (error) {
          console.error('❌ 인증 콜백 오류:', error);
          navigate('/?error=auth_failed');
          return;
        }

        if (session?.user) {
          console.log('✅ 인증 성공:', session.user);
          // 홈으로 리다이렉트
          navigate('/');
        } else {
          console.warn('⚠️ 세션이 없습니다');
          navigate('/?error=no_session');
        }
      } catch (error) {
        console.error('❌ 인증 콜백 처리 오류:', error);
        navigate('/?error=auth_error');
      }
    };

    handleAuthCallback();
  }, [navigate]);

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      flexDirection: 'column',
      gap: '1rem'
    }}>
      <div>인증 처리 중...</div>
      <div style={{ fontSize: '0.875rem', color: '#666' }}>잠시만 기다려주세요.</div>
    </div>
  );
};

export default AuthCallback;


