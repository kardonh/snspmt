import React from 'react'
import { Star, Users, Heart, Eye, MessageCircle, Instagram, Youtube, Facebook, Twitter, Globe, CheckCircle, Shield, Clock, Zap } from 'lucide-react'
import './ServicePage.css'

const ServicePage = () => {
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
