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
  Coins
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './Sidebar.css'

const Sidebar = ({ onClose }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const { currentUser, logout } = useAuth()
  const [businessInfoOpen, setBusinessInfoOpen] = useState(false)
  const [userPoints, setUserPoints] = useState(0)
  const [pointsLoading, setPointsLoading] = useState(false)

  // 사용자 포인트 조회 함수
  const fetchUserPoints = async () => {
    if (!currentUser) return
    
    setPointsLoading(true)
    try {
      const response = await fetch('/api/points', {
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

  // 사용자가 로그인했을 때 포인트 조회
  useEffect(() => {
    if (currentUser) {
      fetchUserPoints()
    } else {
      setUserPoints(0)
    }
  }, [currentUser])

  const menuItems = [
    { id: 'order', name: '주문하기', icon: Star, path: '/', color: '#3b82f6' },
    { id: 'orders', name: '주문내역', icon: FileText, path: '/orders', color: '#8b5cf6' },
    { id: 'points', name: '포인트 구매', icon: CreditCard, path: '/points', color: '#f59e0b' },
    { id: 'info', name: '상품안내 및 주문방법', icon: Info, path: '/info', color: '#10b981' },
    { id: 'faq', name: '자주 묻는 질문', icon: HelpCircle, path: '/faq', color: '#f59e0b' },
    { id: 'service', name: '서비스 소개서', icon: FileText, path: '/service', color: '#6b7280' }
  ]

  // 관리자 메뉴 아이템 (관리자 계정일 때만 표시)
  const adminMenuItems = [
    { id: 'admin', name: '관리자 대시보드', icon: Shield, path: '/admin', color: '#dc2626' }
  ]

  const handleSignOut = async () => {
    try {
      await logout()
      alert('로그아웃되었습니다.')
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
        <h2>Sociality</h2>
      </div>

      {/* User Status */}
      <div className="user-status">
        {currentUser ? (
          <div className="user-info">
            <span className="user-name">{currentUser.displayName || currentUser.email}</span>
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
            <span>guest</span>
          </div>
        )}
      </div>

      {/* Navigation Menu */}
      <nav className="sidebar-nav">
        {menuItems.map(({ id, name, icon: Icon, path, color }) => (
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
        ))}
        
        {/* 관리자 메뉴 (관리자 계정일 때만 표시) */}
        {currentUser && currentUser.email === 'tambleofficial@gmail.com' && (
          console.log('Rendering admin menu for:', currentUser.email),
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
              <strong>상호명:</strong> tamble
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
              <strong>통신판매:</strong> 신고예정
            </div>
            <div className="info-item">
              <strong>연락처:</strong> 준비중
            </div>
            <div className="info-item">
              <strong>이메일:</strong> 준비중
            </div>
            <div className="info-links">
              <a href="/terms">이용약관</a>
              <a href="/privacy">개인정보취급방침</a>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
