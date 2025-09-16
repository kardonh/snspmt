import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Instagram, 
  Youtube, 
  MessageCircle,
  Users,
  Heart,
  Eye,
  TrendingUp,
  CheckCircle,
  Star,
  Zap
} from 'lucide-react';
import './ServicesPage.css';

// Force redeploy - Fix 503 Service Unavailable error
const ServicesPage = () => {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const navigate = useNavigate();

  // 실제 주문 시스템과 호환되는 서비스 ID 매핑
  const services = {
    instagram: [
      {
        id: 'followers_korean',
        name: 'Instagram 팔로워 (한국인)',
        description: '실제 한국인 사용자 팔로워 증가',
        icon: <Users size={24} />,
        features: ['실제 한국인 사용자', '영구 보장', '24시간 내 시작', '자연스러운 증가'],
        price: '120원',
        delivery: '24-48시간',
        minQuantity: 100,
        maxQuantity: 20000,
        apiId: 361
      },
      {
        id: 'followers_foreign',
        name: 'Instagram 팔로워 (외국인)',
        description: '실제 외국인 사용자 팔로워 증가',
        icon: <Users size={24} />,
        features: ['실제 외국인 사용자', '영구 보장', '24시간 내 시작', '자연스러운 증가'],
        price: '1원',
        delivery: '24-48시간',
        minQuantity: 100,
        maxQuantity: 2000,
        apiId: 472
      },
      {
        id: 'likes_korean',
        name: 'Instagram 좋아요 (한국인)',
        description: '포스트 좋아요 수 증가',
        icon: <Heart size={24} />,
        features: ['실제 한국인 좋아요', '즉시 적용', '안전한 서비스', '자연스러운 비율'],
        price: '120원',
        delivery: '즉시',
        minQuantity: 50,
        maxQuantity: 5000,
        apiId: 122
      },
      {
        id: 'views_korean',
        name: 'Instagram 조회수 (한국인)',
        description: '스토리/릴스 조회수 증가',
        icon: <Eye size={24} />,
        features: ['실제 조회수', '즉시 적용', '자연스러운 증가', '안전한 서비스'],
        price: '120원',
        delivery: '즉시',
        minQuantity: 100,
        maxQuantity: 10000,
        apiId: 124
      }
    ],
    youtube: [
      {
        id: 'subscribers_foreign',
        name: 'YouTube 구독자 (외국인)',
        description: '실제 외국인 구독자 수 증가',
        icon: <Users size={24} />,
        features: ['실제 외국인 구독자', '영구 보장', '자연스러운 증가', '알고리즘 친화적'],
        price: '30원',
        delivery: '24-72시간',
        minQuantity: 100,
        maxQuantity: 5000,
        apiId: 1001
      },
      {
        id: 'views_foreign',
        name: 'YouTube 조회수 (외국인)',
        description: '동영상 조회수 증가',
        icon: <Eye size={24} />,
        features: ['실제 조회수', '즉시 적용', '자연스러운 증가', '알고리즘 최적화'],
        price: '30원',
        delivery: '즉시',
        minQuantity: 1000,
        maxQuantity: 100000,
        apiId: 1002
      }
    ],
    tiktok: [
      {
        id: 'followers_foreign',
        name: 'TikTok 팔로워 (외국인)',
        description: '실제 외국인 팔로워 수 증가',
        icon: <Users size={24} />,
        features: ['실제 외국인 사용자', '영구 보장', '24시간 내 시작', '자연스러운 증가'],
        price: '22원',
        delivery: '24-48시간',
        minQuantity: 100,
        maxQuantity: 10000,
        apiId: 702
      },
      {
        id: 'likes_foreign',
        name: 'TikTok 좋아요 (외국인)',
        description: '동영상 좋아요 수 증가',
        icon: <Heart size={24} />,
        features: ['실제 외국인 좋아요', '즉시 적용', '자연스러운 비율', '알고리즘 최적화'],
        price: '22원',
        delivery: '즉시',
        minQuantity: 100,
        maxQuantity: 10000,
        apiId: 244
      }
    ]
  };

  const categories = [
    { id: 'all', name: '전체 서비스', icon: <Zap size={20} /> },
    { id: 'instagram', name: 'Instagram', icon: <Instagram size={20} /> },
    { id: 'youtube', name: 'YouTube', icon: <Youtube size={20} /> },
    { id: 'tiktok', name: 'TikTok', icon: <MessageCircle size={20} /> }
  ];

  const getFilteredServices = () => {
    if (selectedCategory === 'all') {
      return Object.values(services).flat();
    }
    return services[selectedCategory] || [];
  };

  const handleOrder = (service) => {
    // 플랫폼과 서비스 ID를 추출하여 주문 페이지로 이동
    const platform = Object.keys(services).find(key => 
      services[key].some(s => s.id === service.id)
    );
    
    if (platform && service.id) {
      navigate(`/order/${platform}/${service.id}`);
    } else {
      alert('주문할 수 없는 서비스입니다.');
    }
  };

  return (
    <div className="services-page">
      <div className="services-container">
        {/* 헤더 섹션 */}
        <div className="services-header">
          <div className="logo-container">
            <div className="logo">Sociality</div>
          </div>
          <h1 className="services-title">SNS 서비스</h1>
          <p className="services-subtitle">
            Instagram, YouTube, TikTok 등 다양한 소셜미디어 서비스를 제공합니다
          </p>
        </div>

        {/* 카테고리 필터 */}
        <div className="category-filter">
          {categories.map((category) => (
            <button
              key={category.id}
              className={`category-btn ${selectedCategory === category.id ? 'active' : ''}`}
              onClick={() => setSelectedCategory(category.id)}
            >
              {category.icon}
              <span>{category.name}</span>
            </button>
          ))}
        </div>

        {/* 서비스 그리드 */}
        <div className="services-grid">
          {getFilteredServices().map((service) => (
            <div key={service.id} className="service-card">
              <div className="service-header">
                <div className="service-icon">
                  {service.icon}
                </div>
                <div className="service-info">
                  <h3 className="service-name">{service.name}</h3>
                  <p className="service-description">{service.description}</p>
                </div>
              </div>

              <div className="service-features">
                <h4>주요 특징</h4>
                <ul className="features-list">
                  {service.features.map((feature, index) => (
                    <li key={index} className="feature-item">
                      <CheckCircle size={16} />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="service-details">
                <div className="detail-row">
                  <span className="detail-label">가격:</span>
                  <span className="detail-value price">{service.price}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">배송:</span>
                  <span className="detail-value">{service.delivery}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">수량:</span>
                  <span className="detail-value">
                    {service.minQuantity.toLocaleString()} - {service.maxQuantity.toLocaleString()}
                  </span>
                </div>
              </div>

                              <div className="service-actions">
                  <button className="order-btn" onClick={() => handleOrder(service)}>
                    <Star size={16} />
                    주문하기
                  </button>
                <button className="info-btn">
                  <MessageCircle size={16} />
                  상세정보
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* 추가 정보 섹션 */}
        <div className="services-info">
          <div className="info-card">
            <h3>💡 서비스 이용 가이드</h3>
            <ul>
              <li>모든 서비스는 실제 사용자와 데이터를 사용합니다</li>
              <li>24시간 내 서비스가 시작되며, 안전하게 진행됩니다</li>
              <li>서비스 완료 후 30일간 보장 서비스를 제공합니다</li>
              <li>문의사항이 있으시면 고객센터로 연락해주세요</li>
            </ul>
          </div>

          <div className="info-card">
            <h3>🔒 보안 및 안전성</h3>
            <ul>
              <li>개인정보는 암호화되어 안전하게 보호됩니다</li>
              <li>모든 거래는 SSL 보안 연결을 통해 진행됩니다</li>
              <li>서비스 진행 상황을 실시간으로 확인할 수 있습니다</li>
              <li>문제 발생 시 즉시 환불 및 재처리를 보장합니다</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServicesPage;
