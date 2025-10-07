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
  const { currentUser, logout, setShowAuthModal } = useAuth()
  const navigate = useNavigate()

  // 사용자 포인트 조회 함수
  const fetchUserPoints = async () => {
    if (!currentUser) return
    
    setPointsLoading(true)
    try {
      const response = await fetch(`/api/points?user_id=${currentUser.uid}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await currentUser.getIdToken()}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setUserPoints(data.points || 0)
      }
    } catch (error) {
      console.error('포인트 조회 실패:', error)
    } finally {
      setPointsLoading(false)
    }
  }

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)

    const checkIsMobile = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    
    checkIsMobile()
    window.addEventListener('resize', checkIsMobile)

    // 사용자 포인트 조회
    if (currentUser) {
      fetchUserPoints()
    }

    return () => {
      clearInterval(timer)
      window.removeEventListener('resize', checkIsMobile)
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
              <img src="/logo.png" alt="Sociality" className="mobile-header-logo" />
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
                <button 
                  className="mobile-login-btn"
                  onClick={() => setShowAuthModal(true)}
                >
                  <User size={16} />
                  <span>로그인</span>
                </button>
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
        <div className="status-content">
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
