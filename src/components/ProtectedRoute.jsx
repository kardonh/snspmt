import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function ProtectedRoute({ children }) {
  const { currentUser, loading } = useAuth();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // localStorage에서 사용자 정보 확인
    const checkLocalStorage = () => {
      try {
        const storedUser = localStorage.getItem('currentUser');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          console.log('🔒 ProtectedRoute: localStorage 사용자 확인됨', userData);
          return true;
        }
      } catch (error) {
        console.error('ProtectedRoute: localStorage 확인 실패', error);
      }
      return false;
    };

    // 로딩이 완료되거나 localStorage에 사용자 정보가 있으면 체크 완료
    if (!loading || checkLocalStorage()) {
      setIsChecking(false);
    }

    // 타임아웃: 5초 후에도 로딩 중이면 강제로 체크 완료
    const timeoutId = setTimeout(() => {
      console.warn('⚠️ ProtectedRoute: 인증 확인 타임아웃, 로딩 강제 종료');
      setIsChecking(false);
    }, 5000);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [loading]);

  // 로딩 중이거나 체크 중일 때는 로딩 표시
  if (loading || isChecking) {
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
          인증 확인 중...
        </div>
        <div style={{ 
          width: '40px', 
          height: '40px', 
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #667eea',
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

  // Firebase 인증 또는 localStorage에 사용자 정보가 없으면 리다이렉트
  if (!currentUser) {
    // localStorage에서도 사용자 정보가 없는 경우에만 리다이렉트
    const storedUser = localStorage.getItem('currentUser');
    if (!storedUser) {
      return <Navigate to="/" />;
    }
  }

  return children;
}
