import React from 'react'
import { useLocation, Link } from 'react-router-dom'
import { 
  Star, 
  FileText, 
  Info, 
  HelpCircle, 
  Shield,
  CreditCard,
  Package
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './BottomTabBar.css'

const BottomTabBar = () => {
  const location = useLocation()
  const { currentUser, setShowAuthModal } = useAuth()

  const tabItems = [
    { id: 'order', name: '주문하기', icon: Star, path: '/', color: '#3b82f6' },
    { id: 'orders', name: '주문내역', icon: FileText, path: '/orders', color: '#8b5cf6' },
    { id: 'points', name: '포인트 구매', icon: CreditCard, path: '/points', color: '#f59e0b' },
    { id: 'info', name: '상품안내', icon: Info, path: '/info', color: '#10b981' }
  ]

  // 관리자 탭 (관리자 계정일 때만 표시)
  const adminTab = { id: 'admin', name: '관리자', icon: Shield, path: '/admin', color: '#dc2626' }

  return (
    <div className="bottom-tab-bar">
      {tabItems.map(({ id, name, icon: Icon, path, color }) => (
        <Link
          key={id}
          to={path}
          className={`tab-item ${location.pathname === path ? 'active' : ''}`}
        >
          <div className="tab-icon" style={{ color: location.pathname === path ? color : '#6b7280' }}>
            <Icon size={20} />
          </div>
          <span className="tab-label">{name}</span>
        </Link>
      ))}
      
      {/* 관리자 탭 (관리자 계정일 때만 표시) */}
      {currentUser && (currentUser.email === 'tambleofficial@gmail.com' || currentUser.email === 'tambleofficial01@gmail.com') && (
        <Link
          to={adminTab.path}
          className={`tab-item admin-tab ${location.pathname === adminTab.path ? 'active' : ''}`}
        >
          <div className="tab-icon" style={{ color: location.pathname === adminTab.path ? adminTab.color : '#6b7280' }}>
            <adminTab.icon size={20} />
          </div>
          <span className="tab-label">{adminTab.name}</span>
        </Link>
      )}
    </div>
  )
}

export default BottomTabBar
