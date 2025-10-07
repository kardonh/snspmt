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
import '../components/NoticePopup.css'

const Home = () => {
  const { currentUser, setShowAuthModal } = useAuth()
  const { isGuest } = useGuest()
  const navigate = useNavigate()

  const [selectedPlatform, setSelectedPlatform] = useState('instagram')
  const [selectedServiceType, setSelectedServiceType] = useState('recommended')
  const [selectedService, setSelectedService] = useState('followers_korean')
  const [selectedDetailedService, setSelectedDetailedService] = useState(null)
  const [selectedTab, setSelectedTab] = useState('korean') // 'korean' or 'foreign'
  const [quantity, setQuantity] = useState(200)
  const [totalPrice, setTotalPrice] = useState(0)
  const [showChecklist, setShowChecklist] = useState(false)
  const [link, setLink] = useState('')
  const [comments, setComments] = useState('')
  const [explanation, setExplanation] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showOrderMethodModal, setShowOrderMethodModal] = useState(false)

  
  // 할인 쿠폰 관련 상태
  const [selectedDiscountCoupon, setSelectedDiscountCoupon] = useState(null)
  const [availableDiscountCoupons, setAvailableDiscountCoupons] = useState([])
  
  // SMM Panel 유효 서비스 ID 목록
  const [validServiceIds, setValidServiceIds] = useState([])
  const [isLoadingServices, setIsLoadingServices] = useState(false)
  
  // 공지사항 팝업 관련 상태
  const [notices, setNotices] = useState([])
  const [showNoticePopup, setShowNoticePopup] = useState(false)
  const [currentNoticeIndex, setCurrentNoticeIndex] = useState(0)
  
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
      const response = await fetch('/api/smm-panel/services')
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

  // 공지사항 로드
  const loadNotices = async () => {
    try {
      const response = await fetch('/api/notices/active')
      if (response.ok) {
        const data = await response.json()
        setNotices(data.notices || [])
        
        // 오늘 하루 보지 않기 체크
        const today = new Date().toDateString()
        const dismissedNotices = JSON.parse(localStorage.getItem('dismissedNotices') || '{}')
        
        // 오늘 보지 않은 공지사항이 있고, 활성 공지사항이 있으면 팝업 표시
        if (data.notices && data.notices.length > 0 && dismissedNotices[today] !== true) {
          setShowNoticePopup(true)
        }
      }
    } catch (error) {
      // 공지사항 로드 실패 시 무시
    }
  }

  // 오늘 하루 보지 않기
  const handleDismissToday = () => {
    const today = new Date().toDateString()
    const dismissedNotices = JSON.parse(localStorage.getItem('dismissedNotices') || '{}')
    dismissedNotices[today] = true
    localStorage.setItem('dismissedNotices', JSON.stringify(dismissedNotices))
    setShowNoticePopup(false)
  }

  // 공지사항 닫기
  const handleCloseNotice = () => {
    setShowNoticePopup(false)
  }

  // 다음 공지사항 보기
  const handleNextNotice = () => {
    if (currentNoticeIndex < notices.length - 1) {
      setCurrentNoticeIndex(currentNoticeIndex + 1)
    } else {
      setShowNoticePopup(false)
    }
  }

  // 컴포넌트 마운트 시 기본 서비스 자동 선택 및 SMM 서비스 목록 로드
  useEffect(() => {
    loadSMMServices()
    loadNotices()
    
    if (selectedPlatform && selectedService && !selectedDetailedService) {
      const detailedServices = getDetailedServices(selectedPlatform, selectedService)
      if (detailedServices && detailedServices.length > 0) {
        setSelectedDetailedService(detailedServices[0])
        // 패키지 상품은 수량을 1로 고정
        if (detailedServices[0].package) {
          setQuantity(1)
        } else {
        setQuantity(detailedServices[0].min)
        }
      }
    }
  }, [selectedPlatform, selectedService, selectedDetailedService])

  // 할인 쿠폰 초기화 - 백엔드에서 실제 쿠폰 조회
  useEffect(() => {
    const loadUserCoupons = async () => {
      if (!currentUser?.uid) {
        // 로그인하지 않은 경우 기본 쿠폰만 표시
        setAvailableDiscountCoupons([
          { id: 'no_discount', name: '할인 없음', discount: 0, type: 'none' }
        ])
        return
      }
      
      try {
        // 백엔드에서 사용자의 사용 가능한 쿠폰 조회
        const response = await fetch(`/api/user/coupons?user_id=${currentUser.uid}`)
        if (response.ok) {
          const data = await response.json()
          const usableCoupons = data.coupons.filter(coupon => 
            !coupon.is_used && new Date(coupon.expires_at) > new Date()
          )
          
          if (usableCoupons.length > 0) {
            // 백엔드에서 가져온 쿠폰 + 할인 없음 옵션
            const couponOptions = [
              ...usableCoupons.map(coupon => ({
                id: coupon.id,
                name: `추천인 ${coupon.discount_value}% 할인 쿠폰`,
                discount: coupon.discount_value,
                type: coupon.discount_type,
                referralCode: coupon.referral_code
              })),
              { id: 'no_discount', name: '할인 없음', discount: 0, type: 'none' }
            ]
            setAvailableDiscountCoupons(couponOptions)
            // 기본으로 첫 번째 쿠폰 선택
            setSelectedDiscountCoupon(couponOptions[0])
          } else {
            // 사용 가능한 쿠폰이 없는 경우
            setAvailableDiscountCoupons([
              { id: 'no_discount', name: '할인 없음', discount: 0, type: 'none' }
            ])
          }
        } else {
          // API 오류 시 기본 쿠폰만 표시
          setAvailableDiscountCoupons([
            { id: 'no_discount', name: '할인 없음', discount: 0, type: 'none' }
          ])
        }
      } catch (error) {
        // 오류 발생 시 기본 쿠폰만 표시
        setAvailableDiscountCoupons([
          { id: 'no_discount', name: '할인 없음', discount: 0, type: 'none' }
        ])
      }
    }
    
    loadUserCoupons()
  }, [currentUser])

  // 인스타그램 세부 서비스 데이터
  const instagramDetailedServices = {
    popular_posts: [
      // 기존 서비스들
      { id: 361, name: '🥇인기게시물 상위 노출[🎨사진] TI1', price: 3000000, min: 1, max: 10, time: '6 시간 10 분' },
      { id: 444, name: '🥇인기게시물 상위 노출 유지[🎨사진] TI1-1', price: 90000, min: 100, max: 3000, time: '데이터가 충분하지 않습니다' },
      { id: 435, name: '🥇인기게시물 상위 노출[🎬릴스] TV1', price: 12000000, min: 1, max: 10, time: '23 시간 32 분' },
      { id: 443, name: '🥇인기게시물 상위 노출[🎨사진] TI2', price: 27000, min: 100, max: 500, time: '16 분' },
      { id: 445, name: '🥇인기게시물 상위 노출 유지[🎨사진] TI2-1', price: 90000, min: 100, max: 3000, time: '데이터가 충분하지 않습니다' },
      { id: 332, name: '0️⃣.[준비단계]:최적화 계정 준비', price: 0, min: 1, max: 1, time: '데이터가 충분하지 않습니다' },
      { id: 325, name: '1️⃣.[상승단계]:리얼 한국인 좋아요 유입', price: 19500, min: 100, max: 10000, time: '데이터가 충분하지 않습니다' },
      { id: 326, name: '2️⃣.[상승단계]:리얼 한국인 댓글 유입', price: 225000, min: 10, max: 300, time: '데이터가 충분하지 않습니다' },
      { id: 327, name: '3️⃣.[상승단계]:파워 외국인 좋아요 유입', price: 1800, min: 100, max: 200000, time: '데이터가 충분하지 않습니다' },
      { id: 328, name: '4️⃣.[등록단계]:파워 게시물 저장 유입', price: 315, min: 100, max: 1000000, time: '1 시간 52 분' },
      { id: 329, name: '5️⃣.[등록단계]:파워 게시물 노출 + 도달 + 홈 유입', price: 450, min: 1000, max: 1000000, time: '데이터가 충분하지 않습니다' },
      { id: 330, name: '6️⃣.[유지단계]:파워 게시물 저장 [✔연속 유입] 작업', price: 300, min: 100, max: 1000000, time: '7 시간 5 분' },
      { id: 331, name: '7️⃣.[유지단계]:게시물 노출+도달+홈 [✔연속 유입] 작업', price: 450, min: 100, max: 1000000, time: '데이터가 충분하지 않습니다' }
    ],
    
    // 한국인 패키지 서비스
    korean_package: [
      // 🎯 추천탭 상위노출 (내계정) - 진입단계
      { id: 1003, name: '🎯 추천탭 상위노출 (내계정) - 진입단계 [3단계 패키지]', price: 20000000, min: 1, max: 1, time: '24-48시간', description: '진입단계 3단계 완전 패키지', package: true, steps: [
        { id: 122, name: '1단계: 실제 한국인 게시물 좋아요 [진입 단계]', quantity: 300, delay: 0, description: '🇰🇷 인스타그램 한국인 💎💎파워업 좋아요💖💖[💪인.게 최적화↑]' },
        { id: 329, name: '2단계: 파워 게시물 노출 + 도달 + 기타 유입', quantity: 3000, delay: 10, description: '5️⃣:[등록단계]파워게시물 노출 + 도달 + 홈 유입' },
        { id: 328, name: '3단계: 파워 게시물 저장 유입', quantity: 1000, delay: 10, description: '4️⃣[등록단계]파워 게시물 저장 유입' }
      ]},
      
      // 🎯 추천탭 상위노출 (내계정) - 유지단계
      { id: 1004, name: '🎯 추천탭 상위노출 (내계정) - 유지단계 [2단계 패키지]', price: 15000000, min: 1, max: 1, time: '12-24시간', description: '유지단계 2단계 완전 패키지', package: true, steps: [
        { id: 325, name: '1단계: 실제 한국인 게시물 좋아요 [진입 단계]', quantity: 250, delay: 0, description: '[상승단계]:리얼 한국인 좋아요' },
        { id: 331, name: '2단계: 게시물 노출+도달+홈 [✔연속 유입]', quantity: 3000, delay: 10, description: '[유지단계]:게시물 노출+도달+홈 [✔연속 유입] 작업' }
      ]}
    ],
    
    // 커스텀/이모지 댓글 서비스
    custom_comments_korean: [
      { id: 339, name: 'KR 인스타그램 한국인 커스텀 댓글', price: 400000, min: 5, max: 500, time: '6분', description: '상세정보' },
      { id: 340, name: 'KR 인스타그램 한국인 커스텀 댓글 [여자]', price: 500000, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
      { id: 341, name: 'KR 인스타그램 한국인 커스텀 댓글 [남자]', price: 500000, min: 5, max: 500, time: '6분', description: '상세정보' },
      { id: 291, name: 'KR 인스타그램 한국인 이모지 댓글', price: 260000, min: 5, max: 1000, time: '데이터 부족', description: '상세정보' }
    ],
    
    // 릴스 조회수 서비스
    reels_views_korean: [
      { id: 111, name: 'KR 인스타그램 리얼 한국인 동영상 조회수', price: 2000, min: 100, max: 2147483647, time: '20시간 33분', description: '상세정보' }
    ],
    
    // 자동 팔로워 서비스
    auto_followers: [
      { id: 369, name: 'KR 인스타그램 한국인 💎 슈퍼프리미엄 자동 좋아요', price: 30000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
    ],
    
    // 자동 리그램 서비스
    auto_regram: [
      { id: 305, name: 'KR 인스타그램 한국인 리그램', price: 450000, min: 3, max: 3000, time: '6시간 12분', description: '상세정보' }
    ],
    
    
    likes_korean: [
      { id: 122, name: 'KR 인스타그램 한국인 ❤️ 파워업 좋아요', price: 19000, min: 30, max: 2500, time: '14시간 54분', description: '상세정보' },
      { id: 333, name: 'KR 인스타그램 한국인 ❤️ 슈퍼프리미엄 좋아요', price: 29000, min: 100, max: 1000, time: '데이터 부족', description: '상세정보' },
      { id: 276, name: 'KR 인스타그램 리얼 한국인 [여자] 좋아요', price: 29000, min: 30, max: 5000, time: '9분', description: '상세정보' },
      { id: 275, name: 'KR 인스타그램 리얼 한국인 [남자] 좋아요', price: 29000, min: 30, max: 5000, time: '10분', description: '상세정보' },
      { id: 277, name: 'KR 인스타그램 리얼 한국인 [20대] 좋아요', price: 29000, min: 30, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 280, name: 'KR 인스타그램 리얼 한국인 [20대여자] 좋아요', price: 39000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 279, name: 'KR 인스타그램 리얼 한국인 [20대남자] 좋아요', price: 39000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 278, name: 'KR 인스타그램 리얼 한국인 [30대] 좋아요', price: 29000, min: 30, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 282, name: 'KR 인스타그램 리얼 한국인 [30대여자] 좋아요', price: 39000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 281, name: 'KR 인스타그램 리얼 한국인 [30대남자] 좋아요', price: 39000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' }
    ],
    followers_korean: [
      { id: 491, name: 'KR 인스타그램 💯 리얼 한국인 팔로워 [일반]', price: 180000, min: 10, max: 1000, time: '2시간 16분', description: '상세정보' },
      { id: 491, name: 'KR 인스타그램 💯 리얼 한국인 팔로워 [디럭스]', price: 210000, min: 10, max: 1000, time: '데이터 부족', description: '상세정보' },
      { id: 334, name: 'KR 인스타그램 💯 리얼 한국인 팔로워 [프리미엄]', price: 270000, min: 10, max: 40000, time: '1시간 3분', description: '상세정보' }
    ],
    views: [
      { id: 111, name: 'KR 인스타그램 리얼 한국인 동영상 조회수', price: 2000, min: 100, max: 2147483647, time: '20시간 33분', description: '상세정보' },
      { id: 109, name: '인스타그램 동영상 조회수 [REEL/IGTV/VIDEO 가능]', price: 300, min: 100, max: 1000000, time: '데이터 부족' },
      { id: 382, name: '인스타그램 동영상 조회수+저장+시간', price: 1200, min: 100, max: 1000000, time: '데이터 부족' },
      { id: 515, name: '인스타그램 프로필 방문', price: 1000, min: 10, max: 10000, time: '데이터 부족' },
      { id: 374, name: 'KR 인스타그램 한국인 노출 [+도달+기타]', price: 8000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
      { id: 141, name: 'KR 인스타그램 리얼 한국인 저장', price: 40000, min: 10, max: 1000000, time: '2분', description: '상세정보' },
      { id: 305, name: 'KR 인스타그램 한국인 리그램', price: 450000, min: 3, max: 3000, time: '6시간 12분', description: '상세정보' }
    ],
    comments_korean: [
      { id: 342, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글', price: 260000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 297, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [여자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 296, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [남자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 298, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [20대]', price: 260000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 299, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [20대여자]', price: 400000, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 300, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [20대남자]', price: 400000, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 301, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [30대]', price: 260000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 302, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [30대여자]', price: 400000, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 303, name: 'KR 인스타그램 리얼 한국인 랜덤 댓글 [30대남자]', price: 400000, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 291, name: 'KR 인스타그램 한국인 이모지 댓글', price: 260000, min: 5, max: 1000, time: '데이터 부족', description: '상세정보' },
      { id: 339, name: 'KR 인스타그램 한국인 커스텀 댓글', price: 400000, min: 5, max: 500, time: '6분', description: '상세정보' },
      { id: 340, name: 'KR 인스타그램 한국인 커스텀 댓글 [여자]', price: 500000, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
      { id: 341, name: 'KR 인스타그램 한국인 커스텀 댓글 [남자]', price: 500000, min: 5, max: 500, time: '6분', description: '상세정보' }
    ],
    regram_korean: [
      { id: 305, name: '🇰🇷 인스타그램 한국인 리그램🎯', price: 375000, min: 3, max: 3000, time: '7 시간 21 분' }
    ],
    exposure_save_share: [
      { id: 142, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 2500, min: 100, max: 1000000, time: '데이터 부족' },
      { id: 145, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 5000, min: 100, max: 1000000, time: '데이터 부족' },
      { id: 312, name: '인스타그램 저장', price: 500, min: 10, max: 10000, time: '데이터 부족' },
      { id: 313, name: '인스타그램 공유', price: 8000, min: 10, max: 10000, time: '데이터 부족' }
    ],

    auto_likes: [
      { id: 348, name: 'KR 인스타그램 한국인 ❤️ 파워업 좋아요', price: 19000, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 369, name: 'KR 인스타그램 한국인 💎 슈퍼프리미엄 자동 좋아요', price: 30000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
    ],
    auto_views: [
      { id: 349, name: '인스타그램 동영상 자동 조회수', price: 6000, min: 100, max: 2147483647, time: '데이터 부족', description: '상세정보' }
    ],
    auto_comments: [
      { id: 350, name: 'KR 인스타그램 한국인 자동 랜덤 댓글', price: 260000, min: 3, max: 100, time: '10분', description: '상세정보' }
    ],

    // 스레드 세부 서비스 데이터
    threads: {
      likes_korean: [
        { id: 453, name: 'KR Threads 한국인 리얼 좋아요', price: 22000, min: 50, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 454, name: 'KR Threads 한국인 리얼 팔로워', price: 95000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 457, name: 'KR Threads 한국인 리얼 댓글', price: 270000, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
        { id: 498, name: 'KR Threads 한국인 리얼 공유', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 인스타그램 외국인 서비스 데이터
    foreign_package: [
      
    ],
    followers_foreign: [
      { id: 475, name: '인스타그램 외국인 팔로워', price: 10000, min: 100, max: 10000, time: '데이터 부족', description: '외국인 팔로워 서비스' }
    ],
    likes_foreign: [
      { id: 105, name: '인스타그램 외국인 좋아요', price: 4000, min: 50, max: 10000, time: '데이터 부족', description: '외국인 좋아요 서비스' },
      { id: 116, name: '인스타그램 리얼 외국인 좋아요', price: 6000, min: 50, max: 10000, time: '데이터 부족', description: '리얼 외국인 좋아요 서비스' }
    ],
    comments_foreign: [
      { id: 480, name: '인스타그램 외국인 랜덤 댓글', price: 50000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 랜덤 댓글 서비스' },
      { id: 481, name: '인스타그램 외국인 커스텀 댓글', price: 60000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 커스텀 댓글 서비스' },
      { id: 358, name: '인스타그램 외국인 랜덤 이모지 댓글', price: 50000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 랜덤 이모지 댓글 서비스' }
    ],
    reels_views_foreign: [
      { id: 109, name: '인스타그램 동영상 조회수 [REEL/IGTV/VIDEO 가능]', price: 300, min: 100, max: 1000000, time: '데이터 부족', description: '동영상 조회수 서비스' },
      { id: 382, name: '인스타그램 동영상 조회수+저장+시간', price: 1200, min: 100, max: 1000000, time: '데이터 부족', description: '동영상 조회수+저장+시간 서비스' }
    ],
    exposure_save_share_foreign: [
      { id: 515, name: '인스타그램 프로필 방문', price: 1000, min: 10, max: 10000, time: '데이터 부족', description: '프로필 방문 서비스' },
      { id: 142, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 2500, min: 100, max: 1000000, time: '데이터 부족', description: '노출+도달+추+프로필+기타 서비스' },
      { id: 145, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 5000, min: 100, max: 1000000, time: '데이터 부족', description: '노출+도달+추+프로필+기타 서비스' },
      { id: 312, name: '인스타그램 저장', price: 500, min: 10, max: 10000, time: '데이터 부족', description: '저장 서비스' },
      { id: 313, name: '인스타그램 공유', price: 8000, min: 10, max: 10000, time: '데이터 부족', description: '공유 서비스' }
      ],
      live_streaming: [
      { id: 393, name: '인스타그램 실시간 라이브 스트리밍 시청 [15분]', price: 3000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 394, name: '인스타그램 실시간 라이브 스트리밍 시청 [30분]', price: 6000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 395, name: '인스타그램 실시간 라이브 스트리밍 시청 [60분]', price: 12000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 396, name: '인스타그램 실시간 라이브 스트리밍 시청 [90분]', price: 18000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 397, name: '인스타그램 실시간 라이브 스트리밍 시청 [120분]', price: 24000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 398, name: '인스타그램 실시간 라이브 스트리밍 시청 [180분]', price: 36000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 399, name: '인스타그램 실시간 라이브 스트리밍 시청 [240분]', price: 48000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 400, name: '인스타그램 실시간 라이브 스트리밍 시청 [360분]', price: 72000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 서비스' },
      { id: 426, name: '인스타그램 실시간 라이브 스트리밍 시청 + 좋아요 + 댓글', price: 40000, min: 10, max: 10000, time: '데이터 부족', description: '실시간 라이브 스트리밍 시청 + 좋아요 + 댓글 서비스' }
    ],
    auto_likes_foreign: [
      { id: 105, name: '인스타그램 외국인 좋아요', price: 4000, min: 50, max: 10000, time: '데이터 부족', description: '외국인 좋아요 서비스' },
      { id: 116, name: '인스타그램 리얼 외국인 좋아요', price: 6000, min: 50, max: 10000, time: '데이터 부족', description: '리얼 외국인 좋아요 서비스' }
    ],
    auto_followers_foreign: [
      { id: 475, name: '인스타그램 외국인 팔로워', price: 10000, min: 100, max: 10000, time: '데이터 부족', description: '외국인 팔로워 서비스' }
    ],
    auto_comments_foreign: [
      { id: 480, name: '인스타그램 외국인 랜덤 댓글', price: 50000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 랜덤 댓글 서비스' },
      { id: 481, name: '인스타그램 외국인 커스텀 댓글', price: 60000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 커스텀 댓글 서비스' },
      { id: 358, name: '인스타그램 외국인 랜덤 이모지 댓글', price: 50000, min: 20, max: 1000, time: '데이터 부족', description: '외국인 랜덤 이모지 댓글 서비스' }
    ],
    auto_reels_views_foreign: [
      { id: 109, name: '인스타그램 동영상 조회수 [REEL/IGTV/VIDEO 가능]', price: 300, min: 100, max: 1000000, time: '데이터 부족', description: '동영상 조회수 서비스' },
      { id: 382, name: '인스타그램 동영상 조회수+저장+시간', price: 1200, min: 100, max: 1000000, time: '데이터 부족', description: '동영상 조회수+저장+시간 서비스' }
    ],
    auto_exposure_save_share_foreign: [
      { id: 142, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 2500, min: 100, max: 1000000, time: '데이터 부족', description: '노출+도달+추+프로필+기타 서비스' },
      { id: 145, name: '인스타그램 노출(+도달+추+프로필+기타)', price: 5000, min: 100, max: 1000000, time: '데이터 부족', description: '노출+도달+추+프로필+기타 서비스' },
      { id: 312, name: '인스타그램 저장', price: 500, min: 10, max: 10000, time: '데이터 부족', description: '저장 서비스' },
      { id: 313, name: '인스타그램 공유', price: 8000, min: 10, max: 10000, time: '데이터 부족', description: '공유 서비스' }
    ],

    // 페이스북 세부 서비스 데이터
    facebook: {
      foreign_services: [
        { id: 154, name: '페이스북 외국인 페이지 좋아요+팔로워', price: 15000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 156, name: '페이스북 외국인 페이지 팔로우', price: 15000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 314, name: '페이스북 외국인 프로필 팔로우', price: 35000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 318, name: '페이스북 외국인 게시물 좋아요', price: 10000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 319, name: '페이스북 외국인 이모지 리액션 [LOVE]', price: 30000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
      ],
      page_likes_korean: [
        { id: 226, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [일반]', price: 250000, min: 20, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 227, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [남성]', price: 400000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 228, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [여성]', price: 400000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 229, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [20대]', price: 400000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 230, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [30대]', price: 400000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 231, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [20대여자]', price: 500000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 232, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [20대남자]', price: 500000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 233, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [30대여자]', price: 500000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 234, name: 'KR 페이스북 리얼 한국인 페이지 좋아요+팔로워 [30대남자]', price: 500000, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      post_likes_korean: [
        { id: 198, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [일반]', price: 38000, min: 30, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 199, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [남성]', price: 55000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 200, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [여성]', price: 55000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 201, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [20대]', price: 55000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 202, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [30대]', price: 55000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 203, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [20대남자]', price: 60000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 204, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [20대여자]', price: 60000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 205, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [30대남자]', price: 60000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 206, name: 'KR 페이스북 리얼 한국인 게시물 좋아요 [30대여자]', price: 60000, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      post_comments_korean: [
        { id: 207, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [일반]', price: 270000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 209, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [남성]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 210, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [여성]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 211, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [20대]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 212, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [30대]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 213, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [20대여자]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 214, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [20대남자]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 215, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [30대여자]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 216, name: 'KR 페이스북 리얼 한국인 게시물 랜덤 댓글 [30대남자]', price: 450000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      profile_follows_korean: [
        { id: 217, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [일반]', price: 270000, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
        { id: 218, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [남성]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 219, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [여성]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 220, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [20대]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 221, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [30대]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 222, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [20대여자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 223, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [20대남자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 224, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [30대여자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 225, name: 'KR 페이스북 리얼 한국인 개인계정 팔로우 [30대남자]', price: 400000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 틱톡 세부 서비스 데이터
    tiktok: {
      likes_foreign: [
        { id: 458, name: '틱톡 외국인 리얼 좋아요', price: 9000, min: 100, max: 1000000, time: '10분', description: '상세정보' }
      ],
      views_foreign: [
        { id: 194, name: '틱톡 외국인 조회수', price: 400, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      views_korean: [
        { id: 497, name: 'KR 틱톡 리얼 한국인 조회수 [15초]', price: 30000, min: 100, max: 30000, time: '데이터 부족', description: '상세정보' }
      ],
      followers_foreign: [
        { id: 476, name: '틱톡 외국인 리얼 계정 팔로워 [중속]', price: 25000, min: 100, max: 1000000, time: '7시간 12분', description: '상세정보' },
        { id: 478, name: '틱톡 외국인 리얼 계정 팔로워 [중고속]', price: 30000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      save_share: [
        { id: 421, name: '틱톡 외국인 저장', price: 1500, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 422, name: '틱톡 외국인 공유', price: 2000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      live_streaming: [
        { id: 427, name: '틱톡 실시간 라이브 스트리밍 이모지 댓글', price: 8000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 429, name: '틱톡 실시간 라이브 스트리밍 커스텀 댓글', price: 12000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 430, name: '틱톡 실시간 라이브 스트리밍 100% 리얼 좋아요', price: 300000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 트위터 세부 서비스 데이터
    twitter: {
      followers_foreign: [
        { id: 197, name: '트위터(X) 외국인 팔로워', price: 80000, min: 100, max: 200000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 카카오/네이버 세부 서비스 데이터
    kakao_naver: {
      kakao_services: [
        { id: 271, name: 'K사 카카오 채널 친구 추가', price: 300000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
      ],
 
    },

    // 텔레그램 세부 서비스 데이터
    telegram: {
      subscribers: [
        { id: 437, name: '텔레그램 채널 구독자', price: 15000, min: 100, max: 50000, time: '데이터 부족', description: '상세정보' }
      ],
      views: [
        { id: 191, name: '텔레그램 게시물 조회수', price: 2000, min: 50, max: 10000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 왓츠앱 세부 서비스 데이터
    whatsapp: {
      followers: [
        { id: 442, name: '왓츠앱 채널 팔로워', price: 30000, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
      ]
    },





    // 유튜브 세부 서비스 데이터
    youtube: {
      views: [
        { id: 360, name: 'KR 유튜브 리얼 한국인 조회수', price: 40000, min: 4000, max: 100000, time: '데이터 부족', description: '상세정보' },
        { id: 496, name: 'KR 유튜브 리얼 한국인 조회수 [20초 시청]', price: 70000, min: 10, max: 30000, time: '데이터 부족', description: '상세정보' },
        { id: 371, name: '유튜브 외국인 동영상 조회수', price: 6000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      auto_views: [
        { id: 486, name: '🌐유튜브 외국인 동영상 자동 조회수', price: 6000, min: 1000, max: 10000000, time: '데이터 부족', description: '상세정보' }
      ],
      likes: [
        { id: 489, name: 'KR 유튜브 리얼 한국인 좋아요', price: 100000, min: 10, max: 1000, time: '데이터 부족', description: '상세정보' },
        { id: 136, name: '유튜브 외국인 좋아요', price: 8000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      auto_likes: [
        { id: 487, name: '🌐유튜브 외국인 동영상 자동 좋아요', price: 8000, min: 20, max: 500000, time: '데이터 부족', description: '상세정보' }
      ],
      subscribers: [
        { id: 485, name: 'KR 유튜브 리얼 한국인 채널 구독자 [고속]', price: 400000, min: 50, max: 10000, time: '11시간 40분', description: '상세정보' },
        { id: 236, name: 'KR 유튜브 리얼 한국인 채널 구독자 [대량]', price: 700000, min: 200, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 500, name: '유튜브 외국인 채널 구독자', price: 65000, min: 100, max: 100000, time: '데이터 부족', description: '상세정보' }
      ],
      comments_shares: [
        { id: 482, name: 'KR 유튜브 한국인 동영상 AI 랜덤 댓글', price: 300000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 262, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [일반]', price: 390000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 263, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [남성]', price: 590000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 264, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [여성]', price: 590000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 265, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [20대]', price: 590000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 266, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [30대]', price: 590000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 267, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [20대 남성]', price: 700000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 268, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [20대 여성]', price: 700000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 269, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [30대 남성]', price: 700000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 270, name: 'KR 유튜브 한국인 동영상 랜덤 댓글 [30대 여성]', price: 700000, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 261, name: 'KR 유튜브 한국 소셜 공유', price: 10000, min: 1, max: 1500, time: '데이터 부족', description: '상세정보' },
        { id: 423, name: '유튜브 외국인 랜덤 댓글', price: 50000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 138, name: '유튜브 외국인 커스텀 댓글', price: 60000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 260, name: '유튜브 외국인 이모지 랜덤 댓글', price: 50000, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      live_streaming: [
        { id: 393, name: '유튜브 외국인 실시간 라이브 스트리밍 [15분]', price: 10000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 394, name: '유튜브 외국인 실시간 라이브 스트리밍 [30분]', price: 20000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 395, name: '유튜브 외국인 실시간 라이브 스트리밍 [60분]', price: 40000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 396, name: '유튜브 외국인 실시간 라이브 스트리밍 [90분]', price: 60000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 397, name: '유튜브 외국인 실시간 라이브 스트리밍 [120분]', price: 80000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
        { id: 398, name: '유튜브 외국인 실시간 라이브 스트리밍 [180분]', price: 120000, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ]
    }
  }
  
  // 세부 서비스 목록 가져오기
  const getDetailedServices = (platform, serviceType) => {
  if (platform === 'top-exposure') {
    const services = instagramDetailedServices.top_exposure || {}
    if (serviceType === 'seo') {
      return filterValidServices(services.manual?.filter(s => s.id === 1001) || [])
    } else if (serviceType === 'instagram_optimization') {
      return filterValidServices(services.manual?.filter(s => s.id === 1002) || [])
    } else if (serviceType === 'entry_stage') {
      return filterValidServices(services.manual?.filter(s => s.id === 1003) || [])
    } else if (serviceType === 'maintenance_stage') {
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
      case 'top-exposure':
        return [
          { id: 'seo', name: '검색엔진 최적화 [SEO]', description: '웹사이트 SEO 최적화 서비스' },
          { id: 'instagram_optimization', name: '인스타 최적화 계정만들기 [30일]', description: '인스타그램 계정 최적화 및 관리' },
          { id: 'entry_stage', name: '추천탭 상위노출 (셀프) - 진입단계', description: '진입단계 4단계 완전 패키지' },
          { id: 'maintenance_stage', name: '추천탭 상위노출 (셀프) - 유지단계', description: '유지단계 2단계 완전 패키지' }
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
    
    // 패키지 상품인 경우 수량과 상관없이 고정 가격
    if (selectedDetailedService && selectedDetailedService.package) {
      basePrice = selectedDetailedService.price / 1000  // 패키지 전체 가격
    } else if (selectedPlatform === 'instagram' || selectedPlatform === 'threads' || selectedPlatform === 'youtube' || selectedPlatform === 'facebook' || selectedPlatform === 'naver' || selectedPlatform === 'tiktok' || selectedPlatform === 'twitter' || selectedPlatform === 'telegram' || selectedPlatform === 'whatsapp' || selectedPlatform === 'top-exposure') {
      // 일반 상품의 경우 수량에 따라 가격 계산
      basePrice = (selectedDetailedService.price / 1000) * quantity
    } else {
      // 기존 SMM KINGS 가격 사용
      basePrice = (selectedDetailedService.price / 1000) * quantity
    }
    
    // 할인 적용
    let discount = 0
    
    // 선택된 할인 쿠폰만 적용
    if (selectedDiscountCoupon && selectedDiscountCoupon.discount > 0) {
      discount = selectedDiscountCoupon.discount
    }
    
    const totalDiscount = discount
    
    const finalPrice = basePrice * (1 - totalDiscount / 100)
    setTotalPrice(Math.round(finalPrice))
  }, [selectedDetailedService, quantity, selectedPlatform])

  const handlePlatformSelect = (platformId) => {
    setSelectedPlatform(platformId)
    setSelectedServiceType('recommended')
    setSelectedDetailedService(null)
    
    // 플랫폼에 따라 기본 서비스 설정
    if (platformId === 'top-exposure') {
      setSelectedService('popular_posts')
      setQuantity(1)
    } else if (['recommended', 'event', 'account-management', 'package', 'other', 'threads', 'news-media', 'experience-group', 'kakao', 'store-marketing', 'app-marketing', 'seo-traffic'].includes(platformId)) {
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
      // 패키지 상품은 수량을 1로 고정
      if (detailedServices[0].package) {
        setQuantity(1)
      } else {
        setQuantity(0)
      }
    }
  }

  const handleDetailedServiceSelect = (detailedService) => {
    setSelectedDetailedService(detailedService)
    // 패키지 상품은 수량을 1로 고정, 일반 상품은 0으로 초기화
    if (detailedService.package) {
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
      
      const orderData = {
        user_id: userId,
        service_id: safeServiceId,
        link: safeLink,
        quantity: safeQuantity,
        price: safeTotalPrice,
        runs: 1,
        interval: 0,
        comments: safeComments,
        username: '',
        min: 0,
        // 분할 발송 정보
        is_split_delivery: isSplitDelivery,
        split_days: isSplitDelivery ? splitDays : null,
        split_quantity: isSplitDelivery ? getDailyQuantity() : null,
        // 선택된 할인 쿠폰 정보
        use_coupon: selectedDiscountCoupon && selectedDiscountCoupon.discount > 0,
        coupon_id: selectedDiscountCoupon && selectedDiscountCoupon.id !== 'no_discount' ? selectedDiscountCoupon.id : null,
        coupon_discount: selectedDiscountCoupon ? selectedDiscountCoupon.discount : 0,
        // 패키지 상품 정보
        package_steps: selectedDetailedService?.package && selectedDetailedService?.steps ? selectedDetailedService.steps.map(step => ({
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
            discount: selectedDiscountCoupon ? selectedDiscountCoupon.discount : 0,
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
        <h2>주문하기</h2>
        <p>원하는 서비스를 선택하고 주문해보세요!</p>
        
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
          {!['tiktok', 'threads', 'twitter', 'kakao', 'telegram', 'whatsapp'].includes(selectedPlatform) && (
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
                if (['tiktok', 'threads', 'twitter', 'kakao', 'telegram', 'whatsapp'].includes(selectedPlatform)) {
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
          <h3>
            주문 정보 입력
          </h3>
            <button 
              className="order-method-btn"
              onClick={() => setShowOrderMethodModal(true)}
            >
              📋 주문방법
            </button>
          </div>
          
          
          {/* Quantity Selection - 패키지 상품이 아닐 때만 표시 */}
          {selectedDetailedService && !selectedDetailedService.package && (
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

          {/* 할인 쿠폰 선택 */}
          {availableDiscountCoupons.length > 1 && (
            <div className="form-group">
              <label>할인 쿠폰 선택</label>
              <div className="discount-coupon-selection">
                {availableDiscountCoupons.map((coupon) => (
                  <div 
                    key={coupon.id}
                    className={`discount-coupon-option ${selectedDiscountCoupon?.id === coupon.id ? 'selected' : ''}`}
                    onClick={() => setSelectedDiscountCoupon(coupon)}
                  >
                    <div className="coupon-info">
                      <span className="coupon-name">{coupon.name}</span>
                      {coupon.discount > 0 && (
                        <span className="coupon-discount">{coupon.discount}% 할인</span>
              )}
            </div>
                    <div className="coupon-radio">
                      <input 
                        type="radio" 
                        name="discountCoupon" 
                        value={coupon.id}
                        checked={selectedDiscountCoupon?.id === coupon.id}
                        onChange={() => setSelectedDiscountCoupon(coupon)}
                      />
          </div>
                  </div>
                ))}
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

          {selectedDetailedService && selectedDetailedService.package && selectedDetailedService.steps && (
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

          {/* 예약 발송 체크박스 */}
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

          {/* 분할 발송 체크박스 */}
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


      {/* 주문방법 모달 */}
      {showOrderMethodModal && (
        <div className="order-method-modal-overlay">
          <div className="order-method-modal">
            <div className="modal-header">
              <h3>📋 주문방법 가이드</h3>
              <button 
                className="modal-close-btn"
                onClick={() => setShowOrderMethodModal(false)}
              >
                ✕
              </button>
            </div>
            
            <div className="modal-content">
              <div className="order-steps">
                <div className="step">
                  <div className="step-number">1</div>
                  <div className="step-content">
                    <h4>서비스 선택</h4>
                    <p>원하는 플랫폼과 서비스를 선택하세요</p>
                  </div>
                </div>
                
                <div className="step">
                  <div className="step-number">2</div>
                  <div className="step-content">
                    <h4>수량 입력</h4>
                    <p>원하는 수량을 입력하세요 (최소 수량 이상)</p>
                  </div>
                </div>
                
                <div className="step">
                  <div className="step-number">3</div>
                  <div className="step-content">
                    <h4>링크 입력</h4>
                    <p>대상 게시물의 URL 또는 사용자명을 입력하세요</p>
                  </div>
                </div>
                
                <div className="step">
                  <div className="step-number">4</div>
                  <div className="step-content">
                    <h4>구매하기</h4>
                    <p>모든 정보를 확인하고 구매하기 버튼을 클릭하세요</p>
                  </div>
                </div>
              </div>
              
              <div className="important-notes">
                <h4>⚠️ 주의사항</h4>
                <ul>
                  <li>공개 계정의 게시물만 주문 가능합니다</li>
                  <li>링크는 정확한 URL 또는 사용자명을 입력해주세요</li>
                  <li>수량은 최소 수량 이상 입력해주세요</li>
                  <li>주문 후 취소는 불가능하니 신중히 선택해주세요</li>
                </ul>
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                className="modal-confirm-btn"
                onClick={() => setShowOrderMethodModal(false)}
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 공지사항 팝업 */}
      {showNoticePopup && notices.length > 0 && (
        <div className="notice-popup-overlay">
          <div className="notice-popup">
            <div className="notice-popup-header">
              <h3>{notices[currentNoticeIndex]?.title}</h3>
              <button 
                className="notice-popup-close"
                onClick={handleCloseNotice}
              >
                ×
              </button>
            </div>
            <div className="notice-popup-content">
              {notices[currentNoticeIndex]?.image_url && (
                <img 
                  src={notices[currentNoticeIndex].image_url} 
                  alt="공지사항 이미지" 
                  className="notice-popup-image"
                />
              )}
              <p>{notices[currentNoticeIndex]?.content}</p>
            </div>
            <div className="notice-popup-footer">
              <button 
                className="notice-dismiss-btn"
                onClick={handleDismissToday}
              >
                오늘 하루 보지 않기
              </button>
              <div className="notice-popup-actions">
                {currentNoticeIndex < notices.length - 1 ? (
                  <button 
                    className="notice-next-btn"
                    onClick={handleNextNotice}
                  >
                    다음 공지사항
                  </button>
                ) : (
                  <button 
                    className="notice-close-btn"
                    onClick={handleCloseNotice}
                  >
                    확인
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

export default Home
