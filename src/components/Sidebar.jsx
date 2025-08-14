import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { Instagram, Youtube, MessageCircle, Facebook, Twitter, Settings, BarChart3 } from 'lucide-react'
import './Sidebar.css'

const Sidebar = () => {
  const { platform } = useParams()
  
  const platforms = [
    { id: 'instagram', name: '인스타그램', icon: Instagram, path: '/order/instagram', color: '#E4405F' },
    { id: 'youtube', name: '유튜브', icon: Youtube, path: '/order/youtube', color: '#FF0000' },
    { id: 'tiktok', name: '틱톡', icon: MessageCircle, path: '/order/tiktok', color: '#000000' },
    { id: 'facebook', name: '페이스북', icon: Facebook, path: '/order/facebook', color: '#1877F2' },
    { id: 'twitter', name: '트위터', icon: Twitter, path: '/order/twitter', color: '#1DA1F2' }
  ]

  const additionalLinks = [
    { id: 'orders', name: '주문 내역', icon: BarChart3, path: '/orders', color: '#10B981' },
    { id: 'settings', name: '설정', icon: Settings, path: '/settings', color: '#6B7280' }
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h3 className="sidebar-title">플랫폼 선택</h3>
        <p className="sidebar-subtitle">원하는 서비스를 선택하세요</p>
      </div>
      
      <div className="sidebar-section">
        <h4 className="sidebar-section-title">소셜미디어</h4>
        <nav className="sidebar-nav">
          {platforms.map(({ id, name, icon: Icon, path, color }) => (
            <Link
              key={id}
              to={path}
              className={`sidebar-item ${platform === id ? 'active' : ''}`}
            >
              <div className="sidebar-item-icon" style={{ color }}>
                <Icon size={20} />
              </div>
              <span className="sidebar-item-text">{name}</span>
            </Link>
          ))}
        </nav>
      </div>
      
      <div className="sidebar-section">
        <h4 className="sidebar-section-title">계정</h4>
        <nav className="sidebar-nav">
          {additionalLinks.map(({ id, name, icon: Icon, path, color }) => (
            <Link
              key={id}
              to={path}
              className="sidebar-item"
            >
              <div className="sidebar-item-icon" style={{ color }}>
                <Icon size={20} />
              </div>
              <span className="sidebar-item-text">{name}</span>
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  )
}

export default Sidebar
