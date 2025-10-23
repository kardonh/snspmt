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
    const userId = localStorage.getItem('userId') || localStorage.getItem('firebase_user_id') || currentUser?.uid
    
    if (!userId) {
      setUserPoints(0)
      setPointsLoading(false)
      return
    }
    
    setPointsLoading(true)
    try {
      const response = await fetch(`${window.location.origin}/api/points?user_id=${userId}`)
      if (response.ok) {
        const data = await response.json()
        const points = data.points || 0
        setUserPoints(points)
      } else {
        setUserPoints(0)
      }
    } catch (error) {
      console.error('포인트 조회 오류:', error)
      setUserPoints(0)
    } finally {
      setPointsLoading(false)
    }
  }

  // 포인트 업데이트 이벤트 핸들러
  const handlePointsUpdate = () => {
    fetchUserPoints()
  }

  useEffect(() => {
    // 초기 포인트 조회
    fetchUserPoints()

    // 포인트 업데이트 이벤트 리스너
    window.addEventListener('pointsUpdated', handlePointsUpdate)
    
    // storage 이벤트 리스너 (다른 탭에서 로그인/로그아웃 시)
    window.addEventListener('storage', (e) => {
      if (e.key === 'userId' || e.key === 'firebase_user_id') {
        fetchUserPoints()
      }
    })
    
    // 포커스 이벤트 리스너 (탭 전환 시)
    window.addEventListener('focus', fetchUserPoints)
    
    // 가시성 변경 이벤트 리스너
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        fetchUserPoints()
      }
    })

    return () => {
      window.removeEventListener('pointsUpdated', handlePointsUpdate)
      window.removeEventListener('storage', fetchUserPoints)
      window.removeEventListener('focus', fetchUserPoints)
      document.removeEventListener('visibilitychange', fetchUserPoints)
    }
  }, [currentUser])

  // 사용자 정보 확인
  const userId = localStorage.getItem('userId') || localStorage.getItem('firebase_user_id') || currentUser?.uid
  const userName = currentUser?.displayName || currentUser?.email || localStorage.getItem('userEmail') || '사용자'

  return (
    <>
      <header className="header">
        <div className="header-content">
          <Link to="/" className="logo">
            <img 
              src="/logo.png" 
              alt="Sociality" 
              className="header-logo"
            />
          </Link>
          
          <nav className="nav">
            <Link to="/" className="nav-link">홈</Link>
            <Link to="/orders" className="nav-link">주문내역</Link>
            <Link to="/points" className="nav-link">포인트</Link>
          </nav>
          
          <div className="user-section">
            {loading ? (
              <div className="loading">로딩 중...</div>
            ) : userId ? (
              <>
                <div className="user-info">
                  <User size={16} />
                  <span className="user-name">{userName}</span>
                </div>
                
                <div className="points-info">
                  <Coins size={16} />
                  <span className="points-amount">
                    {pointsLoading ? '로딩...' : `${userPoints.toLocaleString()}P`}
                  </span>
                </div>
                
                <Link to="/points" className="charge-btn">
                  충전
                </Link>
                
                <button onClick={handleLogout} className="logout-btn">
                  <LogOut size={16} />
                  로그아웃
                </button>
              </>
            ) : (
              <div className="auth-buttons">
                <button 
                  className="login-btn"
                  onClick={() => setIsLoginModalOpen(true)}
                >
                  로그인
                </button>
                <button 
                  className="signup-btn"
                  onClick={() => setIsLoginModalOpen(true)}
                >
                  회원가입
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <AuthModal 
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />
    </>
  )
}

export default Header