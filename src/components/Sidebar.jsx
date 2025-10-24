import React, { useState, useEffect } from 'react'
import { useLocation, Link, useNavigate } from 'react-router-dom'
import { 
  Star, 
  Info, 
  HelpCircle, 
  LogIn, 
  UserPlus, 
  FileText, 
  ChevronDown,
  ChevronUp,
  X,
  Shield,
  CreditCard,
  Package,
  Coins,
  Users
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useGuest } from '../contexts/GuestContext'
import './Sidebar.css'

const Sidebar = ({ onClose }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const { currentUser, logout, openLoginModal, openSignupModal } = useAuth()
  const { isGuest } = useGuest()

  const [businessInfoOpen, setBusinessInfoOpen] = useState(false)
  const [userPoints, setUserPoints] = useState(0)
  const [pointsLoading, setPointsLoading] = useState(false)
  const [hasReferralCode, setHasReferralCode] = useState(false)
  const [referralCodeLoading, setReferralCodeLoading] = useState(false)

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
        setUserPoints(data.points || 0)
      } else {
        setUserPoints(0)
      }
    } catch (error) {
      console.error('포인트 조회 실패:', error)
      setUserPoints(0)
    } finally {
      setPointsLoading(false)
    }
  }

  // 추천인 코드 확인 함수
  const checkReferralCode = async () => {
    if (!currentUser) return
    
    setReferralCodeLoading(true)
    try {
      // 사용자 이메일 가져오기 (추천인 코드는 이메일로 저장됨)
      const userEmail = currentUser.email || `${currentUser.uid}@example.com`
      const response = await fetch(`/api/referral/my-codes?user_id=${userEmail}`)
      
      if (response.ok) {
        const data = await response.json()
        setHasReferralCode(data.codes && data.codes.length > 0)
      } else {
        setHasReferralCode(false)
      }
    } catch (error) {
      console.error('추천인 코드 확인 실패:', error)
      setHasReferralCode(false)
    } finally {
      setReferralCodeLoading(false)
    }
  }

  // 포인트 업데이트 이벤트 핸들러
  const handlePointsUpdate = () => {
    fetchUserPoints()
  }

  // 사용자가 로그인했을 때 포인트 조회 및 추천인 코드 확인
  useEffect(() => {
    if (currentUser) {
      fetchUserPoints()
      checkReferralCode()
    } else {
      setUserPoints(0)
      setHasReferralCode(false)
    }

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

  // 기본 메뉴 아이템
  const baseMenuItems = [
    { id: 'order', name: '주문하기', icon: Star, path: '/', color: '#3b82f6' },
    { id: 'orders', name: '주문내역', icon: FileText, path: '/orders', color: '#8b5cf6' },
    { id: 'points', name: '포인트 구매', icon: CreditCard, path: '/points', color: '#f59e0b' },
    { id: 'blog', name: '블로그', icon: FileText, path: '/blog', color: '#06b6d4' },
    { id: 'faq', name: '자주 묻는 질문', icon: HelpCircle, path: '/faq', color: '#10b981' },
    { id: 'service', name: '서비스 소개서', icon: FileText, path: '/service-guide.pdf', color: '#6b7280', external: true },
  ]

  // 추천인 대시보드 메뉴 (추천인 코드가 있는 사용자만)
  const referralMenuItem = { id: 'referral', name: '추천인 대시보드', icon: Users, path: '/referral', color: '#8b5cf6' }

  // 최종 메뉴 아이템 구성
  const filteredBaseMenuItems = (isGuest && !currentUser)
    ? baseMenuItems.filter(item => ['order', 'blog', 'faq', 'service'].includes(item.id)) // 게스트 모드에서는 주문하기, 블로그, FAQ, 서비스 소개서만 표시
    : baseMenuItems

  const menuItems = (hasReferralCode && !isGuest) 
    ? [...filteredBaseMenuItems.slice(0, 3), referralMenuItem, ...filteredBaseMenuItems.slice(3)]
    : filteredBaseMenuItems

  // 관리자 메뉴 아이템 (관리자 계정일 때만 표시)
  const adminMenuItems = [
    { id: 'admin', name: '관리자 대시보드', icon: Shield, path: '/admin', color: '#dc2626' }
  ]

  const handleSignOut = async () => {
    try {
      await logout()
      alert('로그아웃되었습니다. 게스트 모드로 전환됩니다.')
      // 모바일에서 사이드바가 열려있다면 닫기
      if (onClose) {
        onClose()
      }
      // 홈페이지로 리다이렉트
      navigate('/')
    } catch (error) {
      console.error('로그아웃 실패:', error)
      alert('로그아웃 중 오류가 발생했습니다.')
    }
  }

  const handleMenuItemClick = () => {
    // 모바일에서만 사이드바 닫기 (onClose가 있을 때만)
    if (onClose && window.innerWidth <= 768) {
      onClose()
    }
  }

  return (
    <aside className="sidebar">
      {/* Mobile Close Button */}
      {onClose && (
        <button className="mobile-close-btn" onClick={onClose}>
          <X size={24} />
        </button>
      )}
      
      {/* Logo */}
      <div className="sidebar-logo">
        <img 
          src="/logo.png" 
          alt="Sociality" 
          className="logo-image" 
          onClick={() => navigate('/')}
          style={{ cursor: 'pointer' }}
        />
      </div>

      {/* User Status */}
      <div className="user-status">
        {(currentUser || localStorage.getItem('userId') || localStorage.getItem('firebase_user_id')) ? (
          <div className="user-info">
            <span className="user-name">
              {currentUser?.displayName || currentUser?.email || localStorage.getItem('userEmail') || '사용자'}
            </span>
            <div className="user-points">
              <Coins size={16} className="points-icon" />
              <span className="points-text">
                {pointsLoading ? '로딩중...' : `${userPoints.toLocaleString()}P`}
              </span>
            </div>
            <button onClick={handleSignOut} className="logout-btn">로그아웃</button>
          </div>
        ) : (
          <div className="guest-info">
            <span className="guest-text">게스트 모드</span>
            <div className="auth-buttons">
              <button onClick={openLoginModal} className="login-btn">로그인</button>
              <button onClick={openSignupModal} className="signup-btn">회원가입</button>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Menu */}
      <nav className="sidebar-nav">
        {menuItems.map(({ id, name, icon: Icon, path, color, external }) => (
          external ? (
            <a
              key={id}
              href={path}
              target="_blank"
              rel="noopener noreferrer"
              className="sidebar-item"
              onClick={handleMenuItemClick}
            >
              <div className="sidebar-item-icon" style={{ color }}>
                <Icon size={20} />
              </div>
              <span className="sidebar-item-text">{name}</span>
            </a>
          ) : (
            <Link
              key={id}
              to={path}
              className={`sidebar-item ${location.pathname === path ? 'active' : ''}`}
              onClick={handleMenuItemClick}
            >
              <div className="sidebar-item-icon" style={{ color }}>
                <Icon size={20} />
              </div>
              <span className="sidebar-item-text">{name}</span>
            </Link>
          )
        ))}
        
        {/* 관리자 메뉴 (관리자 계정일 때만 표시) */}
        {currentUser && (currentUser.email === 'tambleofficial@gmail.com' || currentUser.email === 'tambleofficial01@gmail.com') && (
          <>
            <div className="admin-separator"></div>
            {adminMenuItems.map(({ id, name, icon: Icon, path, color }) => (
              <Link
                key={id}
                to={path}
                className={`sidebar-item admin-item ${location.pathname === path ? 'active' : ''}`}
                onClick={handleMenuItemClick}
              >
                <div className="sidebar-item-icon" style={{ color }}>
                  <Icon size={20} />
                </div>
                <span className="sidebar-item-text">{name}</span>
              </Link>
            ))}
          </>
        )}
      </nav>

      {/* Business Information */}
      <div className="business-info">
        <button 
          className="business-info-toggle"
          onClick={() => setBusinessInfoOpen(!businessInfoOpen)}
        >
          <span>Sociality 사업자정보</span>
          {businessInfoOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        
        {businessInfoOpen && (
          <div className="business-info-content">
            <div className="info-item">
              <strong>상호명:</strong> 탬블(tamble)
            </div>
            <div className="info-item">
              <strong>대표:</strong> 서동현
            </div>
            <div className="info-item">
              <strong>주소:</strong> 충북 청주시 상당구 사직대로361번길 158-10 3R-7
            </div>
            <div className="info-item">
              <strong>사업자번호:</strong> 869-02-02736
            </div>
            <div className="info-item">
              <strong>통신판매:</strong> 2023-충북청주-3089호
            </div>
            <div className="info-item">
              <strong>이메일:</strong> tambleofficial@gmail.com
            </div>
            <div className="info-links">
              <a href="https://drive.google.com/file/d/1Nn3ABQFUbRSUpD25IAdyJrfjBbDn70Ji/view?usp=sharing" target="_blank">이용약관</a>
              <a href="https://drive.google.com/file/d/1PWCtiDv_tFrP2EyNVaQw4CY-pi0K5Hrc/view?usp=sharing" target="_blank">개인정보처리방침</a>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
