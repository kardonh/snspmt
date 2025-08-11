import React from 'react'
import { Link } from 'react-router-dom'
import { Instagram, Youtube, MessageCircle, Facebook, Twitter } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './Home.css'

const Home = () => {
  const { currentUser } = useAuth()
  
  const platforms = [
    { id: 'instagram', name: '인스타그램', icon: Instagram, description: '팔로워, 좋아요, 댓글 서비스' },
    { id: 'youtube', name: '유튜브', icon: Youtube, description: '구독자, 좋아요, 조회수 서비스' },
    { id: 'tiktok', name: '틱톡', icon: MessageCircle, description: '팔로워, 좋아요, 조회수 서비스' },
    { id: 'facebook', name: '페이스북', icon: Facebook, description: '페이지 좋아요, 팔로워 서비스' },
    { id: 'twitter', name: '트위터', icon: Twitter, description: '팔로워, 리트윗, 좋아요 서비스' }
  ]

  return (
    <div className="home">
      <div className="hero">
        <h1>SNSINTO</h1>
        {currentUser ? (
          <>
            <p>안녕하세요, {currentUser.displayName || currentUser.email}님!</p>
            <p>소셜미디어 마케팅의 새로운 시작을 경험해보세요</p>
          </>
        ) : (
          <>
            <p>소셜미디어 마케팅의 새로운 시작</p>
            <p>서비스를 이용하려면 <Link to="/login" className="login-link">로그인</Link>이 필요합니다</p>
          </>
        )}
      </div>
      
      <div className="platforms-grid">
        {platforms.map(({ id, name, icon: Icon, description }) => (
          <Link key={id} to={`/order/${id}`} className="platform-card">
            <div className="platform-icon">
              <Icon size={48} />
            </div>
            <h3>{name}</h3>
            <p>{description}</p>
          </Link>
        ))}
      </div>
      
      <div className="features">
        <h2>왜 SNSINTO인가요?</h2>
        <div className="features-grid">
          <div className="feature">
            <h3>빠른 서비스</h3>
            <p>주문 후 즉시 서비스가 시작됩니다</p>
          </div>
          <div className="feature">
            <h3>안전한 결제</h3>
            <p>안전한 결제 시스템으로 보호받습니다</p>
          </div>
          <div className="feature">
            <h3>24/7 고객지원</h3>
            <p>언제든지 문의하실 수 있습니다</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
