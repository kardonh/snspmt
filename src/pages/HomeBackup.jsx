import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
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
  Zap,
  Package,
  Trophy,
  Folder,
  Facebook,
  Twitter,
  Globe,
  MessageSquare,
  Sparkles,
  ChevronRight
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useGuest } from '../contexts/GuestContext'
import { smmpanelApi, transformOrderData } from '../services/snspopApi'
import './Home.css'
import instagramDetailedServices from '../data/instagramDetailed'

const Home = () => {
  const { currentUser, setShowAuthModal, setShowOrderMethodModal } = useAuth()
  const { isGuest } = useGuest()
  const navigate = useNavigate()
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(true)

  const [selectedPlatform, setSelectedPlatform] = useState('recommended')
  const [selectedServiceType, setSelectedServiceType] = useState('recommended')
  const [selectedService, setSelectedService] = useState('top_exposure_30days')
  const [selectedDetailedService, setSelectedDetailedService] = useState(null)
  const [selectedTab, setSelectedTab] = useState('korean') // 'korean' or 'foreign'
  const [quantity, setQuantity] = useState(200)
  const [totalPrice, setTotalPrice] = useState(0)
  const [showChecklist, setShowChecklist] = useState(false)
  const [link, setLink] = useState('')
  const [comments, setComments] = useState('')
  const [explanation, setExplanation] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  
  // 할인 쿠폰 관련 상태 제거 - 추천인 시스템은 커미션 방식 (할인 쿠폰 아님)
  
  // SMM Panel 유효 서비스 ID 목록
  const [validServiceIds, setValidServiceIds] = useState([])
  const [isLoadingServices, setIsLoadingServices] = useState(false)
  
  // 데이터베이스에서 가져온 상품 데이터
  const [categories, setCategories] = useState([])
  const [products, setProducts] = useState([])
  const [variants, setVariants] = useState([])
  const [packages, setPackages] = useState([])
  const [isLoadingCatalog, setIsLoadingCatalog] = useState(false)
  
  // 예약 발송 관련 상태
  const [isScheduledOrder, setIsScheduledOrder] = useState(false)
  const [scheduledDate, setScheduledDate] = useState('')
  const [scheduledTime, setScheduledTime] = useState('')
  
  // 분할 발송 관련 상태
  const [isSplitDelivery, setIsSplitDelivery] = useState(false)
  const [splitDays, setSplitDays] = useState(1)
  
  // 예약 발송과 분할 발송 상호 배타적 선택
  const handleScheduledOrderChange = (checked) => {
    setIsScheduledOrder(checked)
    if (checked && isSplitDelivery) {
      setIsSplitDelivery(false)
    }
  }
  
  const handleSplitDeliveryChange = (checked) => {
    setIsSplitDelivery(checked)
    if (checked && isScheduledOrder) {
      setIsScheduledOrder(false)
    }
  }
  
  // 일일 수량 자동 계산
  const getDailyQuantity = () => {
    if (!isSplitDelivery || !quantity || !splitDays) return 0
    return Math.ceil(quantity / splitDays)
  }
  
  // 분할 발송 가능 여부 확인
  const isSplitDeliveryValid = () => {
    if (!isSplitDelivery || !quantity || !splitDays || splitDays === 0 || !selectedDetailedService) return true
    
    const dailyQty = getDailyQuantity()
    const minQuantity = selectedDetailedService.min || 1
    const totalSplitQuantity = dailyQty * splitDays
    
    // 최소 수량 미달 또는 총 수량 초과 시 유효하지 않음
    return dailyQty >= minQuantity && totalSplitQuantity <= quantity
  }
  
  // 분할 발송 정보 표시
  const getSplitInfo = () => {
    if (!isSplitDelivery || !quantity || !splitDays) return ''
    const dailyQty = getDailyQuantity()
    const totalDays = Math.ceil(quantity / dailyQty)
    const minQuantity = selectedDetailedService?.min || 1
    const totalSplitQuantity = dailyQty * splitDays
    const isValid = isSplitDeliveryValid()
    
    let info = `총 ${quantity}개를 ${totalDays}일 동안 하루 ${dailyQty}개씩 분할 발송`
    
    if (!isValid) {
      if (dailyQty < minQuantity) {
        info += ` ⚠️ (최소 수량 ${minQuantity}개/일 미달)`
      } else if (totalSplitQuantity > quantity) {
        info += ` ⚠️ (총 수량 ${totalSplitQuantity}개 초과)`
      }
    }
    
    return info
  }

  // 유효한 서비스만 필터링하는 함수
  const filterValidServices = (services) => {
    if (validServiceIds.length > 0) {
      return services.filter(service => {
        // SMM Panel 서비스 ID가 있는 경우에만 필터링
        if (service.smmkings_id) {
          return validServiceIds.includes(service.smmkings_id.toString())
        }
        // 패키지 상품이나 SMM Panel 서비스 ID가 없는 경우는 그대로 유지
        // (패키지 상품은 여러 단계로 구성되어 있어서 SMM Panel 서비스 ID가 없을 수 있음)
        return true
      })
    }
    return services
  }

  // SMM Panel 서비스 목록 로드
  const loadSMMServices = async () => {
    setIsLoadingServices(true)
    try {
      const response = await fetch(`${window.location.origin}/api/smm-panel/services`)
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setValidServiceIds(data.service_ids || [])
        }
      }
    } catch (error) {
      // SMM Panel 서비스 목록 로드 실패 시 무시
    } finally {
      setIsLoadingServices(false)
    }
  }

  // 카탈로그 데이터 로드 (카테고리, 상품, 세부서비스, 패키지)
  const loadCatalog = async () => {
    setIsLoadingCatalog(true)
    const errors = []
    
    try {
      // 카테고리 로드
      try {
        const categoriesRes = await fetch('/api/categories')
        if (categoriesRes.ok) {
          const categoriesData = await categoriesRes.json()
          setCategories(categoriesData.categories || [])
          console.log('✅ 카테고리 로드 완료:', categoriesData.categories?.length || 0, '개')
        } else {
          const errorData = await categoriesRes.json().catch(() => ({}))
          const errorMsg = errorData.error || `카테고리 로드 실패 (${categoriesRes.status})`
          console.error('❌', errorMsg)
          errors.push(errorMsg)
        }
      } catch (error) {
        console.error('❌ 카테고리 로드 오류:', error)
        errors.push('카테고리 로드 중 네트워크 오류가 발생했습니다.')
      }

      // 상품 로드
      try {
        const productsRes = await fetch('/api/products')
        if (productsRes.ok) {
          const productsData = await productsRes.json()
          setProducts(productsData.products || [])
          console.log('✅ 상품 로드 완료:', productsData.products?.length || 0, '개')
        } else {
          const errorData = await productsRes.json().catch(() => ({}))
          const errorMsg = errorData.error || `상품 로드 실패 (${productsRes.status})`
          console.error('❌', errorMsg)
          errors.push(errorMsg)
        }
      } catch (error) {
        console.error('❌ 상품 로드 오류:', error)
        errors.push('상품 로드 중 네트워크 오류가 발생했습니다.')
      }

      // 세부서비스 로드
      try {
        const variantsRes = await fetch('/api/product-variants')
        if (variantsRes.ok) {
          const variantsData = await variantsRes.json()
          // variants 형식 정규화 (API 응답 형식에 맞춤)
          const normalizedVariants = (variantsData.variants || variantsData || []).map(v => ({
            variant_id: v.variant_id || v.id,
            product_id: v.product_id,
            category_id: v.category_id,
            name: v.name,
            price: parseFloat(v.price || 0),
            min_quantity: parseInt(v.min || v.min_quantity || 1),
            max_quantity: parseInt(v.max || v.max_quantity || 1000000),
            delivery_time_days: v.delivery_time_days,
            meta_json: v.meta_json || (typeof v.meta_json === 'string' ? JSON.parse(v.meta_json) : {}),
            api_endpoint: v.api_endpoint,
            product_name: v.product_name,
            category_name: v.category_name,
            // 하위 호환성을 위한 필드
            id: v.variant_id || v.id,
            min: parseInt(v.min || v.min_quantity || 1),
          max: parseInt(v.max || v.max_quantity || 1000000),
          }))
          setVariants(normalizedVariants)
          console.log('✅ 세부서비스 로드 완료:', normalizedVariants.length, '개')
        } else {
          const errorData = await variantsRes.json().catch(() => ({}))
          const errorMsg = errorData.error || `세부서비스 로드 실패 (${variantsRes.status})`
          console.error('❌', errorMsg)
          errors.push(errorMsg)
        }
      } catch (error) {
        console.error('❌ 세부서비스 로드 오류:', error)
        errors.push('세부서비스 로드 중 네트워크 오류가 발생했습니다.')
      }

      // 패키지 로드
      try {
        const packagesRes = await fetch('/api/packages')
        if (packagesRes.ok) {
          const packagesData = await packagesRes.json()
          setPackages(packagesData.packages || [])
          console.log('✅ 패키지 로드 완료:', packagesData.packages?.length || 0, '개')
        } else {
          const errorData = await packagesRes.json().catch(() => ({}))
          const errorMsg = errorData.error || `패키지 로드 실패 (${packagesRes.status})`
          console.error('❌', errorMsg)
          errors.push(errorMsg)
        }
      } catch (error) {
        console.error('❌ 패키지 로드 오류:', error)
        errors.push('패키지 로드 중 네트워크 오류가 발생했습니다.')
      }

      // 에러가 있으면 사용자에게 알림
      if (errors.length > 0) {
        console.warn('⚠️ 일부 카탈로그 데이터 로드 실패:', errors)
        // 데이터베이스 연결 문제인 경우 하드코딩된 데이터 사용 가능
        console.log('💡 데이터베이스 연결 문제로 하드코딩된 데이터를 사용합니다.')
      }
    } catch (error) {
      console.error('❌ 카탈로그 로드 중 예기치 않은 오류:', error)
    } finally {
      setIsLoadingCatalog(false)
    }
  }


  // 컴포넌트 마운트 시 카탈로그 및 SMM 서비스 목록 로드
  useEffect(() => {
    loadCatalog()
    loadSMMServices()
  }, [])

  // 플랫폼/서비스 변경 시 세부 서비스 자동 선택
  useEffect(() => {
    if (selectedPlatform && selectedService && !selectedDetailedService) {
      const detailedServices = getDetailedServices(selectedPlatform, selectedService)
      if (detailedServices && detailedServices.length > 0) {
        setSelectedDetailedService(detailedServices[0])
        // 패키지 상품 또는 drip-feed 상품은 수량을 1로 고정
        if (detailedServices[0].package || detailedServices[0].drip_feed) {
          setQuantity(1)
        } else {
        setQuantity(detailedServices[0].min)
        }
      }
    }
  }, [selectedPlatform, selectedService, selectedDetailedService, variants, packages])

  // 추천인 시스템은 커미션 방식 - 피추천인 구매 금액의 10%를 추천인에게 커미션으로 지급 (백엔드에서 자동 처리)
  // 할인 쿠폰 관련 코드는 모두 제거됨

  // 인스타그램 세부 서비스 데이터
  
  
  // 세부 서비스 목록 가져오기 (데이터베이스 우선, 하드코딩 fallback)
  const getDetailedServices = (platform, serviceType) => {
    // 먼저 데이터베이스에서 가져온 variants와 packages 사용 시도
    let dbServices = []
    
    // 카테고리 이름으로 필터링 (예: '인스타그램', '유튜브' 등)
    const categoryNameMap = {
      'instagram': '인스타그램',
      'youtube': '유튜브',
      'facebook': '페이스북',
      'tiktok': '틱톡',
      'twitter': '트위터',
      'threads': 'Threads',
      'telegram': '텔레그램',
      'whatsapp': 'WhatsApp',
      'kakao': '카카오'
    }
    
    // 플랫폼에 맞는 카테고리 찾기
    const targetCategory = categories.find(c => 
      c.name?.includes(categoryNameMap[platform] || platform) || 
      c.slug === platform
    )
    
    if (targetCategory) {
      // serviceType(상품 ID)에 해당하는 상품 찾기
      const targetProduct = products.find(p => 
        p.category_id === targetCategory.category_id && (
          p.name?.toLowerCase().includes(serviceType?.toLowerCase() || '') ||
          p.description?.toLowerCase().includes(serviceType?.toLowerCase() || '')
        )
      )
      
      // serviceType으로 직접 매칭 시도 (상품 이름이나 설명에 serviceType이 포함된 경우)
      // 또는 products 배열에서 serviceType과 일치하는 상품 찾기
      let matchedProduct = products.find(p => {
        if (p.category_id !== targetCategory.category_id) return false
        
        // serviceType이 상품 이름이나 설명에 포함되어 있는지 확인
        const productNameLower = (p.name || '').toLowerCase()
        const productDescLower = (p.description || '').toLowerCase()
        const serviceTypeLower = (serviceType || '').toLowerCase()
        
        // 정확한 매칭: serviceType이 상품 이름의 키워드와 일치하는지
        // 예: serviceType='likes_korean' -> 상품 이름에 '좋아요' 또는 'likes' 포함
        const serviceTypeKeywords = {
          'likes_korean': ['좋아요', 'likes'],
          'followers_korean': ['팔로워', 'followers'],
          'comments_korean': ['댓글', 'comments'],
          'reels_views_korean': ['릴스', '조회수', 'reels', 'views'],
          'regram_korean': ['리그램', 'regram'],
          'exposure_save_share': ['노출', '저장', '공유', 'exposure', 'save', 'share'],
          'auto_likes': ['자동', '좋아요', 'auto', 'likes'],
          'auto_views': ['자동', '조회수', 'auto', 'views'],
          'auto_comments': ['자동', '댓글', 'auto', 'comments'],
          'auto_followers': ['자동', '팔로워', 'auto', 'followers'],
          'auto_regram': ['자동', '리그램', 'auto', 'regram'],
          'custom_comments_korean': ['커스텀', '이모지', '댓글', 'custom', 'comments'],
          'popular_posts': ['인기게시물', '상위', 'popular', 'posts'],
          'followers_foreign': ['외국인', '팔로워', 'foreign', 'followers'],
          'likes_foreign': ['외국인', '좋아요', 'foreign', 'likes'],
          'comments_foreign': ['외국인', '댓글', 'foreign', 'comments'],
          'reels_views_foreign': ['외국인', '릴스', '조회수', 'foreign', 'reels', 'views'],
          'exposure_save_share_foreign': ['외국인', '노출', '저장', '공유', 'foreign'],
          'live_streaming': ['라이브', '스트리밍', 'live', 'streaming'],
          'auto_likes_foreign': ['외국인', '자동', '좋아요', 'foreign', 'auto', 'likes'],
          'auto_followers_foreign': ['외국인', '자동', '팔로워', 'foreign', 'auto', 'followers'],
          'auto_comments_foreign': ['외국인', '자동', '댓글', 'foreign', 'auto', 'comments'],
          'auto_reels_views_foreign': ['외국인', '자동', '릴스', '조회수', 'foreign', 'auto'],
          'auto_exposure_save_share_foreign': ['외국인', '자동', '노출', '저장', '공유', 'foreign', 'auto'],
        }
        
        const keywords = serviceTypeKeywords[serviceType] || [serviceTypeLower]
        return keywords.some(keyword => 
          productNameLower.includes(keyword.toLowerCase()) || 
          productDescLower.includes(keyword.toLowerCase())
        )
      })
      
      if (matchedProduct) {
        // 해당 상품의 variants만 필터링하고 형식 변환
        dbServices = variants.filter(v => 
          v.product_id === matchedProduct.product_id
        ).map(v => ({
          id: v.variant_id || v.id,
          name: v.name,
          price: parseFloat(v.price || 0),
          min: parseInt(v.min_quantity || v.min || 1),
          max: parseInt(v.max_quantity || v.max || 1000000),
          time: v.meta_json?.time || v.delivery_time_days ? `${v.delivery_time_days}일` : '데이터가 충분하지 않습니다',
          description: v.meta_json?.description || v.description || '',
          smm_service_id: v.meta_json?.smm_service_id || v.smm_service_id,
          meta_json: v.meta_json || {},
        }))
        
        // 해당 상품의 패키지도 추가
        const productPackages = packages.filter(p => 
          p.category_id === targetCategory.category_id && 
          (p.name?.toLowerCase().includes(serviceType?.toLowerCase() || '') ||
           p.description?.toLowerCase().includes(serviceType?.toLowerCase() || ''))
        )
        
        // 패키지를 variant 형식으로 변환
        productPackages.forEach(pkg => {
          dbServices.push({
            id: pkg.package_id,
            name: pkg.name,
            price: pkg.price || 0,
            min: 1,
            max: 1,
            time: pkg.meta_json?.time || '데이터가 충분하지 않습니다',
            description: pkg.description,
            package: true,
            steps: pkg.steps || pkg.items || [],
            drip_feed: pkg.meta_json?.drip_feed || false,
            smmkings_id: pkg.meta_json?.smmkings_id,
            runs: pkg.meta_json?.runs,
            interval: pkg.meta_json?.interval,
            drip_quantity: pkg.meta_json?.drip_quantity,
          })
        })
      } else {
        // 상품을 찾지 못한 경우, 카테고리 전체 variants 사용 (fallback)
        dbServices = variants.filter(v => 
          v.category_id === targetCategory.category_id
        )
        
        // 패키지도 추가
        const categoryPackages = packages.filter(p => 
          p.category_id === targetCategory.category_id
        )
        
        categoryPackages.forEach(pkg => {
          dbServices.push({
            id: pkg.package_id,
            name: pkg.name,
            price: pkg.price || 0,
            min: 1,
            max: 1,
            time: pkg.meta_json?.time || '데이터가 충분하지 않습니다',
            description: pkg.description,
            package: true,
            steps: pkg.steps || pkg.items || [],
            drip_feed: pkg.meta_json?.drip_feed || false,
            smmkings_id: pkg.meta_json?.smmkings_id,
            runs: pkg.meta_json?.runs,
            interval: pkg.meta_json?.interval,
            drip_quantity: pkg.meta_json?.drip_quantity,
          })
        })
      }
    }
    
    // 데이터베이스에서 서비스를 찾았으면 반환
    if (dbServices.length > 0) {
      console.log(`✅ 데이터베이스에서 ${dbServices.length}개 서비스 로드: ${platform}/${serviceType}`)
      return filterValidServices(dbServices)
    }
    
    // 데이터베이스에 없으면 기존 하드코딩된 데이터 사용 (fallback)
    console.log(`⚠️ 데이터베이스에 서비스 없음, 하드코딩 데이터 사용: ${platform}/${serviceType}`)
    
    // 추천서비스 매핑 (기존 하드코딩)
    if (platform === 'recommended') {
      if (serviceType === 'top_exposure_30days') {
        return filterValidServices(instagramDetailedServices.top_exposure?.manual?.filter(s => s.id === 1005) || [])
      } else if (serviceType === 'recommended_tab_entry') {
        return filterValidServices(instagramDetailedServices.top_exposure?.manual?.filter(s => s.id === 1003) || [])
      } else if (serviceType === 'instagram_followers') {
        return filterValidServices(instagramDetailedServices.followers_korean || [])
      } else if (serviceType === 'instagram_reels_views') {
        return filterValidServices(instagramDetailedServices.reels_views_korean || [])
      } else if (serviceType === 'instagram_optimization_30days') {
        return filterValidServices(instagramDetailedServices.top_exposure?.manual?.filter(s => s.id === 1002) || [])
      } else if (serviceType === 'recommended_tab_maintenance') {
        return filterValidServices(instagramDetailedServices.top_exposure?.manual?.filter(s => s.id === 1004) || [])
      } else if (serviceType === 'instagram_korean_likes') {
        return filterValidServices(instagramDetailedServices.likes_korean || [])
      } else if (serviceType === 'instagram_regram') {
        return filterValidServices(instagramDetailedServices.regram_korean || [])
      }
      return filterValidServices([])
    }
  
  // 이벤트 매핑
  if (platform === 'event') {
    if (serviceType === 'instagram_korean_followers_bulk') {
      return filterValidServices(instagramDetailedServices.followers_korean || [])
    } else if (serviceType === 'instagram_korean_likes_bulk') {
      return filterValidServices(instagramDetailedServices.likes_korean || [])
    }
    return filterValidServices([])
  }
  
  // 상위노출 매핑
  if (platform === 'top-exposure') {
    const services = instagramDetailedServices.top_exposure || {}
    if (serviceType === 'top_exposure_30days') {
      return filterValidServices(services.manual?.filter(s => s.id === 1005) || [])
    } else if (serviceType === 'instagram_optimization_30days') {
      return filterValidServices(services.manual?.filter(s => s.id === 1002) || [])
    } else if (serviceType === 'recommended_tab_entry') {
      return filterValidServices(services.manual?.filter(s => s.id === 1003) || [])
    } else if (serviceType === 'recommended_tab_maintenance') {
      return filterValidServices(services.manual?.filter(s => s.id === 1004) || [])
    }
    return filterValidServices([])
    }
    if (platform === 'instagram' && instagramDetailedServices[serviceType]) {
      return filterValidServices(instagramDetailedServices[serviceType])
    }
    
    // 인스타그램 외국인 서비스 매핑
    if (platform === 'instagram' && instagramDetailedServices) {
      if (serviceType === 'foreign_package') {
        return filterValidServices(instagramDetailedServices.foreign_package || [])
      } else if (serviceType === 'followers_foreign') {
        return filterValidServices(instagramDetailedServices.followers_foreign || [])
      } else if (serviceType === 'likes_foreign') {
        return filterValidServices(instagramDetailedServices.likes_foreign || [])
      } else if (serviceType === 'comments_foreign') {
        return filterValidServices(instagramDetailedServices.comments_foreign || [])
      } else if (serviceType === 'reels_views_foreign') {
        return filterValidServices(instagramDetailedServices.reels_views_foreign || [])
      } else if (serviceType === 'exposure_save_share_foreign') {
        return filterValidServices(instagramDetailedServices.exposure_save_share_foreign || [])
      } else if (serviceType === 'live_streaming') {
        return filterValidServices(instagramDetailedServices.live_streaming || [])
      } else if (serviceType === 'auto_likes_foreign') {
        return filterValidServices(instagramDetailedServices.auto_likes_foreign || [])
      } else if (serviceType === 'auto_followers_foreign') {
        return filterValidServices(instagramDetailedServices.auto_followers_foreign || [])
      } else if (serviceType === 'auto_comments_foreign') {
        return filterValidServices(instagramDetailedServices.auto_comments_foreign || [])
      } else if (serviceType === 'auto_reels_views_foreign') {
        return filterValidServices(instagramDetailedServices.auto_reels_views_foreign || [])
      } else if (serviceType === 'auto_exposure_save_share_foreign') {
        return filterValidServices(instagramDetailedServices.auto_exposure_save_share_foreign || [])
      }
    }
    
    // 유튜브 서비스 매핑
    if (platform === 'youtube' && instagramDetailedServices.youtube) {
      if (serviceType === 'views_korean') {
        return filterValidServices(instagramDetailedServices.youtube.views.filter(service => service.name.includes('한국')))
      } else if (serviceType === 'views_foreign') {
        return filterValidServices(instagramDetailedServices.youtube.views.filter(service => !service.name.includes('한국')))
      } else if (serviceType === 'likes_korean') {
        return filterValidServices(instagramDetailedServices.youtube.likes.filter(service => service.name.includes('한국')))
      } else if (serviceType === 'likes_foreign') {
        return filterValidServices(instagramDetailedServices.youtube.likes.filter(service => !service.name.includes('한국')))
      } else if (serviceType === 'subscribers_korean') {
        return filterValidServices(instagramDetailedServices.youtube.subscribers.filter(service => service.name.includes('한국')))
      } else if (serviceType === 'subscribers_foreign') {
        return filterValidServices(instagramDetailedServices.youtube.subscribers.filter(service => !service.name.includes('한국')))
      } else if (serviceType === 'comments_korean') {
        return filterValidServices((instagramDetailedServices.youtube.comments_shares || []).filter(service => service.name.includes('한국') && service.name.includes('댓글')))
      } else if (serviceType === 'comments_foreign') {
        return filterValidServices((instagramDetailedServices.youtube.comments_shares || []).filter(service => !service.name.includes('한국') && service.name.includes('댓글')))
      } else if (serviceType === 'shares_korean') {
        return filterValidServices((instagramDetailedServices.youtube.comments_shares || []).filter(service => service.name.includes('한국') && service.name.includes('공유')))
      } else if (serviceType === 'auto_views_foreign') {
        return filterValidServices(instagramDetailedServices.youtube.auto_views || [])
      } else if (serviceType === 'auto_likes_foreign') {
        return filterValidServices(instagramDetailedServices.youtube.auto_likes || [])
      } else if (serviceType === 'live_streaming') {
        return filterValidServices(instagramDetailedServices.youtube.live_streaming || [])
      }
    }
    
    // 페이스북 서비스 매핑
    if (platform === 'facebook' && instagramDetailedServices.facebook) {
      if (serviceType === 'page_likes_korean') {
        return instagramDetailedServices.facebook.page_likes_korean || []
      } else if (serviceType === 'post_likes_korean') {
        return instagramDetailedServices.facebook.post_likes_korean || []
      } else if (serviceType === 'post_comments_korean') {
        return instagramDetailedServices.facebook.post_comments_korean || []
      } else if (serviceType === 'profile_follows_korean') {
        return instagramDetailedServices.facebook.profile_follows_korean || []
      } else if (serviceType === 'event_page_likes_foreign') {
        return (instagramDetailedServices.facebook.foreign_services || []).filter(service => 
          service.name.includes('페이지 좋아요') || service.name.includes('페이지 팔로워')
        )
      } else if (serviceType === 'page_followers_foreign') {
        return (instagramDetailedServices.facebook.foreign_services || []).filter(service => 
          service.name.includes('페이지 팔로워') || service.name.includes('페이지 팔로우')
        )
      } else if (serviceType === 'post_likes_foreign') {
        return (instagramDetailedServices.facebook.foreign_services || []).filter(service => 
          service.name.includes('게시물 좋아요')
        )
      } else if (serviceType === 'profile_followers_foreign') {
        return (instagramDetailedServices.facebook.foreign_services || []).filter(service => 
          service.name.includes('프로필 팔로워') || service.name.includes('프로필 팔로우')
        )
      } else if (serviceType === 'post_comments_foreign') {
        return (instagramDetailedServices.facebook.foreign_services || []).filter(service => 
          service.name.includes('댓글') || service.name.includes('리액션')
        )
      }
    }
    
    // 스레드 서비스 매핑
    if (platform === 'threads' && instagramDetailedServices.threads) {
      if (serviceType === 'likes') {
        return [instagramDetailedServices.threads.likes_korean[0]] // 좋아요 서비스
      } else if (serviceType === 'comments') {
        return [instagramDetailedServices.threads.likes_korean[2]] // 댓글 서비스
      } else if (serviceType === 'followers') {
        return [instagramDetailedServices.threads.likes_korean[1]] // 팔로워 서비스
      } else if (serviceType === 'shares') {
        return [instagramDetailedServices.threads.likes_korean[3]] // 공유 서비스
      }
    }
    
    // 틱톡 서비스 매핑
    if (platform === 'tiktok' && instagramDetailedServices.tiktok) {
      if (serviceType === 'likes_foreign') {
        return instagramDetailedServices.tiktok.likes_foreign || []
      } else if (serviceType === 'views_foreign') {
        return instagramDetailedServices.tiktok.views_foreign || []
      } else if (serviceType === 'views_korean') {
        return instagramDetailedServices.tiktok.views_korean || []
      } else if (serviceType === 'followers_foreign') {
        return instagramDetailedServices.tiktok.followers_foreign || []
      } else if (serviceType === 'save_share') {
        return instagramDetailedServices.tiktok.save_share || []
      } else if (serviceType === 'live_streaming') {
        return instagramDetailedServices.tiktok.live_streaming || []
      }
    }
    
    // 트위터 서비스 매핑
    if (platform === 'twitter' && instagramDetailedServices.twitter) {
      if (serviceType === 'twitter_services') {
        return instagramDetailedServices.twitter.followers_foreign || []
      }
    }
    
    // 텔레그램 서비스 매핑
    if (platform === 'telegram' && instagramDetailedServices.telegram) {
      if (serviceType === 'telegram_services') {
        return [
          ...(instagramDetailedServices.telegram.subscribers || []),
          ...(instagramDetailedServices.telegram.views || [])
        ]
      }
    }
    
    // 왓츠앱 서비스 매핑
    if (platform === 'whatsapp' && instagramDetailedServices.whatsapp) {
      if (serviceType === 'whatsapp_services') {
        return instagramDetailedServices.whatsapp.followers || []
      }
    }
    
    // 카카오 서비스 매핑
    if (platform === 'kakao' && instagramDetailedServices.kakao_naver) {
      if (serviceType === 'kakao_services') {
        return instagramDetailedServices.kakao_naver.kakao_services || []
      }
    }
    
    // 기존 로직 사용
    const services = getDetailedServicesLegacy(platform, serviceType)
    return filterValidServices(services)
  }

  // 선택된 세부 서비스 정보 가져오기
  const getSelectedDetailedService = () => {
    if (selectedDetailedService && selectedPlatform === 'instagram') {
      const services = getDetailedServices(selectedPlatform, selectedService)
      return services.find(service => service.id === selectedDetailedService.id)
    }
    return null
  }

  // 가격 계산 (인스타그램용)
  const calculateInstagramPrice = () => {
    if (selectedDetailedService && selectedPlatform === 'instagram') {
      const selectedService = getSelectedDetailedService()
      if (selectedService) {
        return (selectedService.price / 1000) * quantity // 1000개 가격을 1개 가격으로 변환
      }
    }
    return 0
  }

  const platforms = [
    { id: 'recommended', name: '추천서비스', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/recommend.svg', color: '#f59e0b' },
    { id: 'event', name: '이벤트', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/brand.svg', color: '#8b5cf6' },
    { id: 'top-exposure', name: '상위노출', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/top.svg', color: '#f59e0b' },
    { id: 'instagram', name: '인스타그램', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/instagram.svg', color: '#e4405f' },
    { id: 'youtube', name: '유튜브', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/youtube.svg', color: '#ff0000' },
    { id: 'facebook', name: '페이스북', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/facebook.svg', color: '#1877f2' },
    { id: 'tiktok', name: '틱톡', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/tiktok.svg', color: '#000000' },
    { id: 'threads', name: '스레드', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/threads.svg', color: '#000000' },
    { id: 'twitter', name: '트위터', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/X.svg', color: '#1da1f2' },
    { id: 'kakao', name: '카카오', icon: 'https://assets.snsshop.kr/assets/img2/new-order/platform/kakao.svg', color: '#fbbf24' },
    { id: 'telegram', name: '텔레그램', icon: '/TelegramLogo.svg.png', color: '#0088cc' },
    { id: 'whatsapp', name: '왓츠앱', icon: '/whatsapp-logo-new.svg', color: '#25d366' },
    // { id: 'news-media', name: '뉴스언론보도', icon: FileText, color: '#3b82f6' },
    // { id: 'experience-group', name: '체험단', icon: Users, color: '#10b981' },
   
    // { id: 'store-marketing', name: '스토어마케팅', icon: HomeIcon, color: '#f59e0b' },
    // { id: 'app-marketing', name: '어플마케팅', icon: Smartphone, color: '#3b82f6' },
    // { id: 'seo-traffic', name: 'SEO트래픽', icon: TrendingUp, color: '#8b5cf6' }
  ]

    // 플랫폼별 서비스 목록



    
  const getServicesForPlatform = (platform) => {
    switch (platform) {
      case 'recommended':
        return [
          { id: 'top_exposure_30days', name: '인스타 계정 상위노출 [30일]', description: '인스타그램 계정 상위노출 서비스' },
          { id: 'recommended_tab_entry', name: '추천탭 상위노출 (본인계정) - 진입단계', description: '추천탭 상위노출 진입단계 서비스' },
          { id: 'instagram_followers', name: '인스타 팔로워 늘리기', description: '인스타그램 팔로워 증가 서비스' },
          { id: 'instagram_reels_views', name: '인스타 릴스 조회수 늘리기', description: '인스타그램 릴스 조회수 증가 서비스' },
          { id: 'instagram_optimization_30days', name: '인스타 최적화 계정만들기 [30일]', description: '인스타그램 최적화 계정 생성 서비스' },
          { id: 'recommended_tab_maintenance', name: '추천탭 상위노출 (본인계정) - 유지단계', description: '추천탭 상위노출 유지단계 서비스' },
          { id: 'instagram_korean_likes', name: '인스타 한국인 좋아요 늘리기', description: '인스타그램 한국인 좋아요 증가 서비스' },
          { id: 'instagram_regram', name: '인스타 리그램', description: '인스타그램 리그램 서비스' }
        ]
      case 'event':
        return [
          { id: 'instagram_korean_followers_bulk', name: '인스타 한국인 팔로워 대량 구매', description: '인스타그램 한국인 팔로워 대량 구매 서비스' },
          { id: 'instagram_korean_likes_bulk', name: '인스타 한국인 좋아요 대량 구매', description: '인스타그램 한국인 좋아요 대량 구매 서비스' }
        ]
      case 'top-exposure':
        return [
          { id: 'top_exposure_30days', name: '인스타 계정 상위노출 [30일]', description: '인스타그램 계정 상위노출 서비스' },
          { id: 'instagram_optimization_30days', name: '인스타 최적화 계정만들기 [30일]', description: '인스타그램 최적화 계정 생성 서비스' },
          { id: 'recommended_tab_entry', name: '추천탭 상위노출 (본인계정) - 진입단계', description: '추천탭 상위노출 진입단계 서비스' },
          { id: 'recommended_tab_maintenance', name: '추천탭 상위노출 (본인계정) - 유지단계', description: '추천탭 상위노출 유지단계 서비스' }
        ]
      case 'instagram':
        return [
          // 한국인 서비스 (12개)
          { id: 'korean_package', name: '인스타 한국인 패키지', description: '한국인 종합 패키지 서비스' },
          { id: 'reels_views_korean', name: '인스타 릴스 조회수 늘리기', description: '한국인 릴스 조회수 서비스' },
          { id: 'likes_korean', name: '인스타 좋아요 늘리기', description: '한국인 좋아요 서비스' },
          { id: 'regram_korean', name: '인스타 리그램', description: '한국인 리그램 서비스' },
          { id: 'exposure_save_share', name: '인스타 도달, 저장, 공유 등', description: '노출, 도달, 저장, 공유 서비스' },
          { id: 'auto_comments', name: '댓글 늘리기', description: '자동 댓글 서비스' },
          { id: 'custom_comments_korean', name: '인스타 커스텀/이모지 댓글', description: '한국인 커스텀/이모지 댓글 서비스' },
          { id: 'auto_likes', name: '좋아요 늘리기', description: '자동 좋아요 서비스' },
          { id: 'followers_korean', name: '인스타 팔로워 늘리기', description: '한국인 팔로워 서비스' },
          { id: 'auto_followers', name: '팔로워 늘리기', description: '자동 팔로워 서비스' },
          { id: 'comments_korean', name: '인스타 댓글 늘리기', description: '한국인 댓글 서비스' },
          { id: 'auto_regram', name: '리그램', description: '자동 리그램 서비스' },
          
          // 외국인 서비스 (12개)
          { id: 'foreign_package', name: '인스타 외국인 패키지', description: '외국인 종합 패키지 서비스' },
          { id: 'followers_foreign', name: '인스타 팔로워 늘리기', description: '외국인 팔로워 서비스' },
          { id: 'likes_foreign', name: '인스타 좋아요 늘리기', description: '외국인 좋아요 서비스' },
          
          { id: 'auto_reels_views_foreign', name: '조회수 늘리기', description: '외국인 자동 릴스 조회수 서비스' },
          { id: 'reels_views_foreign', name: '인스타 릴스 조회수 늘리기', description: '외국인 릴스 조회수 서비스' },
          { id: 'auto_followers_foreign', name: '팔로워 늘리기', description: '외국인 자동 팔로워 서비스' },
          { id: 'live_streaming', name: '인스타 실시간 라이브 스트리밍 시청', description: '실시간 라이브 스트리밍 시청 서비스' },
          { id: 'auto_likes_foreign', name: '좋아요 늘리기', description: '외국인 자동 좋아요 서비스' },
          { id: 'exposure_save_share_foreign', name: '인스타 노출, 도달, 저장, 공유 등', description: '외국인 노출, 도달, 저장, 공유 서비스' },
          { id: 'auto_comments_foreign', name: '댓글 늘리기', description: '외국인 자동 댓글 서비스' },
          { id: 'comments_foreign', name: '인스타 댓글 늘리기', description: '외국인 댓글 서비스' },
          { id: 'auto_exposure_save_share_foreign', name: '노출,도달,저장,공유', description: '외국인 자동 노출, 도달, 저장, 공유 서비스' }
        ]
      case 'youtube':
        return [
          // 한국인 서비스 (5개)
          { id: 'views_korean', name: '유튜브 조회수 늘리기', description: '한국인 조회수 서비스' },
          { id: 'empty_service_korean', name: ' ', description: ' ' },
          { id: 'likes_korean', name: '유튜브 좋아요 늘리기', description: '한국인 좋아요 서비스' },
          { id: 'subscribers_korean', name: '유튜브 구독자 늘리기', description: '한국인 구독자 서비스' },
          { id: 'no', name: 'no', description: ' ' },
          
          { id: 'comments_korean', name: '유튜브 댓글 늘리기', description: '한국인 댓글 서비스' },
          { id: 'shares_korean', name: '유튜브 공유 늘리기', description: '한국인 공유 서비스' },
          
          // 외국인 서비스 (7개)
          { id: 'views_foreign', name: '유튜브 조회수 늘리기', description: '외국인 조회수 서비스' },
          { id: 'empty_service_foreign', name: ' ', description: ' ' },
          { id: 'likes_foreign', name: '유튜브 좋아요 늘리기', description: '외국인 좋아요 서비스' },
          { id: 'subscribers_foreign', name: '유튜브 구독자 늘리기', description: '외국인 구독자 서비스' },
          { id: 'comments_foreign', name: '유튜브 댓글 늘리기', description: '외국인 댓글 서비스' },
          { id: 'auto_likes_foreign', name: '좋아요 늘리기', description: '외국인 자동 좋아요 서비스' },
          { id: 'live_streaming', name: '유튜브 실시간 라이브 스트리밍 시청', description: '실시간 라이브 스트리밍 시청 서비스' },
          { id: 'auto_views_foreign', name: '조회수 늘리기', description: '외국인 자동 조회수 서비스' },
        ]
      case 'tiktok':
        return [
          { id: 'likes_foreign', name: '틱톡 외국인 좋아요', description: '외국인 좋아요 서비스' },
          { id: 'views_foreign', name: '틱톡 외국인 조회수', description: '외국인 조회수 서비스' },
          { id: 'views_korean', name: '틱톡 한국인 조회수', description: '한국인 조회수 서비스' },
          { id: 'followers_foreign', name: '틱톡 외국인 팔로워', description: '외국인 팔로워 서비스' },
          { id: 'save_share', name: '틱톡 저장/공유', description: '저장/공유 서비스' },
          { id: 'live_streaming', name: '틱톡 라이브 스트리밍', description: '라이브 스트리밍 서비스' }
        ]
      case 'facebook':
        return [
          // 한국인 서비스 (4개)
          { id: 'page_likes_korean', name: '페이스북 페이지 좋아요', description: '한국인 페이지 좋아요 서비스' },
          { id: 'post_likes_korean', name: '페이스북 게시물 좋아요', description: '한국인 게시물 좋아요 서비스' },
          { id: 'post_comments_korean', name: '페이스북 게시물 댓글', description: '한국인 게시물 댓글 서비스' },
          { id: 'profile_follows_korean', name: '페이스북 개인계정 팔로우', description: '한국인 개인계정 팔로우 서비스' },
          
          // 외국인 서비스 (5개)
          { id: 'event_page_likes_foreign', name: '이벤트 : 페이스북 페이지 좋아요 + 팔로워', description: '외국인 이벤트 페이지 좋아요+팔로워 서비스' },
          { id: 'empty_service', name: ' ', description: ' ' },
          { id: 'page_followers_foreign', name: '페이스북 페이지 팔로워', description: '외국인 페이지 팔로워 서비스' },
          { id: 'post_likes_foreign', name: '페이스북 게시물 좋아요', description: '외국인 게시물 좋아요 서비스' },
          { id: 'profile_followers_foreign', name: '페이스북 프로필 팔로워', description: '외국인 프로필 팔로워 서비스' },
          { id: 'post_comments_foreign', name: '페이스북 게시물 댓글', description: '외국인 게시물 댓글 서비스' }

        ]
      case 'threads':
        return [
          { id: 'likes', name: '스레드 좋아요 늘리기', description: '좋아요 서비스' },
          { id: 'comments', name: '스레드 댓글 늘리기', description: '댓글 서비스' },
          { id: 'followers', name: '스레드 팔로우 늘리기', description: '팔로우 서비스' },
          { id: 'shares', name: '스레드 공유 늘리기', description: '공유 서비스' }
        ]
      case 'naver':
        return [
          { id: 'n_k_services', name: 'N사 / K사 서비스', description: '네이버/카카오 서비스' }
        ]
      case 'kakao':
        return [
          { id: 'kakao_services', name: '카카오 서비스', description: '카카오 서비스' }
        ]
      case 'twitter':
        return [
          { id: 'twitter_services', name: '트위터 서비스', description: '트위터 서비스' }
        ]
      case 'telegram':
        return [
          { id: 'telegram_services', name: '텔레그램 서비스', description: '텔레그램 서비스' }
        ]
      case 'whatsapp':
        return [
          { id: 'whatsapp_services', name: '왓츠앱 서비스', description: '왓츠앱 서비스' }
        ]
      default:
        return []
    }
  }

  // 사용 가능한 서비스 목록 가져오기
  const getAvailableServices = (platform) => {
    // 플랫폼별 서비스 데이터 반환
    if (platform === 'instagram') {
      return Object.values(instagramDetailedServices).flat()
    } else if (platform === 'youtube' && instagramDetailedServices.youtube) {
      return Object.values(instagramDetailedServices.youtube).flat()
    } else if (platform === 'facebook' && instagramDetailedServices.facebook) {
      return Object.values(instagramDetailedServices.facebook).flat()
    } else if (platform === 'threads' && instagramDetailedServices.threads) {
      return Object.values(instagramDetailedServices.threads).flat()
    } else if (platform === 'tiktok' && instagramDetailedServices.tiktok) {
      return Object.values(instagramDetailedServices.tiktok).flat()
    } else if (platform === 'twitter' && instagramDetailedServices.twitter) {
      return Object.values(instagramDetailedServices.twitter).flat()
    } else if (platform === 'telegram' && instagramDetailedServices.telegram) {
      return Object.values(instagramDetailedServices.telegram).flat()
    } else if (platform === 'whatsapp' && instagramDetailedServices.whatsapp) {
      return Object.values(instagramDetailedServices.whatsapp).flat()
    } else if (platform === 'kakao' && instagramDetailedServices.kakao) {
      return Object.values(instagramDetailedServices.kakao).flat()
    }
    
    // 기본 서비스 목록 (실제로는 API에서 가져와야 함)
    return [
      //{ id: 'followers_korean', name: '한국인 팔로워', price: 1000, min: 10, max: 10000 },
      //{ id: 'likes_korean', name: '한국인 좋아요', price: 500, min: 10, max: 10000 },
      //{ id: 'comments_korean', name: '한국인 댓글', price: 2000, min: 5, max: 1000 }
    ]
  }

  // 서비스 타입별 세부 서비스 목록 (기존 로직 유지)
  const getDetailedServicesLegacy = (platform, serviceType) => {
    // 플랫폼별로 직접 서비스 데이터 가져오기
    let availableServices = []
    if (platform === 'instagram') {
      availableServices = Object.values(instagramDetailedServices).flat()
    } else if (platform === 'youtube' && instagramDetailedServices.youtube) {
      availableServices = Object.values(instagramDetailedServices.youtube).flat()
    } else if (platform === 'facebook' && instagramDetailedServices.facebook) {
      availableServices = Object.values(instagramDetailedServices.facebook).flat()
    } else if (platform === 'threads' && instagramDetailedServices.threads) {
      availableServices = Object.values(instagramDetailedServices.threads).flat()
    } else if (platform === 'tiktok' && instagramDetailedServices.tiktok) {
      availableServices = Object.values(instagramDetailedServices.tiktok).flat()
    } else if (platform === 'twitter' && instagramDetailedServices.twitter) {
      availableServices = Object.values(instagramDetailedServices.twitter).flat()
    } else if (platform === 'telegram' && instagramDetailedServices.telegram) {
      availableServices = Object.values(instagramDetailedServices.telegram).flat()
    } else if (platform === 'whatsapp' && instagramDetailedServices.whatsapp) {
      availableServices = Object.values(instagramDetailedServices.whatsapp).flat()
    } else if (platform === 'kakao' && instagramDetailedServices.kakao_naver) {
      availableServices = Object.values(instagramDetailedServices.kakao_naver).flat()
    }
    
    // 플랫폼별 서비스 이름 필터링 추가
    availableServices = availableServices.filter(service => {
      if (platform === 'youtube') {
        return service.name.includes('유튜브') || service.name.includes('YouTube')
      } else if (platform === 'facebook') {
        return service.name.includes('페이스북') || service.name.includes('Facebook')
      } else if (platform === 'threads') {
        return service.name.includes('Threads') || service.name.includes('스레드')
      } else if (platform === 'tiktok') {
        return service.name.includes('틱톡') || service.name.includes('TikTok')
      } else if (platform === 'twitter') {
        return service.name.includes('트위터') || service.name.includes('Twitter') || service.name.includes('X')
      } else if (platform === 'telegram') {
        return service.name.includes('텔레그램') || service.name.includes('Telegram')
      } else if (platform === 'whatsapp') {
        return service.name.includes('왓츠앱') || service.name.includes('WhatsApp')
      } else if (platform === 'kakao') {
        return service.name.includes('카카오') || service.name.includes('K사')
      }
      return true // 인스타그램은 모든 서비스 허용
    })
    
    return availableServices.filter(service => {
      // 서비스 타입에 따라 필터링
      if (serviceType === 'followers_korean') {
        return String(service.id).includes('followers') && service.name.includes('한국') || service.name.includes('HQ') || service.name.includes('실제')
      } else if (serviceType === 'followers_foreign') {
        return String(service.id).includes('followers') && !service.name.includes('한국')
      } else if (serviceType === 'likes_korean') {
        return String(service.id).includes('likes') && service.name.includes('한국') || service.name.includes('UHQ')
      } else if (serviceType === 'likes_foreign') {
        return String(service.id).includes('likes') && !service.name.includes('한국') && !service.name.includes('UHQ')
      } else if (serviceType === 'comments_korean') {
        return String(service.id).includes('comments') && service.name.includes('한국') && !service.name.includes('커스텀') && !service.name.includes('랜덤')
      } else if (serviceType === 'custom_comments_korean') {
        return String(service.id).includes('comments') && service.name.includes('한국') && (service.name.includes('커스텀') || service.name.includes('이모지'))
      } else if (serviceType === 'random_comments_korean') {
        return String(service.id).includes('comments') && service.name.includes('한국') && service.name.includes('랜덤')
      } else if (serviceType === 'comments_foreign') {
        return String(service.id).includes('comments') && !service.name.includes('한국') && service.name.includes('인스타그램')
      } else if (serviceType === 'comments' && platform === 'instagram') {
        return String(service.id).includes('comments')
      } else if (serviceType === 'likes' && platform === 'instagram') {
        return String(service.id).includes('likes')
      } else if (serviceType === 'followers' && platform === 'instagram') {
        return String(service.id).includes('followers')
      } else if (serviceType === 'shares' && platform === 'instagram') {
        return String(service.id).includes('shares')
      } else if (serviceType === 'views' && platform === 'instagram') {
        return String(service.id).includes('views')
      } else if (serviceType === 'views_korean') {
        return String(service.id).includes('views') && service.name.includes('한국') && service.name.includes('인스타그램')
      } else if (serviceType === 'views_foreign') {
        return String(service.id).includes('views') && !service.name.includes('한국') && service.name.includes('인스타그램')
      } else if (serviceType === 'shares_foreign') {
        return (String(service.id).includes('shares') || String(service.id).includes('saves')) && service.name.includes('인스타그램')
      } else if (serviceType === 'story_foreign') {
        return String(service.id).includes('story')
      } else if (serviceType === 'live_foreign') {
        return String(service.id).includes('live')
      } else if (serviceType === 'followers_foreign' && platform === 'threads') {
        return String(service.id).includes('followers')
      } else if (serviceType === 'likes_foreign' && platform === 'threads') {
        return String(service.id).includes('likes')
      } else if (serviceType === 'live_foreign' && platform === 'naver') {
        return String(service.id).includes('live') || String(service.id).includes('tv')
      } else if (serviceType === 'followers_korean' && platform === 'youtube') {
        return String(service.id).includes('subscribers')
      } else if (serviceType === 'page_likes_foreign' && platform === 'facebook') {
        return String(service.id).includes('page_likes')
      } else if (serviceType === 'post_likes_foreign' && platform === 'facebook') {
        return String(service.id).includes('post_likes')
      } else if (serviceType === 'video_views_foreign' && platform === 'facebook') {
        return String(service.id).includes('video_views')
      } else if (serviceType === 'comments_foreign' && platform === 'facebook') {
        return String(service.id).includes('comments')
      } else if (platform === 'recommended') {
        // 추천서비스는 각 플랫폼의 인기 서비스들을 매핑
        if (serviceType === 'instagram_followers') {
          return String(service.id).includes('followers') && (service.name.includes('인스타그램') || service.name.includes('Instagram'))
        } else if (serviceType === 'instagram_likes') {
          return String(service.id).includes('likes') && (service.name.includes('인스타그램') || service.name.includes('Instagram'))
        } else if (serviceType === 'instagram_popular') {
          return String(service.id).includes('popular') && (service.name.includes('인스타그램') || service.name.includes('Instagram'))
        } else if (serviceType === 'youtube_subscribers') {
          return String(service.id).includes('subscribers') && (service.name.includes('YouTube') || service.name.includes('유튜브'))
        } else if (serviceType === 'youtube_views') {
          return String(service.id).includes('views') && (service.name.includes('YouTube') || service.name.includes('유튜브'))
        } else if (serviceType === 'tiktok_followers') {
          return String(service.id).includes('followers') && (service.name.includes('틱톡') || service.name.includes('TikTok'))
        } else if (serviceType === 'tiktok_views') {
          return String(service.id).includes('views') && (service.name.includes('틱톡') || service.name.includes('TikTok'))
        } else if (serviceType === 'facebook_page_likes') {
          return String(service.id).includes('page_likes') && (service.name.includes('페이스북') || service.name.includes('Facebook'))
        } else if (serviceType === 'twitter_followers') {
          return String(service.id).includes('followers') && (service.name.includes('트위터') || service.name.includes('Twitter') || service.name.includes('X'))
        }
      }
      
      // 외국인 서비스들
      if (serviceType === 'foreign_package') {
        return service.id === 999
      } else if (serviceType === 'followers_foreign') {
        return service.id === 100
      } else if (serviceType === 'comments_foreign') {
        return service.id === 101
      } else if (serviceType === 'reels_views_foreign') {
        return service.id === 102
      } else if (serviceType === 'exposure_save_share_foreign') {
        return service.id === 103
      } else if (serviceType === 'live_streaming') {
        return service.id === 104
      } else if (serviceType === 'auto_likes_foreign') {
        return service.id === 105
      } else if (serviceType === 'auto_followers_foreign') {
        return service.id === 106
      } else if (serviceType === 'auto_comments_foreign') {
        return service.id === 107
      } else if (serviceType === 'auto_reels_views_foreign') {
        return service.id === 108
      } else if (serviceType === 'auto_exposure_save_share_foreign') {
        return service.id === 109
      }
      
      return false
    })
  }

  const services = getServicesForPlatform(selectedPlatform)
  const detailedServices = getDetailedServices(selectedPlatform, selectedService)

  // 플랫폼 정보 가져오기
  const getPlatformInfo = (platformId) => {
    const platform = platforms.find(p => p.id === platformId)
    return platform || { name: '알 수 없음', icon: Globe, color: '#6b7280' }
  }

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


  // 가격 계산 (SMM KINGS 가격 사용)
  useEffect(() => {
    if (!selectedPlatform || !selectedDetailedService || quantity <= 0) {
      setTotalPrice(0)
      return
    }
    
    let basePrice = 0
    
    // 패키지 상품 또는 drip-feed 상품인 경우 수량과 상관없이 고정 가격
    if (selectedDetailedService && (selectedDetailedService.package || selectedDetailedService.drip_feed)) {
      basePrice = selectedDetailedService.price / 1000  // 패키지/드립피드 전체 가격
    } else if (selectedPlatform === 'instagram' || selectedPlatform === 'threads' || selectedPlatform === 'youtube' || selectedPlatform === 'facebook' || selectedPlatform === 'naver' || selectedPlatform === 'tiktok' || selectedPlatform === 'twitter' || selectedPlatform === 'telegram' || selectedPlatform === 'whatsapp' || selectedPlatform === 'top-exposure') {
      // 일반 상품의 경우 수량에 따라 가격 계산
      basePrice = (selectedDetailedService.price / 1000) * quantity
    } else {
      // 기존 SMM KINGS 가격 사용
      basePrice = (selectedDetailedService.price / 1000) * quantity
    }
    
    // 할인 제거 - 추천인 시스템은 커미션 방식 (할인 쿠폰 아님)
    // 추천인은 피추천인 구매 금액의 10%를 커미션으로 받음 (백엔드에서 자동 처리)
    setTotalPrice(Math.round(basePrice))
  }, [selectedDetailedService, quantity, selectedPlatform])

  const handlePlatformSelect = (platformId) => {
    setSelectedPlatform(platformId)
    setSelectedServiceType('recommended')
    setSelectedDetailedService(null)
    
    // 플랫폼에 따라 기본 서비스 설정
    if (platformId === 'recommended') {
      setSelectedService('top_exposure_30days')
      setQuantity(1)
    } else if (platformId === 'event') {
      setSelectedService('instagram_korean_followers_bulk')
      setQuantity(1)
    } else if (platformId === 'top-exposure') {
      setSelectedService('top_exposure_30days')
      setQuantity(1)
    } else if (['account-management', 'package', 'other', 'threads', 'news-media', 'experience-group', 'kakao', 'store-marketing', 'app-marketing', 'seo-traffic'].includes(platformId)) {
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
    if (detailedServices && detailedServices.length > 0) {
      setSelectedDetailedService(detailedServices[0])
      // 패키지 상품 또는 drip-feed 상품은 수량을 1로 고정
      if (detailedServices[0].package || detailedServices[0].drip_feed) {
        setQuantity(1)
      } else {
        setQuantity(0)
      }
    }
  }

  const handleDetailedServiceSelect = (detailedService) => {
    setSelectedDetailedService(detailedService)
    // 패키지 상품 또는 drip-feed 상품은 수량을 1로 고정, 일반 상품은 0으로 초기화
    if (detailedService.package || detailedService.drip_feed) {
      setQuantity(1)
    } else {
      setQuantity(0)
    }
  }

  const handleQuantityChange = (newQuantity) => {
    if (selectedDetailedService) {
      const max = selectedDetailedService.max
      
      // 최대값만 체크하고, 0 이상이면 허용
      if (newQuantity >= 0 && newQuantity <= max) {
        setQuantity(newQuantity)
      }
    } else {
      setQuantity(newQuantity)
    }
  }



  const handleHelpClick = () => {
    alert('주문 방법에 대한 상세한 가이드를 확인할 수 있습니다.')
  }

  // 상품 설명 반환 함수
  const getProductDescription = (platform, service) => {
    const descriptions = {
      instagram: {
        followers_korean: {
          title: "🇰🇷 한국인 인스타그램 팔로워",
          specs: [
            "✴️ 품질: 고품질 리얼 한국인 팔로워",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "⛔ 동일한 링크로 동일한 상품군 주문시, 기존 주문이 완료되기 전 추가 주문을 넣으시면 구매 수량보다 덜 유입될 수 있습니다.",
            "✴️ 최근 인스타그램의 업데이트로 인해 특정 계정의 팔로우시 승인이 필요하게 되었습니다.",
            "✴️ 모든 팔로워는 이탈이 발생할 수 있으며, 대규모 업데이트가 있는 경우 대량 이탈이 발생할 수 있습니다.",
            "✔️ 주문후 속도를 높이거나 중도 취소/환불이 불가합니다.",
            "✔️ 계정공개 필수, 비공개 계정 작업 불가"
          ],
          settings: [
            "1. 인스타그램 설정(앱화면 오른쪽 최상단 삼선 클릭)",
            "2. 친구 팔로우 및 초대 클릭", 
            "3. 검토를 위해 플래그 지정 끄기(회색으로)"
          ]
        },
        followers_foreign: {
          title: "🌍 외국인 인스타그램 팔로워",
          specs: [
            "✴️ 품질: 고품질 리얼 외국인 팔로워",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "⛔ 동일한 링크로 동일한 상품군 주문시, 기존 주문이 완료되기 전 추가 주문을 넣으시면 구매 수량보다 덜 유입될 수 있습니다.",
            "✴️ 최근 인스타그램의 업데이트로 인해 특정 계정의 팔로우시 승인이 필요하게 되었습니다.",
            "✴️ 모든 팔로워는 이탈이 발생할 수 있으며, 대규모 업데이트가 있는 경우 대량 이탈이 발생할 수 있습니다.",
            "✔️ 주문후 속도를 높이거나 중도 취소/환불이 불가합니다.",
            "✔️ 계정공개 필수, 비공개 계정 작업 불가"
          ],
          settings: [
            "1. 인스타그램 설정(앱화면 오른쪽 최상단 삼선 클릭)",
            "2. 친구 팔로우 및 초대 클릭",
            "3. 검토를 위해 플래그 지정 끄기(회색으로)"
          ]
        },
        likes_korean: {
          title: "❤️ 한국인 인스타그램 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 한국인 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        likes_foreign: {
          title: "❤️ 외국인 인스타그램 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 외국인 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        comments_korean: {
          title: "💬 한국인 인스타그램 댓글",
          specs: [
            "✴️ 품질: 고품질 리얼 한국인 댓글",
            "✴️ 시작: 1~6시간",
            "✳️ 속도: 자연스러운 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 댓글 내용을 입력해주세요"
          ]
        },
        comments_foreign: {
          title: "💬 외국인 인스타그램 댓글",
          specs: [
            "✴️ 품질: 고품질 리얼 외국인 댓글",
            "✴️ 시작: 1~6시간",
            "✳️ 속도: 자연스러운 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 댓글 내용을 입력해주세요"
          ]
        },
        views: {
          title: "👁️ 인스타그램 조회수",
          specs: [
            "✴️ 품질: 고품질 리얼 조회수",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        story_views: {
          title: "📖 인스타그램 스토리 조회수",
          specs: [
            "✴️ 품질: 고품질 리얼 스토리 조회수",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        top_exposure_photo_ti1: {
          title: "🥇 인기게시물 상위 노출 (사진)",
          specs: [
            "✴️ 품질: 고품질 상위 노출 서비스",
            "✴️ 시작: 1~6시간",
            "✳️ 속도: 자연스러운 속도로 노출"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        top_exposure_reels_tv1: {
          title: "🥇 인기게시물 상위 노출 (릴스)",
          specs: [
            "✴️ 품질: 고품질 상위 노출 서비스",
            "✴️ 시작: 1~6시간",
            "✳️ 속도: 자연스러운 속도로 노출"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        korean_likes_powerup: {
          title: "🇰🇷 한국인 파워업 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 한국인 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        korean_likes_real: {
          title: "🇰🇷 한국인 리얼 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 한국인 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        korean_likes_man: {
          title: "👨 한국인 남성 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 한국인 남성 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        korean_likes_woman: {
          title: "👩 한국인 여성 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 한국인 여성 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        foreign_followers_30day: {
          title: "🌍 외국인 팔로워 (30일)",
          specs: [
            "✴️ 품질: 고품질 리얼 외국인 팔로워",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "⛔ 동일한 링크로 동일한 상품군 주문시, 기존 주문이 완료되기 전 추가 주문을 넣으시면 구매 수량보다 덜 유입될 수 있습니다.",
            "✴️ 최근 인스타그램의 업데이트로 인해 특정 계정의 팔로우시 승인이 필요하게 되었습니다.",
            "✴️ 모든 팔로워는 이탈이 발생할 수 있으며, 대규모 업데이트가 있는 경우 대량 이탈이 발생할 수 있습니다.",
            "✔️ 주문후 속도를 높이거나 중도 취소/환불이 불가합니다.",
            "✔️ 계정공개 필수, 비공개 계정 작업 불가"
          ],
          settings: [
            "1. 인스타그램 설정(앱화면 오른쪽 최상단 삼선 클릭)",
            "2. 친구 팔로우 및 초대 클릭",
            "3. 검토를 위해 플래그 지정 끄기(회색으로)"
          ]
        },
        followers_hq_mixed_2m: {
          title: "👥 고품질 혼합 팔로워 (200만)",
          specs: [
            "✴️ 품질: 고품질 리얼 혼합 팔로워",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "⛔ 동일한 링크로 동일한 상품군 주문시, 기존 주문이 완료되기 전 추가 주문을 넣으시면 구매 수량보다 덜 유입될 수 있습니다.",
            "✴️ 최근 인스타그램의 업데이트로 인해 특정 계정의 팔로우시 승인이 필요하게 되었습니다.",
            "✴️ 모든 팔로워는 이탈이 발생할 수 있으며, 대규모 업데이트가 있는 경우 대량 이탈이 발생할 수 있습니다.",
            "✔️ 주문후 속도를 높이거나 중도 취소/환불이 불가합니다.",
            "✔️ 계정공개 필수, 비공개 계정 작업 불가"
          ],
          settings: [
            "1. 인스타그램 설정(앱화면 오른쪽 최상단 삼선 클릭)",
            "2. 친구 팔로우 및 초대 클릭",
            "3. 검토를 위해 플래그 지정 끄기(회색으로)"
          ]
        },
        likes_real_50k: {
          title: "❤️ 리얼 좋아요 (5만)",
          specs: [
            "✴️ 품질: 고품질 리얼 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        comments_random_hq_100: {
          title: "💬 랜덤 고품질 댓글 (100개)",
          specs: [
            "✴️ 품질: 고품질 리얼 댓글",
            "✴️ 시작: 1~6시간",
            "✳️ 속도: 자연스러운 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 댓글 내용을 입력해주세요"
          ]
        },
        views_posts_3m: {
          title: "👁️ 게시물 조회수 (300만)",
          specs: [
            "✴️ 품질: 고품질 리얼 조회수",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        story_views_hq_10k: {
          title: "📖 스토리 조회수 (1만)",
          specs: [
            "✴️ 품질: 고품질 리얼 스토리 조회수",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        reels_likes_s3_200k: {
          title: "🎬 릴스 좋아요 (20만)",
          specs: [
            "✴️ 품질: 고품질 리얼 릴스 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        shares_high_speed_1m: {
          title: "📤 고속 공유 (100만)",
          specs: [
            "✴️ 품질: 고품질 리얼 공유",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        saves_real_4k: {
          title: "💾 리얼 저장 (4천)",
          specs: [
            "✴️ 품질: 고품질 리얼 저장",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        }
      },
      youtube: {
        subscribers: {
          title: "👥 유튜브 구독자",
          specs: [
            "✴️ 품질: 고품질 리얼 구독자",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "✔️ 채널공개 필수, 비공개 채널 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        views: {
          title: "👁️ 유튜브 조회수",
          specs: [
            "✴️ 품질: 고품질 리얼 조회수",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 채널공개 필수, 비공개 채널 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        likes: {
          title: "👍 유튜브 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 채널공개 필수, 비공개 채널 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        comments_korean: {
          title: "💬 한국인 유튜브 댓글",
          specs: [
            "✴️ 품질: 고품질 리얼 한국인 댓글",
            "✴️ 시작: 1~6시간",
            "✳️ 속도: 자연스러운 속도로 유입"
          ],
          warnings: [
            "✔️ 채널공개 필수, 비공개 채널 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 댓글 내용을 입력해주세요"
          ]
        }
      },
      tiktok: {
        followers: {
          title: "🎵 틱톡 팔로워",
          specs: [
            "✴️ 품질: 고품질 리얼 팔로워",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        likes: {
          title: "❤️ 틱톡 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        views: {
          title: "👁️ 틱톡 조회수",
          specs: [
            "✴️ 품질: 고품질 리얼 조회수",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        }
      },
      twitter: {
        followers: {
          title: "🐦 트위터 팔로워",
          specs: [
            "✴️ 품질: 고품질 리얼 팔로워",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        likes: {
          title: "❤️ 트위터 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        retweets: {
          title: "🔄 트위터 리트윗",
          specs: [
            "✴️ 품질: 고품질 리얼 리트윗",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        }
      },
      facebook: {
        followers: {
          title: "👥 페이스북 팔로워",
          specs: [
            "✴️ 품질: 고품질 리얼 팔로워",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        likes: {
          title: "👍 페이스북 좋아요",
          specs: [
            "✴️ 품질: 고품질 리얼 좋아요",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 계정공개 필수, 비공개 계정 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        }
      },
      telegram: {
        members: {
          title: "📢 텔레그램 멤버",
          specs: [
            "✴️ 품질: 고품질 리얼 멤버",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "✔️ 채널공개 필수, 비공개 채널 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        },
        views: {
          title: "👁️ 텔레그램 조회수",
          specs: [
            "✴️ 품질: 고품질 리얼 조회수",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 채널공개 필수, 비공개 채널 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        }
      },
      whatsapp: {
        members: {
          title: "💬 왓츠앱 멤버",
          specs: [
            "✴️ 품질: 고품질 리얼 멤버",
            "✴️ 시작: 5~24시간",
            "✳️ 속도: 100~1000명/일 (가변적)"
          ],
          warnings: [
            "✔️ 그룹공개 필수, 비공개 그룹 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        }
      },
      naver: {
        blog_views: {
          title: "📝 네이버 블로그 조회수",
          specs: [
            "✴️ 품질: 고품질 리얼 조회수",
            "✴️ 시작: 즉시~30분",
            "✳️ 속도: 빠른 속도로 유입"
          ],
          warnings: [
            "✔️ 블로그공개 필수, 비공개 블로그 작업 불가",
            "✔️ 주문접수 후 취소, 변경, 환불 불가",
            "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
          ]
        }
      }
    };

    // 기본 상품 설명 (모든 서비스에 적용)
    const defaultProduct = {
      title: `${platform === 'instagram' ? '📸 인스타그램' : platform === 'youtube' ? '📺 유튜브' : platform === 'tiktok' ? '🎵 틱톡' : platform === 'twitter' ? '🐦 트위터' : platform === 'facebook' ? '👥 페이스북' : platform === 'telegram' ? '📱 텔레그램' : platform === 'whatsapp' ? '💬 왓츠앱' : platform === 'naver' ? '🔍 네이버' : '📱'} ${service.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').trim()}`,
      specs: [
        "✴️ 품질: 고품질 리얼 서비스",
        "✴️ 시작: 즉시~30분",
        "✳️ 속도: 자연스러운 속도로 유입"
      ],
      warnings: [
        "✔️ 계정공개 필수, 비공개 계정 작업 불가",
        "✔️ 주문접수 후 취소, 변경, 환불 불가",
        "✔️ 진행 상태 정보는 정확히 일치하지 않을 수 있습니다"
      ]
    };

    const product = descriptions[platform]?.[service] || defaultProduct;
    if (!product) return null;

    return (
      <div className="product-description-detail">
        <div className="product-title">{product.title}</div>
        
        <div className="specs-section">
          <h5>📊 상품 정보</h5>
          <ul>
            {product.specs.map((spec, index) => (
              <li key={index}>{spec}</li>
            ))}
          </ul>
        </div>

        {product.settings && (
          <div className="settings-section">
            <h5>⚙️ 필수 설정</h5>
            <ul>
              {product.settings.map((setting, index) => (
                <li key={index}>{setting}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="warnings-section">
          <h5>⚠️ 주의사항</h5>
          <ul>
            {product.warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </div>

        <div className="url-info">
          <h5>📝 주문 URL 입력 방법</h5>
          <div className="url-examples">
            <p><strong>방법 1:</strong> https://www.instagram.com/인스타아이디</p>
            <p><strong>방법 2:</strong> 인스타아이디만 입력</p>
            <p><em>※ http → https, www 반드시 추가, I → i 소문자, co.kr → com</em></p>
          </div>
        </div>
      </div>
    );
  }




  const handlePurchase = async () => {
    try {
      
      // 게스트 모드인 경우 주문 불가
      if (isGuest) {
        alert('게스트 모드에서는 주문할 수 없습니다. 로그인 후 주문해주세요!')
        return
      }

      // 로그인하지 않은 경우
      if (!currentUser) {
        alert('로그인이 필요합니다.')
        return
      }

      if (!selectedDetailedService) {
        alert('세부 서비스를 선택해주세요.')
        return
      }

      if (!link || !link.trim()) {
        alert('링크를 입력해주세요!')
        return
      }

      if (!quantity || quantity === 0) {
        alert('수량을 입력해주세요.')
        return
      }
      
      if (quantity < selectedDetailedService.min) {
        alert(`수량은 최소 ${(selectedDetailedService.min || 0).toLocaleString()}개 이상이어야 합니다.`)
        return
      }

      if (((selectedPlatform === 'instagram' && (selectedService === 'comments_korean' || selectedService === 'comments_foreign')) || 
           (selectedPlatform === 'youtube' && selectedService === 'comments_korean')) && (!comments || !comments.trim())) {
        alert('댓글 내용을 입력해주세요!')
        return
      }

      // 예약 발송과 분할 발송 상호 배타적 검증
      if (isScheduledOrder && isSplitDelivery) {
        alert('예약 발송과 분할 발송은 동시에 선택할 수 없습니다.')
        return
      }

      // 분할 발송 검증
      if (isSplitDelivery) {
        if (splitDays < 0 || splitDays > 30) {
          alert('분할 기간은 0일에서 30일 사이여야 합니다.')
          return
        }
        if (splitDays === 0) {
          alert('분할 기간을 1일 이상으로 설정해주세요.')
          return
        }
        const dailyQty = getDailyQuantity()
        const minQuantity = selectedDetailedService?.min || 1
        const totalSplitQuantity = dailyQty * splitDays
        
        if (dailyQty < 1) {
          alert('일일 수량이 1개 미만입니다. 기간을 조정해주세요.')
          return
        }
        
        // 일일 수량이 상품의 최소 수량을 만족하는지 검증
        if (dailyQty < minQuantity) {
          alert(`일일 수량이 상품의 최소 수량(${minQuantity}개)보다 적습니다. 기간을 줄이거나 총 수량을 늘려주세요.`)
          return
        }
        
        // 일일 수량 × 기간이 총 수량을 초과하는지 검증
        if (totalSplitQuantity > quantity) {
          alert(`분할 발송 수량(${totalSplitQuantity}개)이 선택한 총 수량(${quantity}개)을 초과합니다. 기간을 변경해주세요.`)
          return
        }
        
        if (dailyQty > 1000) {
          alert('일일 수량이 너무 많습니다. 기간을 늘리거나 총 수량을 줄여주세요.')
          return
        }
      }

      // selectedDetailedService가 undefined인 경우 강제로 기본값 설정
      if (!selectedDetailedService || (!selectedDetailedService.id && !selectedDetailedService.smmkings_id)) {
        alert('서비스 선택에 문제가 있습니다. 페이지를 새로고침하고 다시 시도해주세요.')
        return
      }
    } catch (error) {
      alert('주문 생성 중 오류가 발생했습니다. 다시 시도해주세요.')
      return
    }

    setIsLoading(true)

    try {
      const userId = currentUser?.uid || currentUser?.email || 'anonymous'
      
      // 안전한 변수 초기화
      const safeServiceId = selectedDetailedService?.id || selectedDetailedService?.smmkings_id || 'unknown'
      const safeQuantity = quantity || 0
      const safeTotalPrice = totalPrice || 0
      const safeLink = (link || '').trim()
      const safeComments = (comments || '').trim()
      
      // Drip-feed 상품인 경우 runs와 interval 설정
      const isDripFeed = selectedDetailedService?.drip_feed === true
      const dripFeedRuns = isDripFeed ? (selectedDetailedService?.runs || 1) : 1
      const dripFeedInterval = isDripFeed ? (selectedDetailedService?.interval || 0) : 0
      const dripFeedQuantity = isDripFeed ? (selectedDetailedService?.drip_quantity || safeQuantity) : safeQuantity
      
      // Drip-feed 상품인 경우 서비스 ID와 수량 설정
      const finalServiceId = isDripFeed ? (selectedDetailedService?.smmkings_id || selectedDetailedService?.id || safeServiceId) : safeServiceId
      const finalQuantity = isDripFeed ? dripFeedQuantity : safeQuantity

      const orderData = {
        user_id: userId,
        service_id: finalServiceId,
        link: safeLink,
        quantity: finalQuantity,
        price: safeTotalPrice,
        runs: dripFeedRuns,  // Drip-feed 상품: 30일간 하루에 1번씩 → runs: 30, interval: 1440
        interval: dripFeedInterval,  // interval 단위: 분 (1440 = 24시간)
        comments: safeComments,
        username: '',
        min: 0,
        // 분할 발송 정보
        is_split_delivery: isSplitDelivery,
        split_days: isSplitDelivery ? splitDays : null,
        split_quantity: isSplitDelivery ? getDailyQuantity() : null,
        // 할인 쿠폰 제거 - 추천인 시스템은 커미션 방식
        use_coupon: false,
        coupon_id: null,
        coupon_discount: 0,
        // 패키지 상품 정보 (drip-feed가 아닌 경우만)
        package_steps: !isDripFeed && selectedDetailedService?.package && selectedDetailedService?.steps ? selectedDetailedService.steps.map(step => ({
          ...step,
          quantity: step.quantity || 0  // 각 단계별 수량 보장
        })) : [],
        max: 0,
        posts: 0,
        delay: 0,
        expiry: '',
        oldPosts: 0
      }


      // 주문 데이터 검증
      if (!orderData.user_id || orderData.user_id === 'anonymous') {
        throw new Error('사용자 ID가 유효하지 않습니다. 다시 로그인해주세요.')
      }
      
      if (!orderData.service_id || orderData.service_id === 'unknown') {
        throw new Error('서비스 ID가 유효하지 않습니다. 서비스를 다시 선택해주세요.')
      }
      
      if (!orderData.link || orderData.link.trim() === '') {
        throw new Error('링크를 입력해주세요.')
      }
      
      if (!orderData.quantity || orderData.quantity <= 0) {
        throw new Error('수량을 올바르게 입력해주세요.')
      }
      
      if (!orderData.price || orderData.price <= 0) {
        throw new Error('가격이 올바르지 않습니다.')
      }

      // 예약 발송 검증
      if (isScheduledOrder) {
        if (!scheduledDate || !scheduledTime) {
          throw new Error('예약 날짜와 시간을 모두 선택해주세요.')
        }
        
        const scheduledDateTime = new Date(`${scheduledDate} ${scheduledTime}`)
        const now = new Date()
        
        if (scheduledDateTime <= now) {
          throw new Error('예약 시간은 현재 시간보다 늦어야 합니다.')
        }
        
        // 예약 시간이 5분~7일 이내인지 확인
        const timeDiff = scheduledDateTime.getTime() - now.getTime()
        const minutesDiff = timeDiff / (1000 * 60) // 분 단위로 계산
        
        if (minutesDiff < 5) {
          throw new Error('예약 시간은 최소 5분 후여야 합니다.')
        }
        
        if (minutesDiff > 10080) { // 7일 = 7 * 24 * 60 = 10080분
          throw new Error('예약 시간은 최대 7일 이내여야 합니다.')
        }
      }

      
      // 예약 발송 데이터 추가
      if (isScheduledOrder) {
        orderData.is_scheduled = true
        orderData.scheduled_datetime = `${scheduledDate} ${scheduledTime}`
        console.log('📅 예약 발송 데이터:', {
          is_scheduled: orderData.is_scheduled,
          scheduled_datetime: orderData.scheduled_datetime
        })
        }

        // 주문 데이터에 서비스 이름 추가
        const orderDataWithService = {
          ...orderData,
          service_name: selectedDetailedService?.name || '선택된 서비스',
          unit_price: selectedDetailedService?.price || 0,
          total_price: safeTotalPrice
        }

      // 사용자 포인트 조회
      let userPoints = null
      try {
        const pointsResponse = await fetch(`/api/points?user_id=${userId}`)
        if (pointsResponse.ok) {
          userPoints = await pointsResponse.json()
        }
      } catch (error) {
        // 포인트 조회 실패해도 계속 진행
      }

      // 결제 페이지로 이동 (주문 생성 없이)
        navigate(`/payment/${selectedPlatform}`, { 
          state: { 
            orderData: {
              ...orderDataWithService,
              userId: userId,
              platform: selectedPlatform,
              service: selectedService,
              detailedService: selectedDetailedService,
              quantity: safeQuantity,
              unitPrice: selectedDetailedService?.price || 0,
              totalPrice: safeTotalPrice,
              link: safeLink,
              comments: safeComments,
            explanation: explanation || '',
            discount: 0, // 할인 쿠폰 제거 - 추천인 시스템은 커미션 방식
            userPoints: userPoints,
            isScheduledOrder: isScheduledOrder,
            scheduledDate: scheduledDate,
            scheduledTime: scheduledTime,
            isSplitDelivery: isSplitDelivery,
            splitDays: splitDays,
            dailyQuantity: isSplitDelivery ? getDailyQuantity() : null
          }
        }
      })
    } catch (error) {
      alert(`주문 데이터 준비 실패: ${error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddToCart = async () => {
    if (isGuest) {
      alert('게스트 모드에서는 장바구니에 추가할 수 없습니다. 로그인 후 이용해주세요!')
      return
    }

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
      alert('장바구니 추가 실패')
    }
  }

  return (
    <div className="order-page">
      {/* Service Selection */}
      <div className="service-selection">
        <div className="service-header">
          <div className="header-title">
        <h2>주문하기</h2>
        <p>원하는 서비스를 선택하고 주문해보세요!</p>
          </div>
          <button 
            className="order-method-btn"
            onClick={() => setShowOrderMethodModal(true)}
          >
            📋 주문방법
          </button>
        </div>
        
        <div className="platform-grid">
          {platforms.map(({ id, name, icon, color, description }) => (
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
              {typeof icon === 'string' ? (
                <img src={icon} alt={name} className="platform-icon" style={{ width: 32, height: 32 }} />
              ) : (
                <icon size={32} className="platform-icon" />
              )}
              <div className="platform-name">{name}</div>
              <div className="platform-description">{description}</div>
        </div>
          ))}
        </div>
          </div>
      
      {/* Service Type Selection */}
      <div className="service-type-selection">
        
        {/* Service Selection */}
        <div className="service-category">
          <h3 className="category-title">
            {platforms.find(p => p.id === selectedPlatform)?.name} 서비스
          </h3>
          <p className="category-description">상세 서비스를 선택해주세요</p>
          
          {/* Tab Navigation - 특정 플랫폼에서는 숨김 */}
          {!['tiktok', 'threads', 'twitter', 'kakao', 'telegram', 'whatsapp', 'recommended', 'event', 'top-exposure'].includes(selectedPlatform) && (
            <div className="service-tabs">
              <button 
                className={`tab-button ${selectedTab === 'korean' ? 'active' : ''}`}
                onClick={() => setSelectedTab('korean')}
              >
                <img src="https://upload.wikimedia.org/wikipedia/commons/0/09/Flag_of_South_Korea.svg" alt="태극기" style={{ width: 20, height: 20 }} />
                한국인
              </button>
              <button 
                className={`tab-button ${selectedTab === 'foreign' ? 'active' : ''}`}
                onClick={() => setSelectedTab('foreign')}
              >
                <Globe size={20} />
                외국인
              </button>
            </div>
          )}

          {/* Premium Quality Banner */}
          <div className="premium-banner">
            <div className="banner-content">
              <span>선택서비스 소셜리티 퀄리티 확인</span>
              <ChevronRight size={20} />
            </div>
          </div>

          <div className="service-list">
            {services
              .filter(service => {
                // 빈 서비스는 외국인 탭에서만 표시
                if (service.id === 'empty_service' || service.id === 'empty_service_foreign') {
                  return selectedTab === 'foreign'
                }
                
                // 유튜브 한국인 빈 서비스는 한국인 탭에서만 표시
                if (service.id === 'empty_service_korean') {
                  return selectedTab === 'korean'
                }
                
                // 특정 플랫폼들은 탭 구분 없이 모든 서비스 표시
                if (['tiktok', 'threads', 'twitter', 'kakao', 'telegram', 'whatsapp', 'recommended', 'event', 'top-exposure'].includes(selectedPlatform)) {
                  return true
                }
                
                // 한국인/외국인 탭에 따라 필터링
                if (selectedTab === 'korean') {
                  return String(service.id).includes('korean') || 
                         service.id === 'popular_posts' || 
                         service.id === 'views' || 
                         service.id === 'exposure_save_share' || 
                         service.id === 'auto_exposure_save_share' ||
                         service.id === 'n_k_services' ||
                         service.id === 'auto_likes' ||
                         service.id === 'auto_comments' ||
                         service.id === 'auto_followers' ||
                         service.id === 'auto_regram'
                } else if (selectedTab === 'foreign') {
                  return String(service.id).includes('foreign') || 
                         service.id === 'live_streaming' ||
                         service.id === 'auto_likes_foreign' ||
                         service.id === 'auto_views_foreign' || 
                         service.id === 'auto_comments_foreign' ||
                         service.id === 'auto_followers_foreign' ||
                         service.id === 'auto_regram_foreign' ||
                         service.id === 'auto_reels_views_foreign' ||
                         service.id === 'auto_exposure_save_share_foreign'
                }
                return true
              })
              .map(({ id, name, badge, featured, special }) => {
                // 서비스별 배지 매핑
                const getServiceBadge = (serviceId) => {
                  if (serviceId.includes('auto_')) {
                    return <span className="service-badge auto">자동</span>
                  }
                  if (serviceId === 'popular_posts') {
                    return <span className="service-badge new">B</span>
                  }
                  return null
                }

                return (
              <div 
                key={id} 
                className={`service-item ${special ? 'special' : ''} ${featured ? 'featured' : ''} ${selectedService === id ? 'selected' : ''}`}
                onClick={() => handleServiceSelect(id)}
              >
                <div className="service-content">
                      <div className="service-title-row">
                        {getServiceBadge(id)}
                        {badge && <span className="service-badge custom">{badge}</span>}
                  <span className="service-name">{name}</span>
                      </div>
                  {featured && <Star size={16} className="featured-icon" />}
                  {special && (
                    <div className="special-indicator">
                      <Sparkles size={16} />
                      <Sparkles size={16} />
      </div>
                  )}
                </div>
              </div>
                )
              })}
          </div>
        </div>
      </div>
      
      {/* Detailed Service Selection */}
      {selectedService && detailedServices.length > 0 && (
        <div className="detailed-service-selection">
          <h3>
            
            세부 서비스를 선택해주세요
          </h3>
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
                    <div className="detailed-service-range">
                      최소: {(service.min || 0).toLocaleString()} ~ 최대: {(service.max || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="detailed-service-price">
                    {(() => {
                      const price = service.price / 1000;
                      const formattedPrice = price % 1 === 0 ? price.toString() : price.toFixed(2);
                      return (selectedPlatform === 'instagram' || selectedPlatform === 'threads' || selectedPlatform === 'youtube' || selectedPlatform === 'facebook' || selectedPlatform === 'naver' || selectedPlatform === 'tiktok' || selectedPlatform === 'twitter' || selectedPlatform === 'telegram' || selectedPlatform === 'whatsapp' || selectedPlatform === 'top-exposure') ? 
                        `₩${formattedPrice}` : 
                        `${formattedPrice}원`
                    })()}
                  </div>
                </div>
                </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Order Form */}
      {selectedDetailedService && (
        <div className="order-form">
          <div className="order-info-header">
            <h3>주문 정보 입력</h3>
          </div>
          
          {/* 상품 설명 */}
          <div className="product-description">
            <div 
              className="description-header" 
              onClick={() => setIsDescriptionExpanded(!isDescriptionExpanded)}
              style={{ cursor: 'pointer' }}
            >
              <h4>📋 상품 설명</h4>
              <span className="toggle-icon">{isDescriptionExpanded ? '▲' : '▼'}</span>
            </div>
            {isDescriptionExpanded && (
              <div className="description-content">
                {getProductDescription(selectedPlatform, selectedService)}
              </div>
            )}
          </div>
          
          {/* Quantity Selection - 패키지 상품 또는 drip-feed 상품이 아닐 때만 표시 */}
          {selectedDetailedService && !selectedDetailedService.package && !selectedDetailedService.drip_feed && (
          <div className="form-group">
              <label className="quantity-label">수량 선택</label>
            <input
              type="number"
                value={quantity === 0 ? '' : quantity}
              onChange={(e) => {
                  const inputValue = e.target.value
                  if (inputValue === '') {
                    handleQuantityChange(0)
                  } else {
                    const newQuantity = parseInt(inputValue)
                    if (!isNaN(newQuantity)) {
                  handleQuantityChange(newQuantity)
                    }
                }
              }}
                min="0"
              max={selectedDetailedService.max}
                className={`quantity-input-field ${quantity > 0 && quantity < selectedDetailedService.min ? 'quantity-input-invalid' : ''}`}
                placeholder="수량을 입력하세요 (0부터 시작)"
            />
              <div className="quantity-hint-left">
                최소 {(selectedDetailedService.min || 0).toLocaleString()} : 최대 {(selectedDetailedService.max || 0).toLocaleString()}
            </div>
          </div>
          )}


          <div className="form-group">
            <label>링크 입력</label>
            <input
              type="url"
              value={link}
              onChange={(e) => setLink(e.target.value)}
              placeholder={`${platformInfo.name} 게시물 URL 또는 사용자명을 입력하세요`}
              className="form-control link-input-field"
            />
          </div>

          {selectedDetailedService && selectedDetailedService.package && selectedDetailedService.steps && 
           (selectedDetailedService.id === 1003 || selectedDetailedService.id === 1004 || selectedDetailedService.id === 1002) && (
            <div className="package-steps">
              <h3>📦 패키지 구성</h3>
              <div className="steps-container">
                {selectedDetailedService.steps.map((step, index) => (
                  <div key={step.id} className="package-step">
                    <div className="step-header">
                      <span className="step-number">{index + 1}</span>
                      <span className="step-name">{step.name}</span>
                    </div>
                    <div className="step-details">
                      <p className="step-description">{step.description}</p>
                      <p className="step-quantity">수량: {(step.quantity || 0).toLocaleString()}개</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="package-total">
                <strong>총 패키지 가격: {(() => {
                  const price = selectedDetailedService.price / 1000;
                  const formattedPrice = price % 1 === 0 ? price.toString() : price.toFixed(2);
                  return `${formattedPrice}원`;
                })()}</strong>
              </div>
            </div>
          )}

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
              <div className="char-count">{(comments || '').length}/200</div>
            </div>
          )}

          {/* 예약 발송 체크박스 - 숨김 처리 */}
          {false && (
          <div className="scheduled-order-section">
            <div className="scheduled-order-checkbox">
              <input
                type="checkbox"
                id="scheduledOrder"
                checked={isScheduledOrder}
                onChange={(e) => handleScheduledOrderChange(e.target.checked)}
                className="scheduled-checkbox"
              />
              <label htmlFor="scheduledOrder" className="scheduled-label">
                📅 예약 발송
              </label>
            </div>

            {/* 예약 발송 날짜/시간 선택 */}
            {isScheduledOrder && (
              <div className="scheduled-order-details">
                <div className="scheduled-inputs">
                  <input
                    type="date"
                    value={scheduledDate}
                    onChange={(e) => setScheduledDate(e.target.value)}
                    min={new Date().toISOString().split('T')[0]}
                    className="scheduled-date-input"
                    placeholder="날짜"
                  />
                  <input
                    type="time"
                    value={scheduledTime}
                    onChange={(e) => setScheduledTime(e.target.value)}
                    className="scheduled-time-input"
                    placeholder="시간"
                  />
                </div>
                <div className="scheduled-info">
                  <span>⏰ {scheduledDate && scheduledTime ? `${scheduledDate} ${scheduledTime}` : '날짜와 시간을 선택해주세요'}</span>
                </div>
              </div>
            )}
          </div>
          )}

          {/* 분할 발송 체크박스 - 숨김 처리 */}
          {false && (
          <div className="split-delivery-section">
            <div className="split-delivery-checkbox">
              <input
                type="checkbox"
                id="splitDelivery"
                checked={isSplitDelivery}
                onChange={(e) => handleSplitDeliveryChange(e.target.checked)}
                className="split-checkbox"
              />
              <label htmlFor="splitDelivery" className="split-label">
                📦 분할 발송
              </label>
            </div>

            {/* 분할 발송 설정 */}
            {isSplitDelivery && (
              <div className="split-delivery-details">
                <div className="split-inputs">
                  <div className="split-input-group">
                    <label className="split-input-label">분할 기간 (일)</label>
                    <input
                      type="number"
                      value={splitDays}
                      onChange={(e) => setSplitDays(Math.max(0, parseInt(e.target.value) || 0))}
                      min="0"
                      max="30"
                      className="split-days-input"
                      placeholder="예: 7"
                    />
                    <div className="split-input-help">
                      총 수량을 몇 일에 나누어 발송할지 입력하세요
                      <br />
                      <span className="min-quantity-info">
                        (최소 수량: {selectedDetailedService?.min || 1}개/일)
                      </span>
                      {isSplitDelivery && !isSplitDeliveryValid() && (
                        <>
                          <br />
                          <span className="warning-text">
                            ⚠️ 기간을 조정하여 총 수량을 초과하지 않도록 해주세요
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="split-input-group">
                    <label className="split-input-label">일일 수량 (자동계산)</label>
                    <input
                      type="number"
                      value={getDailyQuantity()}
                      disabled
                      className="split-quantity-input disabled"
                      placeholder="자동계산"
                    />
                    <div className="split-input-help">총 수량 ÷ 기간 = 일일 수량</div>
                  </div>
                </div>
                <div className={`split-info ${!isSplitDeliveryValid() ? 'warning' : ''}`}>
                  <span>📊 {getSplitInfo()}</span>
                </div>
              </div>
            )}
          </div>
          )}

          {/* Total Price */}
          <div className="price-display">
            <div className="total-price">{(() => {
              const formattedPrice = totalPrice % 1 === 0 ? totalPrice.toString() : totalPrice.toFixed(2);
              return `${formattedPrice}원`;
            })()}</div>
            <div className="price-label">총 금액</div>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            {isGuest ? (
              <button 
                className="login-required-btn" 
                onClick={() => setShowAuthModal(true)}
                disabled={isLoading}
              >
                로그인하여 주문하기
              </button>
            ) : (
            <button className="submit-btn" onClick={handlePurchase} disabled={isLoading}>
              {isLoading ? '처리 중...' : '구매하기'}
            </button>
            )}
          </div>
        </div>
      )}

    </div>
  )
}

export default Home
