import React, { useState, useEffect } from 'react'
import { CheckCircle, LogOut, Coins, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import './StatusBar.css'

const StatusBar = () => {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [isMobile, setIsMobile] = useState(false)
  const [userPoints, setUserPoints] = useState(0)
  const [pointsLoading, setPointsLoading] = useState(false)
  const { currentUser, logout, openLoginModal, openSignupModal } = useAuth()
  const navigate = useNavigate()

  // 사용자 포인트 조회 함수
  const fetchUserPoints = async () => {
    // 사용자 정보 검증 강화
    const userId = currentUser?.uid || localStorage.getItem('userId') || localStorage.getItem('firebase_user_id')
    
    if (!userId) {
      console.log('🔍 StatusBar: 사용자 ID 없음, 포인트 조회 건너뜀');
      setUserPoints(0)
      return;
    }
    
    // Firebase 사용자 객체 유효성 검증
    if (currentUser && typeof currentUser.uid !== 'string') {
      console.log('🔍 StatusBar: 유효하지 않은 사용자 객체, localStorage 사용');
    }
    
    setPointsLoading(true)
    try {
      console.log('🔍 StatusBar 포인트 조회 시작:', userId);
      const response = await fetch(`${window.location.origin}/api/points?user_id=${userId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setUserPoints(data.points || 0)
        console.log('✅ StatusBar 포인트 조회 성공:', data.points)
      } else {
        console.error('❌ StatusBar 포인트 조회 실패:', response.status)
        setUserPoints(0)
      }
    } catch (error) {
      console.error('❌ StatusBar 포인트 조회 오류:', error)
      setUserPoints(0)
    } finally {
      setPointsLoading(false)
    }
  }

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)

    const checkIsMobile = () => {
      setIsMobile(window.innerWidth <= 1200)
    }
    
    checkIsMobile()
    window.addEventListener('resize', checkIsMobile)

    // 사용자 포인트 조회
    if (currentUser) {
      fetchUserPoints()
    }

    // 주기적 포인트 확인 (30초마다)
    const pointsCheckInterval = setInterval(() => {
      if (currentUser && currentUser.uid) {
        console.log('🔄 StatusBar: 주기적 포인트 확인');
        fetchUserPoints()
      }
    }, 30000) // 30초마다 확인

    // 포인트 업데이트 이벤트 리스너
    const handlePointsUpdate = () => {
      console.log('🔄 StatusBar: pointsUpdated 이벤트 수신');
      console.log('🔄 StatusBar: 현재 사용자 정보:', currentUser);
      console.log('🔄 StatusBar: localStorage userId:', localStorage.getItem('userId'));
      console.log('🔄 StatusBar: localStorage firebase_user_id:', localStorage.getItem('firebase_user_id'));
      
      // 사용자 정보가 있으면 포인트 업데이트
      const userId = currentUser?.uid || localStorage.getItem('userId') || localStorage.getItem('firebase_user_id')
      if (userId) {
        console.log('🔄 StatusBar: 포인트 업데이트 시작');
        fetchUserPoints()
      } else {
        console.log('🔄 StatusBar: 사용자 정보 없음, 포인트 업데이트 건너뜀');
      }
    }

    // 포인트 충전 완료 이벤트 리스너
    window.addEventListener('pointsUpdated', handlePointsUpdate)
    console.log('✅ StatusBar: pointsUpdated 이벤트 리스너 등록됨')

    return () => {
      clearInterval(timer)
      clearInterval(pointsCheckInterval)
      window.removeEventListener('resize', checkIsMobile)
      window.removeEventListener('pointsUpdated', handlePointsUpdate)
    }
  }, [currentUser])

  const handleLogout = async () => {
    try {
      await logout()
      alert('로그아웃되었습니다.')
      navigate('/')
    } catch (error) {
      console.error('로그아웃 실패:', error)
      alert('로그아웃 중 오류가 발생했습니다.')
    }
  }

  const formatTime = (date) => {
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).replace(/\./g, '-')
  }

  return (
    <>
      {/* 모바일 헤더 */}
      {isMobile && (
        <>
          <div className="mobile-header">
            <Link to="/" className="mobile-logo">
              <img 
                src="/logo.png" 
                alt="Sociality" 
                className="mobile-header-logo"
                style={{ cursor: 'pointer' }}
              />
            </Link>
            <div className="mobile-user-info">
              {currentUser ? (
                <>
                  <div className="mobile-points-info">
                    <Coins size={16} />
                    <span className="mobile-points-amount">
                      {pointsLoading ? '로딩...' : `${userPoints.toLocaleString()}P`}
                    </span>
                  </div>
                  <Link to="/points" className="mobile-charge-btn">
                    충전
                  </Link>
                  <span className="mobile-user-name">
                    {currentUser.displayName || currentUser.email}
                  </span>
                  <button onClick={handleLogout} className="mobile-logout-btn">
                    <LogOut size={16} />
                  </button>
                </>
              ) : (
                <div className="mobile-auth-buttons">
                  <button 
                    className="mobile-login-btn"
                    onClick={openLoginModal}
                  >
                    <User size={16} />
                    <span>로그인</span>
                  </button>
                  <button 
                    className="mobile-signup-btn"
                    onClick={openSignupModal}
                  >
                    <User size={16} />
                    <span>회원가입</span>
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {/* 모바일 상태바 */}
          <div className="mobile-status-bar">
            <div className="mobile-status-indicator">
              <CheckCircle size={14} />
              <span>모든 서비스 정상 가동중</span>
            </div>
            <div className="mobile-status-time">
              체크시간: {formatTime(currentTime)}
            </div>
          </div>
        </>
      )}
      
      {/* 데스크톱 상태바 */}
      {!isMobile && (
        <div className="status-content" style={{ display: 'flex', visibility: 'visible', opacity: 1 }}>
          <div className="status-indicator">
            <CheckCircle size={16} />
            <span>모든 서비스 정상 가동중</span>
          </div>
          <div className="status-time">
            체크시간: {formatTime(currentTime)}
          </div>
        </div>
      )}
    </>
  )
}

export default StatusBar
