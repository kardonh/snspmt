import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { User, LogOut, Coins } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { smmpanelApi } from '../services/snspopApi'
import AuthModal from './AuthModal'
import './Header.css'

const Header = () => {
  const { currentUser, logout, loading } = useAuth()
  const [userPoints, setUserPoints] = useState(0)
  const [pointsLoading, setPointsLoading] = useState(false)
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false)

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      console.error('로그아웃 실패:', error)
    }
  }

  // 사용자 포인트 조회
  const fetchUserPoints = async () => {
    // localStorage 우선 사용 (Firebase 인증 우회)
    const userId = localStorage.getItem('userId') || localStorage.getItem('firebase_user_id') || currentUser?.uid
    
    if (!userId) {
      console.log('🔍 Header: 사용자 ID 없음, 포인트 조회 건너뜀');
      setUserPoints(0)
      setPointsLoading(false)
      return;
    }
    
    setPointsLoading(true)
    try {
      console.log('🔍 Header 포인트 조회 시작:', userId)
      const response = await fetch(`${window.location.origin}/api/points?user_id=${userId}`)
      if (response.ok) {
        const data = await response.json()
        const points = data.points || 0
        setUserPoints(points)
        console.log('✅ Header 포인트 조회 성공:', points)
        
        // 강제 리렌더링을 위한 상태 업데이트
        setTimeout(() => {
          setUserPoints(points)
        }, 100)
      } else {
        console.error('❌ Header 포인트 조회 실패:', response.status)
        setUserPoints(0)
      }
    } catch (error) {
      console.error('❌ Header 포인트 조회 오류:', error)
      setUserPoints(0)
    } finally {
      setPointsLoading(false)
    }
  }

  useEffect(() => {
    // 자동 로그인 시 포인트 조회 지연 처리
    const initializePoints = () => {
      const userId = currentUser?.uid || localStorage.getItem('userId') || localStorage.getItem('firebase_user_id')
      console.log('🔍 Header 초기화 - currentUser:', currentUser);
      console.log('🔍 Header 초기화 - localStorage userId:', localStorage.getItem('userId'));
      
      if (userId) {
        console.log('🔍 Header: 사용자 ID 발견, 포인트 조회 시작');
        fetchUserPoints()
      } else {
        console.log('🔍 Header: 사용자 ID 없음, 포인트 조회 건너뜀');
        setUserPoints(0)
      }
    }

    // 즉시 실행
    initializePoints()
    
    // currentUser가 변경될 때도 실행 (자동 로그인 완료 시)
    if (currentUser) {
      console.log('🔍 Header: currentUser 변경 감지, 포인트 조회 재시도');
      initializePoints()
    }

    // 포인트 업데이트 이벤트 리스너
    const handlePointsUpdate = () => {
      console.log('🔄 Header: pointsUpdated 이벤트 수신');
      console.log('🔄 Header: 현재 사용자 정보:', currentUser);
      console.log('🔄 Header: localStorage userId:', localStorage.getItem('userId'));
      console.log('🔄 Header: localStorage firebase_user_id:', localStorage.getItem('firebase_user_id'));
      
      // 사용자 정보가 있으면 포인트 업데이트
      const userId = currentUser?.uid || localStorage.getItem('userId') || localStorage.getItem('firebase_user_id')
      if (userId) {
        console.log('🔄 Header: 포인트 업데이트 시작');
        fetchUserPoints()
      } else {
        console.log('🔄 Header: 사용자 정보 없음, 포인트 업데이트 건너뜀');
      }
    }

    // 포인트 충전 완료 이벤트 리스너
    window.addEventListener('pointsUpdated', handlePointsUpdate)
    console.log('✅ Header: pointsUpdated 이벤트 리스너 등록됨')
    
    // 강제 포인트 업데이트 함수
    const forcePointsUpdate = () => {
      console.log('🔄 Header: 강제 포인트 업데이트');
      const userId = currentUser?.uid || localStorage.getItem('userId') || localStorage.getItem('firebase_user_id')
      if (userId) {
        fetchUserPoints()
      }
    }
    
    // 추가 이벤트 리스너들
    window.addEventListener('storage', (e) => {
      if (e.key === 'userId' || e.key === 'firebase_user_id') {
        console.log('🔄 Header: localStorage 변경 감지, 포인트 업데이트');
        forcePointsUpdate()
      }
    })
    
    // 포커스 이벤트 리스너 (탭 전환 시 포인트 업데이트)
    window.addEventListener('focus', () => {
      console.log('🔄 Header: 윈도우 포커스, 포인트 업데이트');
      forcePointsUpdate()
    })
    
    // 가시성 변경 이벤트 리스너
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        console.log('🔄 Header: 페이지 가시성 변경, 포인트 업데이트');
        forcePointsUpdate()
      }
    })

    return () => {
      window.removeEventListener('pointsUpdated', handlePointsUpdate)
      window.removeEventListener('storage', forcePointsUpdate)
      window.removeEventListener('focus', forcePointsUpdate)
      document.removeEventListener('visibilitychange', forcePointsUpdate)
    }
  }, [currentUser])

  // 로딩 중일 때는 기본 헤더만 표시 (짧은 시간만)
  if (loading) {
    return (
      <header className="header">
        <div className="header-container">
          <Link to="/" className="logo">
            <img src="/logo.png" alt="Sociality" className="header-logo" />
          </Link>
          <nav className="header-nav">
            <Link to="/faq" className="nav-link">
              FAQ
            </Link>
          </nav>
          <div className="header-right">
            <button 
              className="member-btn"
              onClick={() => setIsLoginModalOpen(true)}
            >
              <User size={20} />
              <span>로그인</span>
            </button>
          </div>
        </div>
      </header>
    )
  }

  return (
    <header className="header">
      <div className="header-container">
        <Link to="/" className="logo">
          <img src="/logo.png" alt="Sociality" className="header-logo" />
        </Link>
        <nav className="header-nav">
          <Link to="/faq" className="nav-link">
            FAQ
          </Link>
        </nav>
        <div className="header-right">
          {currentUser ? (
            <div className="user-info">
              {/* 모바일에서는 포인트와 충전 버튼만 표시 */}
              <div className="mobile-user-info">
                <div className="points-info">
                  <Coins size={16} />
                  <span className="points-amount">
                    {pointsLoading ? '로딩...' : `${userPoints.toLocaleString()}P`}
                  </span>
                </div>
                <Link to="/points" className="charge-btn">
                  충전
                </Link>
              </div>
              
              {/* 데스크톱에서는 기존 정보 표시 */}
              <div className="desktop-user-info">
                <Link to="/orders" className="orders-link">
                  주문 내역
                </Link>
                <span className="username">{currentUser.displayName || currentUser.email}</span>
                <button onClick={handleLogout} className="logout-btn">
                  <LogOut size={16} />
                  <span>로그아웃</span>
                </button>
              </div>
            </div>
          ) : (
            <button 
              className="member-btn"
              onClick={() => setIsLoginModalOpen(true)}
              onTouchEnd={() => setIsLoginModalOpen(true)}
            >
              <User size={20} />
              <span>로그인</span>
            </button>
          )}
        </div>
      </div>
      
      <AuthModal 
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        initialMode="login"
      />
    </header>
  )
}

export default Header
