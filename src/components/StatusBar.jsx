import React, { useState, useEffect } from 'react'
import { CheckCircle, LogOut, Coins } from 'lucide-react'
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

  // Debounce timer ref
  const lastFetchRef = React.useRef(0)
  const FETCH_COOLDOWN = 1000000 // 10 minutes minimum between fetches

  // 사용자 포인트 조회 함수 (with debounce)
  const fetchUserPoints = async (force = false) => {
    // currentUser가 없으면 포인트 조회하지 않음
    if (!currentUser?.uid) {
      setUserPoints(0)
      return
    }
    
    const now = Date.now()
    const timeSinceLastFetch = now - lastFetchRef.current
    
    // Prevent too frequent calls (unless forced)
    if (!force && timeSinceLastFetch < FETCH_COOLDOWN) {
      console.log(`⏭️ 포인트 조회 스킵 (${Math.round((FETCH_COOLDOWN - timeSinceLastFetch) / 1000)}초 후 가능)`)
      return
    }
    
    const userId = currentUser.uid
    lastFetchRef.current = now
    
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

  // 포인트 업데이트 이벤트 핸들러 (force refresh)
  const handlePointsUpdate = () => {
    fetchUserPoints(true) // Force immediate fetch
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
      window.removeEventListener('resize', checkIsMobile)
      window.removeEventListener('pointsUpdated', handlePointsUpdate)
      window.removeEventListener('storage', fetchUserPoints)
      window.removeEventListener('focus', fetchUserPoints)
      document.removeEventListener('visibilitychange', fetchUserPoints)
    }
  }, [currentUser])

  const handleLogout = async () => {
    try {
      console.log('🔐 StatusBar 로그아웃 버튼 클릭');
      if (typeof logout === 'function') {
        // 로딩 상태 설정 (버튼 비활성화 방지)
        setPointsLoading(true);
        await logout();
        console.log('✅ StatusBar 로그아웃 처리 완료');
        // 포인트 초기화
        setUserPoints(0);
        setPointsLoading(false);
        alert('로그아웃되었습니다.');
        // 모바일에서 페이지 리로드하여 상태 완전히 초기화
        if (window.innerWidth <= 1200) {
          window.location.href = '/';
        } else {
          navigate('/');
        }
      } else {
        console.error('logout 함수가 정의되지 않았습니다.');
        setPointsLoading(false);
        alert('로그아웃 함수를 찾을 수 없습니다.');
      }
    } catch (error) {
      console.error('로그아웃 실패:', error);
      // 오류가 있어도 포인트 초기화
      setUserPoints(0);
      setPointsLoading(false);
      alert('로그아웃 중 오류가 발생했습니다.');
      // 모바일에서 오류 발생 시에도 페이지 리로드
      if (window.innerWidth <= 1200) {
        window.location.href = '/';
      }
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

  // 사용자 정보 확인 (currentUser만 확인)
  const userName = currentUser?.displayName || currentUser?.email || '사용자'

  return (
    <>
      {/* 모바일 헤더 (원래 있던 상단바 - 로고, OP, 충전 버튼) */}
      {isMobile && (
        <div className="mobile-head">
          <Link to="/" className="mobile-logo-link">
              <img 
                src="/logo.png" 
              alt="SOCIALITY" 
                className="mobile-header-logo"
              />
            </Link>
          
          <div className="mobile-header-right">
            {currentUser ? (
                <>
                <div className="mobile-points-display">
                    <Coins size={16} />
                  <span>{pointsLoading ? '...' : userPoints.toLocaleString()}P</span>
                  </div>
                <Link to="/points" className="mobile-charge-btn-header">
                    충전
                  </Link>
                <button
                  className="mobile-logout-btn-header"
                  onClick={handleLogout}
                  title="로그아웃"
                >
                  <LogOut size={18} />
                  </button>
                </>
              ) : (
              <div className="mobile-header-auth">
                  <button 
                  className="mobile-login-btn-header"
                    onClick={openLoginModal}
                  >
                  로그인
                  </button>
                  <button 
                  className="mobile-signup-btn-header"
                    onClick={openSignupModal}
                  >
                  회원가입
                  </button>
                </div>
              )}
            </div>
          </div>
      )}
          
      {/* 모바일 상태바 (파란색 - 시간 표시) */}
      {isMobile && (
        <div className="status-bar mobile-status-bar">
          <div className="status-info">
            <div className="time-display">
              <CheckCircle size={16} />
              <span>{formatTime(currentTime)}</span>
            </div>
            <div className="status-user-display">
              {currentUser ? (
                <span>{userName}고객님</span>
              ) : (
                <span>게스트</span>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* 데스크톱 상태바 */}
      {!isMobile && (
        <div className="status-bar">
          <div className="status-info">
            <div className="time-display">
            <CheckCircle size={16} />
              <span>{formatTime(currentTime)}</span>
          </div>
          </div>
        </div>
      )}
    </>
  )
}

export default StatusBar