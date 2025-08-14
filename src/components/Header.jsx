import React from 'react'
import { Link } from 'react-router-dom'
import { User, LogOut } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './Header.css'

const Header = () => {
  const { currentUser, logout, loading } = useAuth()

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      console.error('로그아웃 실패:', error)
    }
  }

  // 로딩 중일 때는 기본 헤더만 표시
  if (loading) {
    return (
      <header className="header">
        <div className="header-container">
          <Link to="/" className="logo">
            SNSINTO
          </Link>
        </div>
      </header>
    )
  }

  return (
    <header className="header">
      <div className="header-container">
        <Link to="/" className="logo">
          SNSINTO
        </Link>
        <div className="header-right">
          {currentUser ? (
            <div className="user-info">
              <Link to="/orders" className="orders-link">
                주문 내역
              </Link>
              <span className="username">{currentUser.displayName || currentUser.email}</span>
              <button onClick={handleLogout} className="logout-btn">
                <LogOut size={16} />
                <span>로그아웃</span>
              </button>
            </div>
          ) : (
            <Link to="/login" className="member-btn">
              <User size={20} />
              <span>로그인</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header
