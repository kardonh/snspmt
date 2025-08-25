import React, { useState, useEffect } from 'react'
import { CheckCircle, LogOut } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import './StatusBar.css'

const StatusBar = () => {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [isMobile, setIsMobile] = useState(false)
  const { currentUser, logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)

    const checkIsMobile = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    
    checkIsMobile()
    window.addEventListener('resize', checkIsMobile)

    return () => {
      clearInterval(timer)
      window.removeEventListener('resize', checkIsMobile)
    }
  }, [])

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
    <div className="status-bar">
      {/* 모바일 헤더 */}
      {isMobile && (
        <div className="mobile-header">
          <div className="mobile-logo">
            <h2>SNSinto</h2>
          </div>
          <div className="mobile-user-info">
            {currentUser ? (
              <>
                <span className="mobile-user-name">
                  {currentUser.displayName || currentUser.email}
                </span>
                <button onClick={handleLogout} className="mobile-logout-btn">
                  <LogOut size={16} />
                </button>
              </>
            ) : (
              <span className="mobile-guest">guest</span>
            )}
          </div>
        </div>
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
    </div>
  )
}

export default StatusBar
