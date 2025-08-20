import React, { useState } from 'react'
import { ChevronRight, HelpCircle, ChevronDown, ChevronUp, Instagram, Youtube, Facebook, MessageCircle, Globe, Star, Users, Heart, Eye, MessageSquare } from 'lucide-react'
import './GuidePanel.css'

const GuidePanel = () => {
  const [expandedGuide, setExpandedGuide] = useState(null)
  const [selectedPlatform, setSelectedPlatform] = useState('all')

  const guides = [
    {
      id: 1,
      title: '인스타 인기게시물 상위노출 주문방법',
      platform: 'instagram',
      icon: Instagram,
      color: '#e4405f',
      description: '인스타그램 인기게시물에 상위노출되어 더 많은 사용자에게 노출되도록 도와드립니다.',
      steps: [
        '1. 인스타그램 계정을 공개로 설정해주세요',
        '2. 상위노출을 원하는 게시물의 링크를 복사해주세요',
        '3. 원하는 노출 수량을 선택해주세요',
        '4. 주문서에 게시물 링크를 입력해주세요',
        '5. 결제 후 5분 내에 작업이 시작됩니다'
      ],
      tips: [
        '• 해시태그를 적절히 사용하면 더 효과적입니다',
        '• 게시물의 품질이 높을수록 노출 효과가 좋습니다',
        '• 정기적인 업로드가 중요합니다'
      ]
    },
    {
      id: 2,
      title: '인스타 팔로워 늘리기 주문방법',
      platform: 'instagram',
      icon: Instagram,
      color: '#e4405f',
      description: '인스타그램 팔로워 수를 늘려 계정의 영향력과 신뢰도를 높여드립니다.',
      steps: [
        '1. 인스타그램 계정을 공개로 설정해주세요',
        '2. 팔로워를 늘리고 싶은 계정의 프로필 링크를 복사해주세요',
        '3. 원하는 팔로워 수량을 선택해주세요 (한국인/외국인 선택 가능)',
        '4. 주문서에 계정 링크를 입력해주세요',
        '5. 결제 후 5분 내에 팔로워 작업이 시작됩니다'
      ],
      tips: [
        '• 한국인 팔로워는 언팔 가능성이 낮습니다',
        '• 외국인 팔로워는 글로벌 영향력을 높여줍니다',
        '• 정기적인 콘텐츠 업로드로 팔로워 유지가 중요합니다'
      ]
    },
    {
      id: 3,
      title: '인스타 좋아요 늘리기 주문방법',
      platform: 'instagram',
      icon: Instagram,
      color: '#e4405f',
      description: '인스타그램 게시물의 좋아요 수를 늘려 게시물의 인기도를 높여드립니다.',
      steps: [
        '1. 인스타그램 계정을 공개로 설정해주세요',
        '2. 좋아요를 늘리고 싶은 게시물의 링크를 복사해주세요',
        '3. 원하는 좋아요 수량을 선택해주세요 (한국인/외국인 선택 가능)',
        '4. 주문서에 게시물 링크를 입력해주세요',
        '5. 결제 후 5분 내에 좋아요 작업이 시작됩니다'
      ],
      tips: [
        '• 좋아요가 많을수록 게시물이 더 많은 사용자에게 노출됩니다',
        '• 한국인 좋아요는 더 자연스러운 상호작용을 제공합니다',
        '• 외국인 좋아요는 글로벌 인기도를 높여줍니다'
      ]
    },
    {
      id: 4,
      title: '인스타 자동좋아요 주문방법',
      platform: 'instagram',
      icon: Instagram,
      color: '#e4405f',
      description: '특정 해시태그나 계정의 게시물에 자동으로 좋아요를 눌러주는 서비스입니다.',
      steps: [
        '1. 인스타그램 계정을 공개로 설정해주세요',
        '2. 자동좋아요를 받고 싶은 해시태그나 계정을 지정해주세요',
        '3. 원하는 좋아요 수량을 선택해주세요',
        '4. 주문서에 타겟 해시태그나 계정을 입력해주세요',
        '5. 결제 후 설정한 조건에 맞는 게시물에 자동으로 좋아요가 눌립니다'
      ],
      tips: [
        '• 관련성 높은 해시태그를 사용하면 더 효과적입니다',
        '• 정기적인 업로드와 함께 사용하면 최적의 효과를 얻을 수 있습니다',
        '• 자동좋아요는 자연스러운 상호작용을 시뮬레이션합니다'
      ]
    },
    {
      id: 5,
      title: '유튜브 구독자 늘리기 주문방법',
      platform: 'youtube',
      icon: Youtube,
      color: '#ff0000',
      description: '유튜브 채널의 구독자 수를 늘려 채널의 영향력과 수익화 기회를 높여드립니다.',
      steps: [
        '1. 유튜브 채널을 공개로 설정해주세요',
        '2. 구독자를 늘리고 싶은 채널의 링크를 복사해주세요',
        '3. 원하는 구독자 수량을 선택해주세요 (한국인/외국인 선택 가능)',
        '4. 주문서에 채널 링크를 입력해주세요',
        '5. 결제 후 5분 내에 구독자 작업이 시작됩니다'
      ],
      tips: [
        '• 1,000명 이상의 구독자가 있어야 유튜브 파트너 프로그램에 참여할 수 있습니다',
        '• 한국인 구독자는 더 안정적이고 신뢰할 수 있습니다',
        '• 외국인 구독자는 글로벌 시장 진출에 도움이 됩니다'
      ]
    },
    {
      id: 6,
      title: '유튜브 조회수/좋아요/댓글 주문방법',
      platform: 'youtube',
      icon: Youtube,
      color: '#ff0000',
      description: '유튜브 동영상의 조회수, 좋아요, 댓글을 늘려 동영상의 인기도를 높여드립니다.',
      steps: [
        '1. 유튜브 동영상을 공개로 설정해주세요',
        '2. 조회수/좋아요/댓글을 늘리고 싶은 동영상의 링크를 복사해주세요',
        '3. 원하는 서비스와 수량을 선택해주세요',
        '4. 주문서에 동영상 링크를 입력해주세요',
        '5. 결제 후 5분 내에 작업이 시작됩니다'
      ],
      tips: [
        '• 조회수가 많을수록 유튜브 추천 알고리즘에서 우선순위가 높아집니다',
        '• 좋아요와 댓글은 동영상의 참여도를 높여줍니다',
        '• 정기적인 업로드와 함께 사용하면 최적의 효과를 얻을 수 있습니다'
      ]
    },
    {
      id: 7,
      title: '페이스북 페이지 좋아요+팔로워 주문방법',
      platform: 'facebook',
      icon: Facebook,
      color: '#1877f2',
      description: '페이스북 페이지의 좋아요와 팔로워를 늘려 페이지의 영향력을 높여드립니다.',
      steps: [
        '1. 페이스북 페이지를 공개로 설정해주세요',
        '2. 좋아요와 팔로워를 늘리고 싶은 페이지의 링크를 복사해주세요',
        '3. 원하는 좋아요와 팔로워 수량을 선택해주세요',
        '4. 주문서에 페이지 링크를 입력해주세요',
        '5. 결제 후 5분 내에 작업이 시작됩니다'
      ],
      tips: [
        '• 페이지 좋아요가 많을수록 게시물이 더 많은 사용자에게 노출됩니다',
        '• 팔로워는 페이지의 새로운 게시물을 자동으로 볼 수 있습니다',
        '• 정기적인 콘텐츠 업로드가 중요합니다'
      ]
    },
    {
      id: 8,
      title: '페이스북 팔로워 늘리기 주문방법',
      platform: 'facebook',
      icon: Facebook,
      color: '#1877f2',
      description: '페이스북 개인 계정의 팔로워를 늘려 개인 브랜딩과 영향력을 높여드립니다.',
      steps: [
        '1. 페이스북 계정을 공개로 설정해주세요',
        '2. 팔로워를 늘리고 싶은 계정의 프로필 링크를 복사해주세요',
        '3. 원하는 팔로워 수량을 선택해주세요 (한국인/외국인 선택 가능)',
        '4. 주문서에 계정 링크를 입력해주세요',
        '5. 결제 후 5분 내에 팔로워 작업이 시작됩니다'
      ],
      tips: [
        '• 한국인 팔로워는 더 안정적이고 신뢰할 수 있습니다',
        '• 외국인 팔로워는 글로벌 네트워킹에 도움이 됩니다',
        '• 정기적인 게시물 업로드로 팔로워와의 상호작용을 유지하세요'
      ]
    },
    {
      id: 9,
      title: '페이스북 게시물 좋아요/댓글 주문방법',
      platform: 'facebook',
      icon: Facebook,
      color: '#1877f2',
      description: '페이스북 게시물의 좋아요와 댓글을 늘려 게시물의 인기도를 높여드립니다.',
      steps: [
        '1. 페이스북 게시물을 공개로 설정해주세요',
        '2. 좋아요/댓글을 늘리고 싶은 게시물의 링크를 복사해주세요',
        '3. 원하는 좋아요와 댓글 수량을 선택해주세요',
        '4. 주문서에 게시물 링크를 입력해주세요',
        '5. 결제 후 5분 내에 작업이 시작됩니다'
      ],
      tips: [
        '• 좋아요가 많을수록 게시물이 더 많은 사용자에게 노출됩니다',
        '• 댓글은 게시물의 참여도를 높여줍니다',
        '• 질문이나 토론 주제로 게시물을 작성하면 댓글 참여가 높아집니다'
      ]
    }
  ]

  const platformFilters = [
    { id: 'all', name: '전체', icon: Star },
    { id: 'instagram', name: '인스타그램', icon: Instagram, color: '#e4405f' },
    { id: 'youtube', name: '유튜브', icon: Youtube, color: '#ff0000' },
    { id: 'facebook', name: '페이스북', icon: Facebook, color: '#1877f2' }
  ]

  const filteredGuides = selectedPlatform === 'all' 
    ? guides 
    : guides.filter(guide => guide.platform === selectedPlatform)

  const handleGuideClick = (guideId) => {
    setExpandedGuide(expandedGuide === guideId ? null : guideId)
  }

  const handlePlatformFilter = (platformId) => {
    setSelectedPlatform(platformId)
    setExpandedGuide(null)
  }

  return (
    <aside className="guide-panel">
      <div className="guide-header">
        <HelpCircle size={20} />
        <h3>주문방법 : 링크 입력 가이드</h3>
      </div>

      {/* 플랫폼 필터 */}
      <div className="platform-filters">
        {platformFilters.map((filter) => (
          <button
            key={filter.id}
            className={`platform-filter-btn ${selectedPlatform === filter.id ? 'active' : ''}`}
            onClick={() => handlePlatformFilter(filter.id)}
            style={filter.color ? { '--filter-color': filter.color } : {}}
          >
            <filter.icon size={16} />
            <span>{filter.name}</span>
          </button>
        ))}
      </div>

      <div className="guide-list">
        {filteredGuides.map((guide) => (
          <div key={guide.id} className={`guide-item ${expandedGuide === guide.id ? 'selected' : ''}`}>
            <div 
              className="guide-item-header"
              onClick={() => handleGuideClick(guide.id)}
            >
              <div className="guide-item-icon">
                <guide.icon size={18} style={{ color: guide.color }} />
              </div>
              <span className="guide-text">{guide.title}</span>
              {expandedGuide === guide.id ? <ChevronUp size={16} /> : <ChevronRight size={16} />}
            </div>
            
            {expandedGuide === guide.id && (
              <div className="guide-item-content">
                <p className="guide-description">{guide.description}</p>
                
                <div className="guide-steps">
                  <h4>주문 단계</h4>
                  <ul>
                    {guide.steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ul>
                </div>

                <div className="guide-tips">
                  <h4>💡 팁</h4>
                  <ul>
                    {guide.tips.map((tip, index) => (
                      <li key={index}>{tip}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  )
}

export default GuidePanel
