import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  Instagram, 
  Youtube, 
  MessageCircle, 
  Facebook, 
  Twitter, 
  Zap, 
  Shield, 
  Headphones,
  Users,
  TrendingUp,
  Star,
  ArrowRight,
  CheckCircle,
  Play,
  Award,
  Clock,
  Globe
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './Home.css'

const Home = () => {
  const { currentUser, loading } = useAuth()
  const [animateStats, setAnimateStats] = useState(false)
  
  const platforms = [
    { 
      id: 'instagram', 
      name: '인스타그램', 
      icon: Instagram, 
      description: '팔로워, 좋아요, 댓글 서비스',
      color: '#E4405F',
      stats: '100만+ 팔로워'
    },
    { 
      id: 'youtube', 
      name: '유튜브', 
      icon: Youtube, 
      description: '구독자, 좋아요, 조회수 서비스',
      color: '#FF0000',
      stats: '50만+ 구독자'
    },
    { 
      id: 'tiktok', 
      name: '틱톡', 
      icon: MessageCircle, 
      description: '팔로워, 좋아요, 조회수 서비스',
      color: '#000000',
      stats: '200만+ 팔로워'
    },
    { 
      id: 'facebook', 
      name: '페이스북', 
      icon: Facebook, 
      description: '페이지 좋아요, 팔로워 서비스',
      color: '#1877F2',
      stats: '80만+ 좋아요'
    },
    { 
      id: 'twitter', 
      name: '트위터', 
      icon: Twitter, 
      description: '팔로워, 리트윗, 좋아요 서비스',
      color: '#1DA1F2',
      stats: '150만+ 팔로워'
    }
  ]

  const features = [
    {
      icon: Zap,
      title: '빠른 서비스',
      description: '주문 후 즉시 서비스가 시작됩니다',
      color: '#F59E0B'
    },
    {
      icon: Shield,
      title: '안전한 결제',
      description: '안전한 결제 시스템으로 보호받습니다',
      color: '#10B981'
    },
    {
      icon: Headphones,
      title: '24/7 고객지원',
      description: '언제든지 문의하실 수 있습니다',
      color: '#3B82F6'
    }
  ]

  const stats = [
    { icon: Users, number: '10,000+', label: '만족한 고객', color: '#3B82F6' },
    { icon: TrendingUp, number: '500만+', label: '총 팔로워', color: '#10B981' },
    { icon: Star, number: '4.9', label: '평균 평점', color: '#F59E0B' },
    { icon: Clock, number: '24시간', label: '평균 소요시간', color: '#8B5CF6' }
  ]

  const testimonials = [
    {
      name: '김민수',
      platform: '인스타그램',
      content: '정말 빠르고 안전한 서비스였어요! 팔로워가 확실히 늘어났습니다.',
      rating: 5
    },
    {
      name: '이지영',
      platform: '유튜브',
      content: '구독자 수가 급격히 증가했고, 수익도 함께 올랐습니다. 추천합니다!',
      rating: 5
    },
    {
      name: '박준호',
      platform: '틱톡',
      content: '틱톡 팔로워가 3배로 늘어났어요. 정말 만족스럽습니다.',
      rating: 5
    }
  ]

  useEffect(() => {
    const timer = setTimeout(() => setAnimateStats(true), 500)
    return () => clearTimeout(timer)
  }, [])

  // 로딩 중일 때는 기본 내용만 표시
  if (loading) {
    return (
      <div className="home">
        <div className="hero">
          <div className="hero-content">
            <h1 className="hero-title">
              <span className="gradient-text">SNSINTO</span>
            </h1>
            <p className="hero-description">로딩 중...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="home">
      {/* Hero Section */}
      <div className="hero">
        <div className="hero-background">
          <div className="hero-particles"></div>
        </div>
        <div className="hero-content">
          <div className="hero-badge">
            <Award size={16} />
            <span>2024년 최고의 SNS 마케팅 서비스</span>
          </div>
          <h1 className="hero-title">
            <span className="gradient-text">SNSINTO</span>
            <span className="hero-subtitle-text">소셜미디어 마케팅의 새로운 시작</span>
          </h1>
          {currentUser ? (
            <>
              <p className="hero-greeting">
                안녕하세요, <span className="user-name">{currentUser.displayName || currentUser.email}</span>님!
              </p>
              <p className="hero-description">
                소셜미디어 마케팅의 새로운 시작을 경험해보세요
              </p>
              <div className="hero-actions">
                <Link to="/order/instagram" className="hero-cta-primary">
                  서비스 시작하기
                  <ArrowRight size={20} />
                </Link>
                <Link to="/orders" className="hero-cta-secondary">
                  주문 내역 보기
                </Link>
              </div>
            </>
          ) : (
            <>
              <p className="hero-description">
                서비스를 이용하려면{' '}
                <Link to="/login" className="login-link">로그인</Link>이 필요합니다
              </p>
              <div className="hero-actions">
                <Link to="/login" className="hero-cta-primary">
                  로그인하기
                  <ArrowRight size={20} />
                </Link>
                <Link to="/signup" className="hero-cta-secondary">
                  회원가입
                </Link>
              </div>
            </>
          )}
        </div>
        <div className="hero-visual">
          <div className="floating-card card-1">
            <Instagram size={24} />
            <span>+1,234</span>
          </div>
          <div className="floating-card card-2">
            <Youtube size={24} />
            <span>+567</span>
          </div>
          <div className="floating-card card-3">
            <MessageCircle size={24} />
            <span>+890</span>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="stats-section">
        <div className="container">
          <div className="stats-grid">
            {stats.map(({ icon: Icon, number, label, color }, index) => (
              <div key={index} className={`stat-card ${animateStats ? 'animate' : ''}`}>
                <div className="stat-icon" style={{ color }}>
                  <Icon size={32} />
                </div>
                <div className="stat-number">{number}</div>
                <div className="stat-label">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {/* Platforms Section */}
      <div className="platforms-section">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">플랫폼 선택</h2>
            <p className="section-description">
              원하는 소셜미디어 플랫폼을 선택하고 서비스를 시작하세요
            </p>
          </div>
          <div className="platforms-grid">
            {platforms.map(({ id, name, icon: Icon, description, color, stats }) => (
              <Link key={id} to={`/order/${id}`} className="platform-card">
                <div className="platform-header">
                  <div className="platform-icon" style={{ color }}>
                    <Icon size={32} />
                  </div>
                  <div className="platform-stats">{stats}</div>
                </div>
                <h3 className="platform-name">{name}</h3>
                <p className="platform-description">{description}</p>
                <div className="platform-features">
                  <div className="feature-item">
                    <CheckCircle size={16} />
                    <span>즉시 시작</span>
                  </div>
                  <div className="feature-item">
                    <CheckCircle size={16} />
                    <span>안전 보장</span>
                  </div>
                </div>
                <div className="platform-arrow">
                  <ArrowRight size={20} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
      
      {/* Features Section */}
      <div className="features-section">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">왜 SNSINTO인가요?</h2>
            <p className="section-description">
              믿을 수 있는 서비스로 여러분의 소셜미디어를 성장시켜드립니다
            </p>
          </div>
          <div className="features-grid">
            {features.map(({ icon: Icon, title, description, color }, index) => (
              <div key={index} className="feature-card">
                <div className="feature-icon" style={{ color }}>
                  <Icon size={24} />
                </div>
                <h3 className="feature-title">{title}</h3>
                <p className="feature-description">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Testimonials Section */}
      <div className="testimonials-section">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">고객 후기</h2>
            <p className="section-description">
              실제 고객들의 생생한 후기를 확인해보세요
            </p>
          </div>
          <div className="testimonials-grid">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="testimonial-card">
                <div className="testimonial-header">
                  <div className="testimonial-avatar">
                    {testimonial.name.charAt(0)}
                  </div>
                  <div className="testimonial-info">
                    <h4 className="testimonial-name">{testimonial.name}</h4>
                    <p className="testimonial-platform">{testimonial.platform}</p>
                  </div>
                  <div className="testimonial-rating">
                    {[...Array(testimonial.rating)].map((_, i) => (
                      <Star key={i} size={16} fill="#F59E0B" color="#F59E0B" />
                    ))}
                  </div>
                </div>
                <p className="testimonial-content">{testimonial.content}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="cta-section">
        <div className="container">
          <div className="cta-content">
            <h2 className="cta-title">지금 시작하세요!</h2>
            <p className="cta-description">
              소셜미디어 마케팅의 새로운 차원을 경험해보세요
            </p>
            <div className="cta-actions">
              {currentUser ? (
                <Link to="/order/instagram" className="cta-button primary">
                  서비스 시작하기
                  <ArrowRight size={20} />
                </Link>
              ) : (
                <>
                  <Link to="/login" className="cta-button primary">
                    로그인하기
                    <ArrowRight size={20} />
                  </Link>
                  <Link to="/signup" className="cta-button secondary">
                    회원가입
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
