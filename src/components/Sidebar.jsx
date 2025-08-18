import React, { useState } from 'react'
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
  X
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './Sidebar.css'

const Sidebar = ({ onClose }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const { currentUser, logout } = useAuth()
  const [businessInfoOpen, setBusinessInfoOpen] = useState(false)

  const menuItems = [
    { id: 'order', name: '주문하기', icon: Star, path: '/', color: '#3b82f6' },
    { id: 'info', name: '상품안내 및 주문방법', icon: Info, path: '/info', color: '#10b981' },
    { id: 'faq', name: '자주 묻는 질문', icon: HelpCircle, path: '/faq', color: '#f59e0b' },
    { id: 'service', name: '서비스 소개서', icon: FileText, path: '/service', color: '#6b7280' }
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
    if (onClose) {
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
        <h2>SNSinto</h2>
      </div>

      {/* User Status */}
      <div className="user-status">
        {currentUser ? (
          <div className="user-info">
            <span className="user-name">{currentUser.displayName || currentUser.email}</span>
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
      </nav>

      {/* Business Information */}
      <div className="business-info">
        <button 
          className="business-info-toggle"
          onClick={() => setBusinessInfoOpen(!businessInfoOpen)}
        >
          <span>SNSinto 사업자정보</span>
          {businessInfoOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        
        {businessInfoOpen && (
          <div className="business-info-content">
            <div className="info-item">
              <strong>상호명:</strong> 스마일드래곤주식회사
            </div>
            <div className="info-item">
              <strong>대표:</strong> 대표 이상필, 문영화
            </div>
            <div className="info-item">
              <strong>주소:</strong> 경기 고양시 일산동구 백마로 195, SK 엠시티타워 일반동 13F
            </div>
            <div className="info-item">
              <strong>사업자번호:</strong> 813-87-01236
            </div>
            <div className="info-item">
              <strong>통신판매:</strong> 제2019-고양일산동-1344
            </div>
            <div className="info-item">
              <strong>대표번호:</strong> 1877-6533
            </div>
            <div className="info-item">
              <strong>이메일:</strong> cs@snsshop.kr
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
