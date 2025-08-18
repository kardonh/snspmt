import React from 'react'
import { Star, Users, Heart, Eye, MessageCircle, Instagram, Youtube, Facebook, Twitter, Globe, CheckCircle, Shield, Clock, Zap } from 'lucide-react'
import './ServicePage.css'

const ServicePage = () => {
  const platforms = [
    {
      id: 'instagram',
      name: '인스타그램',
      icon: Instagram,
      color: '#e4405f',
      description: '팔로워, 좋아요, 댓글, 조회수 서비스',
      services: [
        { name: '팔로워 늘리기', icon: Users, description: '한국인/외국인 팔로워' },
        { name: '좋아요 늘리기', icon: Heart, description: '게시물 좋아요 증가' },
        { name: '댓글 늘리기', icon: MessageCircle, description: '커스텀 댓글 서비스' },
        { name: '조회수 늘리기', icon: Eye, description: '동영상 조회수 증가' }
      ]
    },
    {
      id: 'youtube',
      name: '유튜브',
      icon: Youtube,
      color: '#ff0000',
      description: '구독자, 조회수, 좋아요, 댓글 서비스',
      services: [
        { name: '구독자 늘리기', icon: Users, description: '한국인/외국인 구독자' },
        { name: '조회수 늘리기', icon: Eye, description: '동영상 조회수 증가' },
        { name: '좋아요 늘리기', icon: Heart, description: '동영상 좋아요 증가' },
        { name: '댓글 늘리기', icon: MessageCircle, description: 'AI 댓글 서비스' }
      ]
    },
    {
      id: 'facebook',
      name: '페이스북',
      icon: Facebook,
      color: '#1877f2',
      description: '페이지 좋아요, 팔로워, 게시물 서비스',
      services: [
        { name: '페이지 좋아요', icon: Heart, description: '페이스북 페이지 좋아요' },
        { name: '팔로워 늘리기', icon: Users, description: '페이지 팔로워 증가' },
        { name: '게시물 좋아요', icon: Heart, description: '게시물 좋아요 증가' },
        { name: '게시물 댓글', icon: MessageCircle, description: '게시물 댓글 서비스' }
      ]
    },
    {
      id: 'tiktok',
      name: '틱톡',
      icon: MessageCircle,
      color: '#000000',
      description: '팔로워, 좋아요, 조회수 서비스',
      services: [
        { name: '팔로워 늘리기', icon: Users, description: '틱톡 팔로워 증가' },
        { name: '좋아요 늘리기', icon: Heart, description: '동영상 좋아요 증가' },
        { name: '조회수 늘리기', icon: Eye, description: '동영상 조회수 증가' },
        { name: '공유 늘리기', icon: MessageCircle, description: '동영상 공유 증가' }
      ]
    },
    {
      id: 'twitter',
      name: '트위터',
      icon: Twitter,
      color: '#1da1f2',
      description: '팔로워, 리트윗, 좋아요 서비스',
      services: [
        { name: '팔로워 늘리기', icon: Users, description: '트위터 팔로워 증가' },
        { name: '리트윗 늘리기', icon: MessageCircle, description: '트윗 리트윗 증가' },
        { name: '좋아요 늘리기', icon: Heart, description: '트윗 좋아요 증가' },
        { name: '답글 늘리기', icon: MessageCircle, description: '트윗 답글 서비스' }
      ]
    },
    {
      id: 'naver',
      name: '네이버',
      icon: Globe,
      color: '#03c75a',
      description: '블로그, 카페 서비스',
      services: [
        { name: '블로그 방문자', icon: Users, description: '블로그 방문자 증가' },
        { name: '카페 회원', icon: Users, description: '카페 회원 증가' },
        { name: '포스트 조회수', icon: Eye, description: '포스트 조회수 증가' },
        { name: '댓글 늘리기', icon: MessageCircle, description: '댓글 서비스' }
      ]
    }
  ]

  const features = [
    {
      icon: Shield,
      title: '안전한 서비스',
      description: '모든 서비스는 안전한 방법으로 제공되며, 계정에 해를 끼치지 않습니다.'
    },
    {
      icon: Clock,
      title: '24시간 운영',
      description: '24시간 자동으로 서비스가 운영되어 언제든지 주문하실 수 있습니다.'
    },
    {
      icon: Zap,
      title: '빠른 처리',
      description: '주문 후 5-30분 내에 작업이 시작되어 빠르게 결과를 확인하실 수 있습니다.'
    },
    {
      icon: CheckCircle,
      title: '품질 보장',
      description: '모든 서비스는 실제 유저를 통해 작업되며, 품질을 보장합니다.'
    }
  ]

  return (
    <div className="service-page">
      <div className="service-header">
        <h1>서비스 소개서</h1>
        <p>SNS샵에서 제공하는 다양한 소셜미디어 마케팅 서비스를 소개합니다</p>
      </div>

      <div className="service-features">
        <h2>서비스 특징</h2>
        <div className="features-grid">
          {features.map((feature, index) => (
            <div key={index} className="feature-item">
              <div className="feature-icon">
                <feature.icon size={32} />
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="platforms-section">
        <h2>지원 플랫폼</h2>
        <div className="platforms-grid">
          {platforms.map((platform) => (
            <div key={platform.id} className="platform-card">
              <div className="platform-header">
                <div className="platform-icon" style={{ color: platform.color }}>
                  <platform.icon size={32} />
                </div>
                <div className="platform-info">
                  <h3>{platform.name}</h3>
                  <p>{platform.description}</p>
                </div>
              </div>
              
              <div className="platform-services">
                <h4>제공 서비스</h4>
                <div className="services-grid">
                  {platform.services.map((service, index) => (
                    <div key={index} className="service-card">
                      <div className="service-icon">
                        <service.icon size={20} />
                      </div>
                      <div className="service-info">
                        <h5>{service.name}</h5>
                        <p>{service.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="service-stats">
        <h2>서비스 현황</h2>
        <div className="stats-grid">
          <div className="stat-item">
            <div className="stat-number">50,000+</div>
            <div className="stat-label">만족한 고객</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">1,000,000+</div>
            <div className="stat-label">완료된 주문</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">99.9%</div>
            <div className="stat-label">성공률</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">24/7</div>
            <div className="stat-label">고객 지원</div>
          </div>
        </div>
      </div>

      <div className="service-cta">
        <h2>지금 시작하세요</h2>
        <p>SNS샵과 함께 소셜미디어 마케팅을 성공으로 이끌어보세요</p>
        <button className="cta-button">
          <Star size={20} />
          주문하기
        </button>
      </div>
    </div>
  )
}

export default ServicePage
