import React, { useState } from 'react'
import { ChevronDown, ChevronUp, Info, Star, Users, Heart, Eye, MessageCircle } from 'lucide-react'
import './InfoPage.css'

const InfoPage = () => {
  const [selectedService, setSelectedService] = useState('all')
  const [expandedItems, setExpandedItems] = useState({})

  const toggleExpanded = (id) => {
    setExpandedItems(prev => ({
      ...prev,
      [id]: !prev[id]
    }))
  }

  const services = [
    {
      id: 'instagram-likes',
      name: '인스타그램 좋아요 늘리기 서비스란?',
      description: '인스타그램 게시물의 좋아요를 늘려주는 서비스입니다. 인스타그램에서 좋아요는 게시물의 신뢰도와 인기도를 나타내는 지표이며, 좋아요가 많을수록 인기게시물로 선정될 확률이 높아집니다.',
      tip: '좋아요+도달률 서비스를 같이 이용하시면 인기게시물 확률이 더욱 증가합니다.',
      icon: Heart
    },
    {
      id: 'instagram-auto-likes',
      name: '인스타그램 자동 좋아요 늘리기 서비스란?',
      description: '인스타그램에 사진을 업로드할 때마다 자동으로 좋아요가 증가하는 서비스입니다. 기존 게시물에는 적용되지 않고 향후 업로드되는 게시물에만 적용됩니다. 좋아요가 자동으로 증가하기 때문에 편리한 게시물 관리가 가능한 인기 서비스입니다.',
      tip: '자동 좋아요+자동 도달률 서비스를 같이 이용하시면 인기게시물 확률이 증가합니다.',
      icon: Heart
    },
    {
      id: 'instagram-unlimited-likes',
      name: '인스타그램 무제한 자동 좋아요 늘리기 서비스란?',
      description: '기간 한정 서비스로 인스타그램에 사진을 업로드할 때마다 자동으로 좋아요가 증가하는 서비스입니다. 서비스 기간 동안 모든 게시물에 좋아요가 자동으로 증가하며, 구매한 좋아요 수량만큼 일일 제한 없이 업로드되는 게시물에 좋아요가 증가합니다 (예: 하루 10개, 20개, 30개 게시물).',
      tip: '게시물을 특정 기간동안 많이 올려야 하는 분에게 효율적인 서비스 입니다.',
      icon: Heart
    },
    {
      id: 'instagram-views',
      name: '인스타그램 조회수 늘리기 서비스란?',
      description: '인스타그램 동영상 게시물의 조회수를 늘려주는 서비스입니다. 동영상 게시물의 조회수가 많을수록 인기게시물로 선정될 확률이 높아집니다.',
      tip: '동영상을 여러 개 혹은 사진과 같이 올리면 "갤러리 게시물"이 되어 조회수가 표시되지 않습니다. 동영상을 올리실 때에는 동영상 한 개만 올리셔야 조회수가 표시됩니다.',
      icon: Eye
    },
    {
      id: 'instagram-auto-views',
      name: '인스타그램 자동 조회수 늘리기 서비스란?',
      description: '인스타그램에 동영상을 업로드할 때마다 자동으로 조회수가 증가하는 서비스입니다. 기존 동영상에는 적용되지 않고 향후 업로드되는 동영상에만 적용됩니다.',
      tip: '동영상 게시물을 자주 업로드하시는 분에게 추천하는 서비스입니다.',
      icon: Eye
    },
    {
      id: 'instagram-followers',
      name: '인스타그램 팔로워 늘리기 서비스란?',
      description: '인스타그램 계정의 팔로워 수를 늘려주는 서비스입니다. 팔로워가 많을수록 계정의 영향력과 신뢰도가 높아지며, 브랜드 협업 기회도 증가합니다.',
      tip: '한국인 팔로워와 외국인 팔로워 중 선택하여 주문하실 수 있습니다.',
      icon: Users
    },
    {
      id: 'instagram-comments',
      name: '인스타그램 댓글 늘리기 서비스란?',
      description: '인스타그램 게시물에 댓글을 달아주는 서비스입니다. 댓글이 많을수록 게시물의 상호작용이 높아지고 인기게시물로 선정될 확률이 높아집니다.',
      tip: '커스텀 댓글을 입력하실 수 있으며, 한국어 또는 외국어 댓글 중 선택 가능합니다.',
      icon: MessageCircle
    }
  ]

  const orderGuides = [
    'SNS샵 주문하기 이용 가이드',
    '인스타 인기게시물 상위노출 주문방법',
    '인스타 팔로워 주문방법',
    '인스타 좋아요 주문방법',
    '인스타 자동좋아요 주문방법',
    '자동분할주문 주문방법',
    '유튜브 구독자 주문방법',
    '유튜브 조회수/좋아요/댓글 주문방법',
    '페이스북 페이지 좋아요+팔로워 주문방법',
    '페이스북 팔로워 주문방법',
    '페이스북 게시물 좋아요/댓글 주문방법'
  ]

  return (
    <div className="info-page">
      <div className="info-header">
        <h1>상품/가격 안내 및 상품활용 TIP</h1>
        <p>SNS샵의 다양한 서비스와 활용 방법을 알아보세요</p>
      </div>

      <div className="info-content">
        <div className="info-left">
          <div className="service-selector">
            <label>서비스 선택:</label>
            <select 
              value={selectedService} 
              onChange={(e) => setSelectedService(e.target.value)}
              className="service-dropdown"
            >
              <option value="all">서비스 전체</option>
              <option value="instagram">인스타그램</option>
              <option value="youtube">유튜브</option>
              <option value="facebook">페이스북</option>
              <option value="tiktok">틱톡</option>
            </select>
          </div>

          <div className="services-list">
            {services.map((service) => (
              <div key={service.id} className="service-item">
                <div 
                  className="service-header"
                  onClick={() => toggleExpanded(service.id)}
                >
                  <div className="service-icon">
                    <service.icon size={24} />
                  </div>
                  <h3>{service.name}</h3>
                  {expandedItems[service.id] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
                
                {expandedItems[service.id] && (
                  <div className="service-detail-content">
                    <div className="service-description">
                      <p>{service.description}</p>
                    </div>
                    <div className="service-tip">
                      <Info size={16} />
                      <span>{service.tip}</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="info-right">
          <div className="order-info">
            <h2>주문전 필독사항</h2>
            <ul>
              <li>SNS샵의 모든 상품은 24시간 자동으로 접수/주문되기 때문에 주문방법을 숙지하지 않은 상태에서 주문을 하시게 되면 오주문이 발생될 수 있습니다.</li>
              <li>이용에 어려움이 있으신 분들은 문의주시면 도와드리겠습니다.</li>
            </ul>
          </div>

          <div className="order-guides">
            <h2>주문방법 : 링크 입력 가이드</h2>
            <div className="guides-list">
              {orderGuides.map((guide, index) => (
                <div key={index} className="guide-item">
                  <span>{guide}</span>
                  <ChevronDown size={16} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default InfoPage
