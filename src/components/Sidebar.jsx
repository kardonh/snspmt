import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { Instagram, Youtube, MessageCircle, Facebook, Twitter, MessageSquare } from 'lucide-react'
import './Sidebar.css'

const Sidebar = () => {
  const { platform } = useParams()
  
  const platforms = [
    { id: 'instagram', name: '인스타그램', icon: Instagram, path: '/order/instagram' },
    { id: 'youtube', name: '유튜브', icon: Youtube, path: '/order/youtube' },
    { id: 'tiktok', name: '틱톡', icon: MessageCircle, path: '/order/tiktok' },
    { id: 'facebook', name: '페이스북', icon: Facebook, path: '/order/facebook' },
    { id: 'twitter', name: '트위터', icon: Twitter, path: '/order/twitter' },
    { id: 'kakao', name: '카카오', icon: MessageSquare, path: '/order/kakao' }
  ]

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        {platforms.map(({ id, name, icon: Icon, path }) => (
          <Link
            key={id}
            to={path}
            className={`sidebar-item ${platform === id ? 'active' : ''}`}
          >
            <Icon size={20} />
            <span>{name}</span>
          </Link>
        ))}
      </nav>
    </aside>
  )
}

export default Sidebar
