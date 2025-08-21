import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  Star, 
  Package, 
  Trophy, 
  FileText, 
  Folder, 
  Instagram, 
  Youtube, 
  Facebook, 
  MessageCircle, 
  Twitter, 
  Globe, 
  Users,
  ShoppingBag, 
  Phone, 
  BarChart3,
  HelpCircle,
  CheckCircle,
  Sparkles,
  ArrowRight,
  ChevronDown,
  ShoppingBag as ShoppingBagIcon,
  MessageSquare,
  Home as HomeIcon,
  Smartphone,
  TrendingUp,
  MoreHorizontal
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { getPlatformInfo, calculatePrice } from '../utils/platformUtils'
import { smmkingsApi, handleApiError, transformOrderData } from '../services/snspopApi'
import { getSMMKingsServiceId, getSMMKingsServicePrice, getAvailableServices, getSMMKingsServiceMin, getSMMKingsServiceMax } from '../utils/smmkingsMapping'
import './Home.css'

const Home = () => {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const [selectedPlatform, setSelectedPlatform] = useState('instagram')
  const [selectedServiceType, setSelectedServiceType] = useState('recommended')
  const [selectedService, setSelectedService] = useState('followers_korean')
  const [selectedDetailedService, setSelectedDetailedService] = useState(null)
  const [quantity, setQuantity] = useState(200)
  const [totalPrice, setTotalPrice] = useState(0)
  const [showChecklist, setShowChecklist] = useState(false)
  const [link, setLink] = useState('')
  const [comments, setComments] = useState('')
  const [explanation, setExplanation] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  const platforms = [
    { id: 'recommended', name: '추천서비스', icon: Star, color: '#f59e0b', description: '인기 서비스 모음' },
    { id: 'event', name: '이벤트', icon: Package, color: '#8b5cf6', description: '특별 이벤트 서비스' },
    { id: 'top-exposure', name: '상위노출', icon: Trophy, color: '#f59e0b', description: '검색 상위 노출 서비스' },
    { id: 'account-management', name: '계정관리', icon: FileText, color: '#10b981', description: '계정 관리 서비스' },
    { id: 'package', name: '패키지', icon: Folder, color: '#3b82f6', description: '통합 패키지 서비스' },
    { id: 'instagram', name: '인스타그램', icon: Instagram, color: '#e4405f', description: '팔로워, 좋아요, 댓글 서비스' },
    { id: 'youtube', name: '유튜브', icon: Youtube, color: '#ff0000', description: '구독자, 좋아요, 조회수 서비스' },
    { id: 'facebook', name: '페이스북', icon: Facebook, color: '#1877f2', description: '페이지 좋아요, 팔로워 서비스' },
    { id: 'tiktok', name: '틱톡', icon: MessageCircle, color: '#000000', description: '팔로워, 좋아요, 조회수 서비스' },
    { id: 'threads', name: '스레드', icon: MessageSquare, color: '#000000', description: '스레드 서비스' },
    { id: 'twitter', name: '트위터', icon: Twitter, color: '#1da1f2', description: '팔로워, 리트윗, 좋아요 서비스' },
    { id: 'naver', name: '네이버', icon: Globe, color: '#03c75a', description: '네이버 라이브 서비스' },
    { id: 'news-media', name: '뉴스언론보도', icon: FileText, color: '#3b82f6', description: '뉴스 언론 보도 서비스' },
    { id: 'experience-group', name: '체험단', icon: Users, color: '#10b981', description: '체험단 서비스' },
    { id: 'kakao', name: '카카오', icon: MessageCircle, color: '#fbbf24', description: '카카오 서비스' },
    { id: 'store-marketing', name: '스토어마케팅', icon: HomeIcon, color: '#f59e0b', description: '스토어 마케팅 서비스' },
    { id: 'app-marketing', name: '어플마케팅', icon: Smartphone, color: '#3b82f6', description: '앱 마케팅 서비스' },
    { id: 'seo-traffic', name: 'SEO트래픽', icon: TrendingUp, color: '#8b5cf6', description: 'SEO 트래픽 서비스' },
    { id: 'other', name: '기타', icon: MoreHorizontal, color: '#6b7280', description: '기타 서비스' }
  ]

  // 플랫폼별 서비스 목록
  const getServicesForPlatform = (platform) => {
    switch (platform) {
      case 'instagram':
        return [
          { id: 'followers_korean', name: '팔로워 (한국인)', description: '한국인 팔로워 서비스' },
          { id: 'followers_foreign', name: '팔로워 (외국인)', description: '외국인 팔로워 서비스' },
          { id: 'likes_korean', name: '좋아요 (한국인)', description: '한국인 좋아요 서비스' },
          { id: 'likes_foreign', name: '좋아요 (외국인)', description: '외국인 좋아요 서비스' },
          { id: 'comments_korean', name: '댓글 (한국인)', description: '한국인 댓글 서비스' },
          { id: 'comments_foreign', name: '댓글 (외국인)', description: '외국인 댓글 서비스' },
          { id: 'views_korean', name: '조회수 (한국인)', description: '한국인 조회수 서비스' },
          { id: 'views_foreign', name: '조회수 (외국인)', description: '외국인 조회수 서비스' }
        ]
      case 'youtube':
        return [
          { id: 'followers_korean', name: '구독자', description: '구독자 서비스' },
          { id: 'likes_foreign', name: '좋아요', description: '좋아요 서비스' },
          { id: 'views_foreign', name: '조회수', description: '조회수 서비스' }
        ]
      case 'tiktok':
        return [
          { id: 'followers_foreign', name: '팔로워 (외국인)', description: '외국인 팔로워 서비스' },
          { id: 'likes_foreign', name: '좋아요 (외국인)', description: '외국인 좋아요 서비스' },
          { id: 'views_foreign', name: '조회수 (외국인)', description: '외국인 조회수 서비스' },
          { id: 'comments_foreign', name: '댓글 (외국인)', description: '외국인 댓글 서비스' },
          { id: 'shares_foreign', name: '공유/저장 (외국인)', description: '외국인 공유/저장 서비스' },
          { id: 'story_foreign', name: '스토리 (외국인)', description: '외국인 스토리 서비스' },
          { id: 'live_foreign', name: '라이브 (외국인)', description: '외국인 라이브 서비스' }
        ]
      case 'facebook':
        return [
          { id: 'page_likes_foreign', name: '팬페이지 좋아요', description: '팬페이지 좋아요 서비스' },
          { id: 'post_likes_foreign', name: '게시물 좋아요', description: '게시물 좋아요 서비스' },
          { id: 'video_views_foreign', name: '비디오 조회수', description: '비디오 조회수 서비스' },
          { id: 'comments_foreign', name: '댓글', description: '댓글 서비스' }
        ]
      case 'threads':
        return [
          { id: 'followers_foreign', name: '팔로워 (외국인)', description: '외국인 팔로워 서비스' },
          { id: 'likes_foreign', name: '좋아요 (외국인)', description: '외국인 좋아요 서비스' }
        ]
      case 'naver':
        return [
          { id: 'live_foreign', name: '네이버 라이브', description: '네이버 라이브 서비스' }
        ]
      case 'recommended':
        return [
          { id: 'instagram_followers', name: '인스타그램 팔로워', description: '인기 팔로워 서비스' },
          { id: 'instagram_likes', name: '인스타그램 좋아요', description: '인기 좋아요 서비스' },
          { id: 'instagram_popular', name: '인스타그램 상위노출', description: '인기 상위노출 서비스' },
          { id: 'youtube_subscribers', name: '유튜브 구독자', description: '인기 구독자 서비스' },
          { id: 'youtube_views', name: '유튜브 조회수', description: '인기 조회수 서비스' },
          { id: 'tiktok_followers', name: '틱톡 팔로워', description: '인기 팔로워 서비스' },
          { id: 'tiktok_views', name: '틱톡 조회수', description: '인기 조회수 서비스' },
          { id: 'facebook_page_likes', name: '페이스북 팬페이지 좋아요', description: '인기 팬페이지 서비스' },
          { id: 'twitter_followers', name: '트위터 팔로워', description: '인기 팔로워 서비스' }
        ]
      default:
        return []
    }
  }

  // 서비스 타입별 세부 서비스 목록
  const getDetailedServices = (platform, serviceType) => {
    const availableServices = getAvailableServices(platform)
    return availableServices.filter(service => {
      // 서비스 타입에 따라 필터링
      if (serviceType === 'followers_korean') {
        return service.id.includes('followers') && service.name.includes('한국') || service.name.includes('HQ') || service.name.includes('실제')
      } else if (serviceType === 'followers_foreign') {
        return service.id.includes('followers') && !service.name.includes('한국')
      } else if (serviceType === 'likes_korean') {
        return service.id.includes('likes') && service.name.includes('한국') || service.name.includes('UHQ')
      } else if (serviceType === 'likes_foreign') {
        return service.id.includes('likes') && !service.name.includes('한국') && !service.name.includes('UHQ')
      } else if (serviceType === 'comments_korean') {
        return service.id.includes('comments') && service.name.includes('한국') || service.name.includes('커스텀') || service.name.includes('랜덤')
      } else if (serviceType === 'comments_foreign') {
        return service.id.includes('comments') && !service.name.includes('한국')
      } else if (serviceType === 'views_korean') {
        return service.id.includes('views') && service.name.includes('한국')
      } else if (serviceType === 'views_foreign') {
        return service.id.includes('views') && !service.name.includes('한국')
      } else if (serviceType === 'shares_foreign') {
        return service.id.includes('shares') || service.id.includes('saves')
      } else if (serviceType === 'story_foreign') {
        return service.id.includes('story')
      } else if (serviceType === 'live_foreign') {
        return service.id.includes('live')
      } else if (serviceType === 'followers_foreign' && platform === 'threads') {
        return service.id.includes('followers')
      } else if (serviceType === 'likes_foreign' && platform === 'threads') {
        return service.id.includes('likes')
      } else if (serviceType === 'live_foreign' && platform === 'naver') {
        return service.id.includes('live') || service.id.includes('tv')
      } else if (serviceType === 'followers_korean' && platform === 'youtube') {
        return service.id.includes('subscribers')
      } else if (serviceType === 'page_likes_foreign' && platform === 'facebook') {
        return service.id.includes('page_likes')
      } else if (serviceType === 'post_likes_foreign' && platform === 'facebook') {
        return service.id.includes('post_likes')
      } else if (serviceType === 'video_views_foreign' && platform === 'facebook') {
        return service.id.includes('video_views')
      } else if (serviceType === 'comments_foreign' && platform === 'facebook') {
        return service.id.includes('comments')
      } else if (platform === 'recommended') {
        // 추천서비스는 각 플랫폼의 인기 서비스들을 매핑
        if (serviceType === 'instagram_followers') {
          return service.id.includes('followers') && (service.name.includes('인스타그램') || service.name.includes('Instagram'))
        } else if (serviceType === 'instagram_likes') {
          return service.id.includes('likes') && (service.name.includes('인스타그램') || service.name.includes('Instagram'))
        } else if (serviceType === 'instagram_popular') {
          return service.id.includes('popular') && (service.name.includes('인스타그램') || service.name.includes('Instagram'))
        } else if (serviceType === 'youtube_subscribers') {
          return service.id.includes('subscribers') && (service.name.includes('YouTube') || service.name.includes('유튜브'))
        } else if (serviceType === 'youtube_views') {
          return service.id.includes('views') && (service.name.includes('YouTube') || service.name.includes('유튜브'))
        } else if (serviceType === 'tiktok_followers') {
          return service.id.includes('followers') && (service.name.includes('틱톡') || service.name.includes('TikTok'))
        } else if (serviceType === 'tiktok_views') {
          return service.id.includes('views') && (service.name.includes('틱톡') || service.name.includes('TikTok'))
        } else if (serviceType === 'facebook_page_likes') {
          return service.id.includes('page_likes') && (service.name.includes('페이스북') || service.name.includes('Facebook'))
        } else if (serviceType === 'twitter_followers') {
          return service.id.includes('followers') && (service.name.includes('트위터') || service.name.includes('Twitter') || service.name.includes('X'))
        }
      }
      return false
    })
  }

  const services = getServicesForPlatform(selectedPlatform)
  const detailedServices = getDetailedServices(selectedPlatform, selectedService)

  // 플랫폼 정보 가져오기
  const platformInfo = getPlatformInfo(selectedPlatform)

  // 수량 옵션 생성
  const getQuantityOptions = (platform, serviceId) => {
    if (selectedDetailedService) {
      const min = selectedDetailedService.min
      const max = selectedDetailedService.max
      
      // 10개 단위로 수량 옵션 생성
      const options = []
      let current = min
      
      // 최소값을 10의 배수로 조정
      const adjustedMin = Math.ceil(min / 10) * 10
      current = Math.max(min, adjustedMin)
      
      while (current <= max && options.length < 50) {
        options.push(current)
        current += 10
      }
      
      // 최대값이 포함되지 않았다면 추가
      if (options.length > 0 && options[options.length - 1] < max) {
        options.push(max)
      }
      
      return options
    }
    
    // 기본 수량 옵션 (10개 단위)
    return [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 6000, 7000, 8000, 9000, 10000]
  }

  const quantityOptions = getQuantityOptions(selectedPlatform, selectedService)

  // 할인 정보
  const discountTiers = [
    { min: 500, max: 999, discount: 10 },
    { min: 1000, max: 4999, discount: 15 },
    { min: 5000, max: 10000, discount: 20 }
  ]

  const getDiscount = (qty) => {
    const tier = discountTiers.find(t => qty >= t.min && qty <= t.max)
    return tier ? tier.discount : 0
  }

  // 가격 계산 (SMM KINGS 가격 사용)
  useEffect(() => {
    if (!selectedPlatform || !selectedDetailedService || quantity <= 0) {
      setTotalPrice(0)
      return
    }
    
    // SMM KINGS 가격 사용
    const basePrice = selectedDetailedService.price * quantity
    
    // 할인 적용
    let discount = 0
    if (quantity >= 5000) {
      discount = 20
    } else if (quantity >= 1000) {
      discount = 15
    } else if (quantity >= 500) {
      discount = 10
    }
    
    const finalPrice = basePrice * (1 - discount / 100)
    setTotalPrice(Math.round(finalPrice))
  }, [selectedDetailedService, quantity, selectedPlatform])

  const handlePlatformSelect = (platformId) => {
    setSelectedPlatform(platformId)
    setSelectedServiceType('recommended')
    setSelectedDetailedService(null)
    
    // 플랫폼에 따라 기본 서비스 설정
    if (['recommended', 'event', 'top-exposure', 'account-management', 'package', 'other', 'threads', 'news-media', 'experience-group', 'kakao', 'store-marketing', 'app-marketing', 'seo-traffic'].includes(platformId)) {
      setSelectedService('instagram_followers')
      setQuantity(1)
    } else {
      setSelectedService('followers_korean')
      setQuantity(200)
    }
    
    setLink('')
    setComments('')
    setExplanation('')
  }

  const handleServiceSelect = (serviceId) => {
    setSelectedService(serviceId)
    setSelectedDetailedService(null)
    
    // 세부 서비스가 있으면 첫 번째 것을 기본 선택
    const detailedServices = getDetailedServices(selectedPlatform, serviceId)
    if (detailedServices.length > 0) {
      setSelectedDetailedService(detailedServices[0])
      setQuantity(detailedServices[0].min)
    }
  }

  const handleDetailedServiceSelect = (detailedService) => {
    setSelectedDetailedService(detailedService)
    setQuantity(detailedService.min)
  }

  const handleQuantityChange = (newQuantity) => {
    if (selectedDetailedService) {
      const min = selectedDetailedService.min
      const max = selectedDetailedService.max
      
      // 최소/최대 범위 내에서만 수량 변경 허용
      if (newQuantity >= min && newQuantity <= max) {
        setQuantity(newQuantity)
      }
    } else {
      setQuantity(newQuantity)
    }
  }

  const handlePremiumCheck = () => {
    alert('프리미엄 퀄리티 확인 기능이 실행됩니다.')
  }

  const handleHelpClick = () => {
    alert('주문 방법에 대한 상세한 가이드를 확인할 수 있습니다.')
  }

  const handleInquiryClick = () => {
    alert('1:1 문의 기능이 실행됩니다.')
  }

  const handlePurchase = async () => {
    if (!currentUser) {
      alert('로그인이 필요합니다.')
      return
    }

    if (!selectedDetailedService) {
      alert('세부 서비스를 선택해주세요.')
      return
    }

    if (!link.trim()) {
      alert('링크를 입력해주세요!')
      return
    }

    if (((selectedPlatform === 'instagram' && (selectedService === 'comments_korean' || selectedService === 'comments_foreign')) || 
         (selectedPlatform === 'youtube' && selectedService === 'comments_korean')) && !comments.trim()) {
      alert('댓글 내용을 입력해주세요!')
      return
    }

    setIsLoading(true)

    try {
      const orderData = {
        serviceId: selectedDetailedService.smmkings_id,
        link: link.trim(),
        quantity,
        runs: 1,
        interval: 0,
        comments: comments.trim(),
        explanation: explanation.trim(),
        username: '',
        min: 0,
        max: 0,
        posts: 0,
        delay: 0,
        expiry: '',
        oldPosts: 0
      }

      const transformedData = transformOrderData(orderData)
      const userId = currentUser?.uid || currentUser?.email || 'anonymous'
      const result = await smmkingsApi.createOrder(transformedData, userId)

      if (result.error) {
        alert(`주문 생성 실패: ${result.error}`)
      } else {
        const paymentData = {
          orderId: result.order,
          platform: selectedPlatform,
          serviceName: selectedDetailedService.name,
          quantity: quantity,
          unitPrice: selectedDetailedService.price,
          totalPrice: totalPrice,
          link: link.trim(),
          comments: comments.trim(),
          explanation: explanation.trim(),
          discount: getDiscount(quantity)
        }
        
        navigate(`/payment/${selectedPlatform}`, { state: { orderData: paymentData } })
      }
    } catch (error) {
      const errorInfo = handleApiError(error)
      console.error('Order creation failed:', errorInfo)
      alert(`주문 생성 실패: ${errorInfo.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddToCart = async () => {
    if (!currentUser) {
      alert('로그인이 필요합니다.')
      return
    }

    try {
      const cartItem = {
        id: Date.now(),
        platform: selectedPlatform,
        service: selectedService,
        detailedService: selectedDetailedService,
        quantity,
        unitPrice: selectedDetailedService?.price || 0,
        totalPrice,
        timestamp: new Date().toISOString()
      }

      const existingCart = JSON.parse(localStorage.getItem('snspop_cart') || '[]')
      existingCart.push(cartItem)
      localStorage.setItem('snspop_cart', JSON.stringify(existingCart))

      alert('장바구니에 추가되었습니다!')
    } catch (error) {
      console.error('Add to cart failed:', error)
      alert('장바구니 추가 실패')
    }
  }

  return (
    <div className="order-page">
      {/* Service Selection */}
      <div className="service-selection">
        <h2>주문하기</h2>
        <p>원하는 서비스를 선택하고 주문해보세요!</p>
        
        <div className="platform-grid">
          {platforms.map(({ id, name, icon: Icon, color, description }) => (
            <div
              key={id}
              className={`platform-item ${selectedPlatform === id ? 'selected' : ''}`}
              onClick={() => handlePlatformSelect(id)}
              style={{
                '--platform-color': color,
                '--platform-color-secondary': color === '#f59e0b' ? '#d97706' : 
                                            color === '#8b5cf6' ? '#7c3aed' :
                                            color === '#10b981' ? '#059669' :
                                            color === '#3b82f6' ? '#2563eb' :
                                            color === '#e4405f' ? '#dc2626' :
                                            color === '#ff0000' ? '#dc2626' :
                                            color === '#1877f2' ? '#0d6efd' :
                                            color === '#000000' ? '#374151' :
                                            color === '#1da1f2' ? '#0ea5e9' :
                                            color === '#03c75a' ? '#059669' :
                                            color === '#fbbf24' ? '#f59e0b' :
                                            color === '#8b5cf6' ? '#7c3aed' :
                                            color === '#6b7280' ? '#4b5563' : '#667eea'
              }}
            >
              <Icon size={32} className="platform-icon" />
              <div className="platform-name">{name}</div>
              <div className="platform-description">{description}</div>
        </div>
          ))}
        </div>
          </div>
      
      {/* Service Type Selection */}
      <div className="service-type-selection">
        <h3>서비스 타입을 선택해주세요</h3>
        
        {/* Premium Quality Check Button */}
        <div className="service-item premium-check" onClick={handlePremiumCheck}>
          <div className="service-content">
            <CheckCircle size={20} />
            <span>선택상품의 프리미엄 퀄리티확인</span>
          </div>
        </div>

        {/* Service Selection */}
        <div className="service-category">
          <h3 className="category-title">{platforms.find(p => p.id === selectedPlatform)?.name} 서비스</h3>
          <div className="service-list">
            {services.map(({ id, name, badge, featured, special }) => (
              <div 
                key={id} 
                className={`service-item ${special ? 'special' : ''} ${featured ? 'featured' : ''} ${selectedService === id ? 'selected' : ''}`}
                onClick={() => handleServiceSelect(id)}
              >
                <div className="service-content">
                  <span className="service-name">{name}</span>
                  {badge && <span className="service-badge">{badge}</span>}
                  {featured && <Star size={16} className="featured-icon" />}
                  {special && (
                    <div className="special-indicator">
                      <Sparkles size={16} />
                      <Sparkles size={16} />
      </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {/* Detailed Service Selection */}
      {selectedService && detailedServices.length > 0 && (
        <div className="detailed-service-selection">
          <h3>세부 서비스를 선택해주세요</h3>
          <div className="detailed-service-list">
            {detailedServices.map((service) => (
              <div 
                key={service.id} 
                className={`detailed-service-item ${selectedDetailedService?.id === service.id ? 'selected' : ''}`}
                onClick={() => handleDetailedServiceSelect(service)}
              >
                <div className="detailed-service-content">
                  <div className="detailed-service-info">
                    <div className="detailed-service-name">{service.name}</div>
                    <div className="detailed-service-range">최소: {service.min.toLocaleString()} ~ 최대: {service.max.toLocaleString()}</div>
                  </div>
                  <div className="detailed-service-price">{service.price.toFixed(2)}원</div>
                </div>
                </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Order Form */}
      {selectedDetailedService && (
        <div className="order-form">
          <h3>주문 정보 입력</h3>
          
          {/* Service Description */}
          <div className="service-description">
            <h4>선택된 서비스</h4>
            <p>{selectedDetailedService.name}</p>
            <p>1개당 {selectedDetailedService.price.toFixed(2)}원 | 최소: {selectedDetailedService.min.toLocaleString()} ~ 최대: {selectedDetailedService.max.toLocaleString()}</p>
          </div>
          
          {/* Quantity Selection */}
          <div className="form-group">
            <label>수량 선택</label>
            <div className="quantity-controls">
              <button 
                className="quantity-btn" 
                onClick={() => {
                  const newQuantity = Math.max(selectedDetailedService.min, quantity - 10)
                  if (newQuantity >= selectedDetailedService.min) {
                    handleQuantityChange(newQuantity)
                  }
                }}
                disabled={quantity <= selectedDetailedService.min}
              >
                -
              </button>
              <input
                type="text"
                value={quantity.toLocaleString()}
                readOnly
                className="quantity-input"
              />
              <button 
                className="quantity-btn"
                onClick={() => {
                  const newQuantity = Math.min(selectedDetailedService.max, quantity + 10)
                  if (newQuantity <= selectedDetailedService.max) {
                    handleQuantityChange(newQuantity)
                  }
                }}
                disabled={quantity >= selectedDetailedService.max}
              >
                +
              </button>
                </div>
            <div className="quantity-info">
              <p>1개당 {selectedDetailedService.price.toFixed(2)}원</p>
              <p>최소: {selectedDetailedService.min.toLocaleString()} ~ 최대: {selectedDetailedService.max.toLocaleString()}</p>
              <p>10개 단위로 조정 가능</p>
              {getDiscount(quantity) > 0 && (
                <p className="discount-applied">{getDiscount(quantity)}% 할인 적용</p>
              )}
        </div>
      </div>

          {/* Link Input */}
          <div className="form-group">
            <label>링크 입력</label>
            <input
              type="url"
              value={link}
              onChange={(e) => setLink(e.target.value)}
              placeholder={`${platformInfo.name} 게시물 URL 또는 사용자명을 입력하세요`}
              className="form-control"
            />
          </div>

          {/* Comments Input */}
          {((selectedPlatform === 'instagram' && (selectedService === 'comments_korean' || selectedService === 'comments_foreign')) || 
            (selectedPlatform === 'youtube' && selectedService === 'comments_korean')) && (
            <div className="form-group">
              <label>댓글 내용</label>
              <textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="댓글 내용을 입력하세요 (최대 200자)"
                maxLength="200"
                className="form-control"
                rows="4"
              />
              <div className="char-count">{comments.length}/200</div>
                </div>
          )}

          {/* Explanation Input */}
          <div className="form-group">
            <label>추가 요청사항</label>
            <textarea
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder="추가 요청사항이나 특별한 요구사항이 있으시면 입력해주세요 (선택사항)"
              maxLength="500"
              className="form-control"
              rows="4"
            />
            <div className="char-count">{comments.length}/500</div>
      </div>

          {/* Total Price */}
          <div className="price-display">
            <div className="total-price">{totalPrice.toLocaleString()}원</div>
            <div className="price-label">총 금액</div>
              </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button className="submit-btn" onClick={handlePurchase} disabled={isLoading}>
              {isLoading ? '처리 중...' : '구매하기'}
            </button>
          </div>
        </div>
      )}

      {/* Bulk Purchase */}
      <div className="service-category">
        <h3 className="category-title">기타 서비스</h3>
        <div className="service-list">
          <div className="service-item special" onClick={() => alert('대량구매 문의 기능이 실행됩니다.')}>
            <div className="service-content">
              <span className="service-name">대량구매 시 문의주세요</span>
              <div className="special-indicator">
                <Sparkles size={16} />
                <Sparkles size={16} />
      </div>
            </div>
          </div>
        </div>
      </div>

      {/* 1:1 Inquiry Button */}
      <div className="inquiry-button">
        <button className="inquiry-btn" onClick={handleInquiryClick}>
          <MessageCircle size={20} />
          1:1 문의
        </button>
      </div>

    </div>
  )
}

export default Home
