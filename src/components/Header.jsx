import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { User, LogOut, Coins } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { smmpanelApi } from '../services/snspopApi'
import LoginModal from './LoginModal'
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
  useEffect(() => {
    const fetchUserPoints = async () => {
      if (currentUser) {
        setPointsLoading(true)
        try {
          console.log('포인트 조회 시작:', currentUser.uid)
          const response = await smmpanelApi.getUserPoints(currentUser.uid)
          console.log('포인트 조회 응답:', response)
          setUserPoints(response.data?.points || response.points || 0)
        } catch (error) {
          console.error('포인트 조회 실패:', error)
          setUserPoints(0)
        } finally {
          setPointsLoading(false)
        }
      } else {
        setUserPoints(0)
        setPointsLoading(false)
      }
    }

    fetchUserPoints()
  }, [currentUser])

  // 로딩 중일 때는 기본 헤더만 표시
  if (loading) {
    return (
      <header className="header">
        <div className="header-container">
          <Link to="/" className="logo">
            <img src="/logo.png" alt="Sociality" className="header-logo" />
          </Link>
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
          <Link to="/services" className="nav-link">
            서비스
          </Link>
          <Link to="/info" className="nav-link">
            정보
          </Link>
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
            >
              <User size={20} />
              <span>로그인</span>
            </button>
          )}
        </div>
      </div>
      
      <LoginModal 
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />
    </header>
  )
}

export default Header
