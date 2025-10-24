import React, { useState, useEffect } from 'react'
import { CheckCircle, Coins, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { Link } from 'react-router-dom'
import './StatusBar.css'

const StatusBar = () => {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [userPoints, setUserPoints] = useState(0)
  const [pointsLoading, setPointsLoading] = useState(false)
  const { currentUser } = useAuth()

  // 사용자 포인트 조회 함수
  const fetchUserPoints = async () => {
    const userId = localStorage.getItem('userId') || localStorage.getItem('firebase_user_id') || currentUser?.uid
    
    if (!userId) {
      setUserPoints(0)
      return
    }
    
    setPointsLoading(true)
    try {
      const response = await fetch(`${window.location.origin}/api/points?user_id=${userId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
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
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)

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
      clearInterval(timer)
      window.removeEventListener('pointsUpdated', handlePointsUpdate)
      window.removeEventListener('storage', fetchUserPoints)
      window.removeEventListener('focus', fetchUserPoints)
      document.removeEventListener('visibilitychange', fetchUserPoints)
    }
  }, [currentUser])

  const formatTime = (date) => {
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).replace(/\./g, '-')
  }

  // 사용자 정보 확인
  const userId = localStorage.getItem('userId') || localStorage.getItem('firebase_user_id') || currentUser?.uid
  const userName = currentUser?.displayName || currentUser?.email || localStorage.getItem('userEmail') || '사용자'

  return (
    <div className="status-bar">
      <div className="status-info">
        <div className="time-display">
          <CheckCircle size={16} />
          <span>{formatTime(currentTime)}</span>
        </div>
        
        {userId && (
          <div className="user-section">
            <div className="user-info">
              <User size={16} />
              <span className="user-name">{userName}</span>
            </div>
            
            <div className="points-section">
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
          </div>
        )}
      </div>
    </div>
  )
}

export default StatusBar