import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import kakaoAuth from '../utils/kakaoAuth';

const KakaoCallback = () => {
  const navigate = useNavigate();
  const { kakaoLogin } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const handleKakaoCallback = async () => {
      try {
        // URL에서 인가 코드 추출
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const error = urlParams.get('error');

        if (error) {
          throw new Error('카카오 로그인이 취소되었습니다.');
        }

        if (!code) {
          throw new Error('인가 코드를 받지 못했습니다.');
        }

        // 백엔드에 인가 코드 전송하여 토큰 요청
        const response = await fetch('/api/auth/kakao-token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code: code,
            redirectUri: window.location.origin + '/kakao-callback'
          }),
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            // 로그인 성공
            await kakaoLogin(data.user);
            navigate('/');
          } else {
            throw new Error(data.message || '카카오 로그인에 실패했습니다.');
          }
        } else {
          const errorData = await response.json();
          throw new Error(errorData.message || '카카오 로그인에 실패했습니다.');
        }
      } catch (error) {
        console.error('카카오 콜백 처리 오류:', error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    handleKakaoCallback();
  }, [navigate, kakaoLogin]);

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div style={{ fontSize: '18px', color: '#333' }}>
          카카오 로그인 처리 중...
        </div>
        <div style={{ 
          width: '40px', 
          height: '40px', 
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #FEE500',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div style={{ fontSize: '18px', color: '#e74c3c' }}>
          {error}
        </div>
        <button 
          onClick={() => navigate('/')}
          style={{
            padding: '10px 20px',
            backgroundColor: '#FEE500',
            border: 'none',
            borderRadius: '8px',
            fontSize: '16px',
            cursor: 'pointer'
          }}
        >
          홈으로 돌아가기
        </button>
      </div>
    );
  }

  return null;
};

export default KakaoCallback;
