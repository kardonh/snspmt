import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function ProtectedRoute({ children }) {
  const { currentUser, loading } = useAuth();

  // Firebase 인증 상태가 로딩 중일 때는 대기
  if (loading) {
    return <div>Loading...</div>;
  }

  // 로딩이 완료되었지만 사용자가 로그인되지 않은 경우
  if (!currentUser) {
    return <Navigate to="/login" />;
  }

  return children;
}
