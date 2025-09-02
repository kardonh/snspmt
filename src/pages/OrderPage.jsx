import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ShoppingBag, ChevronDown, Star } from 'lucide-react'
import { getPlatformInfo, calculatePrice } from '../utils/platformUtils'
import { smmpanelApi, handleApiError, transformOrderData } from '../services/snspopApi'
import { useAuth } from '../contexts/AuthContext'
import './OrderPage.css'

// Force redeploy - Prevent rollback and fix deployment issues
// 강제 재배포 - 롤백 방지 및 배포 문제 해결
const OrderPage = () => {
  const { platform, serviceId } = useParams()
  const navigate = useNavigate()
  const { currentUser } = useAuth()
  
  // 🚀 완벽한 서비스 상태 관리 시스템
  const [selectedService, setSelectedService] = useState(() => {
    // 1단계: URL 파라미터에서 serviceId 추출
    const urlServiceId = serviceId && serviceId !== 'undefined' && serviceId !== undefined ? serviceId : null
    
    // 2단계: 기본 서비스 결정
    const defaultService = 'followers_korean'
    
    // 3단계: 최종 서비스 결정
    const finalService = urlServiceId || defaultService
    
    console.log('=== 🚀 OrderPage 완벽 초기화 ===')
    console.log('URL serviceId:', serviceId)
    console.log('URL platform:', platform)
    console.log('URL에서 추출된 서비스:', urlServiceId)
    console.log('기본 서비스:', defaultService)
    console.log('최종 선택된 서비스:', finalService)
    
    return finalService
  })
  
  // 🔍 서비스 상태 검증 및 복구 시스템
  const validateAndRecoverService = useCallback(() => {
    const services = getServicesForPlatform(platform)
    const validServiceIds = services.map(s => s.id)
    
    console.log('=== 🔍 서비스 상태 검증 ===')
    console.log('현재 selectedService:', selectedService)
    console.log('유효한 서비스 ID들:', validServiceIds)
    console.log('검증 결과:', validServiceIds.includes(selectedService))
    
    // 문제가 있는 경우 즉시 복구
    if (!selectedService || !validServiceIds.includes(selectedService)) {
      const recoveryService = validServiceIds[0]
      console.log('⚠️ 서비스 상태 문제 감지, 복구 중...')
      console.log('복구 대상 서비스:', recoveryService)
      
      setSelectedService(recoveryService)
      return recoveryService
    }
    
    console.log('✅ 서비스 상태 정상')
    return selectedService
  }, [platform, selectedService])
  
  // 🔧 강제 서비스 설정 시스템
  const forceSetValidService = useCallback((serviceId) => {
    if (!serviceId) return false
    
    const services = getServicesForPlatform(platform)
    const validServiceIds = services.map(s => s.id)
    
    if (validServiceIds.includes(serviceId)) {
      console.log('🔧 강제 서비스 설정:', serviceId)
      setSelectedService(serviceId)
      return true
    } else {
      console.error('❌ 유효하지 않은 서비스 ID:', serviceId)
      return false
    }
  }, [platform])
  
  // selectedService가 변경될 때마다 로깅
  useEffect(() => {
    console.log('=== selectedService 상태 변화 ===')
    console.log('새로운 selectedService:', selectedService)
    console.log('타입:', typeof selectedService)
    console.log('값:', selectedService)
  }, [selectedService])
  
  // URL 파라미터가 변경될 때 selectedService 업데이트
  useEffect(() => {
    if (serviceId && serviceId !== 'undefined' && serviceId !== undefined) {
      console.log('URL 파라미터 변경으로 selectedService 업데이트:', serviceId)
      setSelectedService(serviceId)
    }
  }, [serviceId])
  
  // 컴포넌트 마운트 시 selectedService가 유효한지 확인하고 수정
  useEffect(() => {
    const services = getServicesForPlatform(platform)
    const validServiceIds = services.map(s => s.id)
    
    console.log('=== 🔍 서비스 유효성 검증 ===')
    console.log('현재 selectedService:', selectedService)
    console.log('유효한 서비스 ID들:', validServiceIds)
    console.log('selectedService가 유효한가?', validServiceIds.includes(selectedService))
    
    // selectedService가 유효하지 않으면 첫 번째 유효한 서비스로 설정
    if (!selectedService || !validServiceIds.includes(selectedService)) {
      const firstValidService = validServiceIds[0]
      console.log('⚠️ selectedService가 유효하지 않음, 첫 번째 서비스로 설정:', firstValidService)
      setSelectedService(firstValidService)
    }
  }, [platform]) // selectedService 의존성 제거하여 무한 루프 방지
  
  const [quantity, setQuantity] = useState(200)
  const [totalPrice, setTotalPrice] = useState(0)
  const [showChecklist, setShowChecklist] = useState(false)
  const [link, setLink] = useState('')
  const [comments, setComments] = useState('')
  const [explanation, setExplanation] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [userPoints, setUserPoints] = useState(0)
  const [usePoints, setUsePoints] = useState(true)
  const [pointsToUse, setPointsToUse] = useState(0)
  const [finalPrice, setFinalPrice] = useState(0)
  
  const platformInfo = getPlatformInfo(platform)
  
  // 플랫폼별 서비스 목록
  const getServicesForPlatform = (platform) => {
    switch (platform) {
      case 'instagram':
        return [
          { id: 'followers_korean', name: '팔로워 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 100/20,000개 | 1개당 120원 | 리필불가 | ✴️ 인스타그램 업데이트로 인해 검토를 위한 플래그 지정을 꺼주세요 (설정 > 친구 팔로우 및 초대 > 검토를 위해 플래그 지정 끄기) | ✴️ 하루 약 500~1000명 팔로워 증가 | ✴️ 한국인 프로필 유저들로 유입되어 언팔에 의한 이탈 없음 | ✴️ 한국 시장에서의 신뢰도 및 인지도 향상 | ✴️ 인스타그램 인플루언서 프로그램 참여 자격 획득 가능 | ✴️ 브랜드 협업 및 수익화 기회 확대 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | ✴️ 계정 권위성 및 신뢰도 향상 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'followers_foreign', name: '팔로워 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 100/2,000개 | 1개당 1원 | 리필불가 | ✴️ 인스타그램 업데이트로 인해 검토를 위한 플래그 지정을 꺼주세요 (설정 > 친구 팔로우 및 초대 > 검토를 위해 플래그 지정 끄기) | ✴️ 하루 약 500~1000명 팔로워 증가 | ✴️ 글로벌 팔로워로 구성되어 국제적인 영향력 향상 | ✴️ 국제 시장에서의 브랜드 인지도 향상 | ✴️ 다국어 콘텐츠로 글로벌 시장 공략 가능 | ✴️ 인스타그램 인플루언서 프로그램 참여 자격 획득 가능 | ✴️ 브랜드 협업 및 수익화 기회 확대 | ✴️ 계정 권위성 및 신뢰도 향상 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'likes_korean', name: '좋아요 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 50/10,000개 | 1개당 7원 | 리필불가 | ✴️ 한국인 사용자로부터 좋아요를 받아 게시물의 인기도 향상 | ✴️ 자연스러운 한국어 사용자로 구성 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 댓글 및 공유 가능성 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 50명 단위 주문 가능' },
          { id: 'likes_foreign', name: '좋아요 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/50,000개 | 1개당 1원 | 리필불가 | ✴️ 외국인 사용자로부터 좋아요를 받아 게시물의 인기도 향상 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 국제 시장에서의 콘텐츠 인기도 향상 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 다국어 댓글 및 공유 가능성 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 글로벌 브랜드 인지도 및 신뢰도 향상 | ✴️ 해시태그 트렌딩 효과로 바이럴 확산 가능성 증대 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'comments_korean', name: '댓글 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 5/100개 | 1개당 200원 | 리필불가 | ✴️ 한국어 댓글을 달아 게시물의 상호작용 증가 | ✴️ 커스텀 댓글 입력 가능 | ✴️ 자연스러운 한국어 사용자로 구성 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 댓글을 통한 추가 상호작용 유도 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | ✴️ 게시물 노출도 및 상호작용 증가 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 5명 단위 주문 가능' },
          { id: 'comments_foreign', name: '댓글 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 10/1,000개 | 1개당 50원 | 리필불가 | ✴️ 외국어 댓글을 달아 게시물의 상호작용 증가 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 국제 시장에서의 콘텐츠 인기도 향상 | ✴️ 다국어 댓글로 국제적 소통 증대 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 글로벌 브랜드 인지도 및 신뢰도 향상 | ✴️ 해시태그 트렌딩 효과로 바이럴 확산 가능성 증대 | ✴️ 지역별 타겟팅으로 특정 국가 시장 공략 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 10명 단위 주문 가능' },
          { id: 'views_korean', name: '조회수 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/100,000,000개 | 1개당 1원 | 리필불가 | ✴️ 한국인 사용자로부터 조회수를 증가시켜 콘텐츠의 노출도 향상 | ✴️ 자연스러운 한국어 사용자로 구성 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 스토리 및 릴스 노출도 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | ✴️ 스토리 광고 및 브랜드 협업 기회 확대 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'views_foreign', name: '조회수 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/100,000,000개 | 1개당 0.5원 | 리필불가 | ✴️ 외국인 사용자로부터 조회수를 증가시켜 콘텐츠의 노출도 향상 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 국제 시장에서의 콘텐츠 인기도 향상 | ✴️ 스토리 및 릴스 노출도 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 글로벌 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 특정 국가 시장 공략 가능 | ✴️ 해시태그 트렌딩 효과로 바이럴 확산 가능성 증대 | ✴️ 스토리 광고 및 브랜드 협업 기회 확대 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' }
        ]
      case 'tiktok':
        return [
          { id: 'likes_foreign', name: '좋아요 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/100,000개 | 1개당 6원 | 리필불가 | ✴️ 외국인 사용자로부터 틱톡 동영상의 좋아요를 받아 인기도 향상 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 동영상 인기도 및 추천 알고리즘 향상 | ✴️ For You 페이지 노출도 증가 | ✴️ 해시태그 트렌딩 효과로 바이럴 확산 가능성 증대 | ✴️ 틱톡 크리에이터 프로그램 참여 자격 획득 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'followers_foreign', name: '팔로워 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 100/1,000,000개 | 1개당 20원 | 리필불가 | ✴️ 외국인 사용자로부터 틱톡 계정의 팔로워를 증가시켜 계정의 인기도 향상 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 계정 권위성 및 신뢰도 향상 | ✴️ 콘텐츠 노출도 증가 | ✴️ 틱톡 라이브 방송 시 시청자 수 증가 | ✴️ 브랜드 협업 및 수익화 기회 확대 | ✴️ 지역별 타겟팅으로 특정 국가 시장 공략 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'views_foreign', name: '조회수 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/2,000,000,000개 | 1개당 2원 | 리필불가 | ✴️ 외국인 사용자로부터 틱톡 동영상의 조회수를 증가시켜 콘텐츠의 노출도 향상 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 동영상 인기도 및 추천 알고리즘 향상 | ✴️ For You 페이지 노출도 증가 | ✴️ 해시태그 트렌딩 효과로 바이럴 확산 가능성 증대 | ✴️ 광고 수익 및 브랜드 협업 기회 확대 | ✴️ 지역별 인기 콘텐츠로 등극 가능 | ✴️ 틱톡 크리에이터 프로그램 참여 자격 획득 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'comments_foreign', name: '댓글 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 10/2,000개 | 1개당 200원 | 리필불가 | ✴️ 외국인 사용자로부터 틱톡 동영상에 댓글을 달아 상호작용 증가 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 동영상 인기도 및 추천 알고리즘 향상 | ✴️ For You 페이지 노출도 증가 | ✴️ 다국어 댓글로 국제적 소통 증대 | ✴️ 해시태그 트렌딩 효과로 바이럴 확산 가능성 증대 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 특정 국가 시장 공략 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 10명 단위 주문 가능' }
        ]
      case 'twitter':
        return [
          { id: 'followers_real', name: '팔로워 (리얼)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 100/200,000개 | 1개당 28원 | 리필불가 | ✴️ 리얼 사용자로부터 트위터 계정의 팔로워를 증가시켜 계정의 인기도 향상 | ✴️ 자연스러운 사용자로 구성되어 언팔에 의한 이탈 최소화 | ✴️ 계정 권위성 및 신뢰도 향상 | ✴️ 트윗 노출도 및 리트윗 가능성 증가 | ✴️ 브랜드 협업 및 수익화 기회 확대 | ✴️ 트위터 블루 인증 획득 자격 향상 | ✴️ 정치, 비즈니스, 엔터테인먼트 등 다양한 분야에서 영향력 증대 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' }
        ]

      case 'facebook':
        return [
          { id: 'followers_korean', name: '개인계정 팔로우 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 100/50,000개 | 1개당 20원 | 리필불가 | ✴️ 한국인 사용자로부터 페이스북 개인계정의 팔로우를 증가시켜 계정의 인기도 향상 | ✴️ 자연스러운 한국어 사용자로 구성되어 언팔에 의한 이탈 최소화 | ✴️ 개인 브랜딩 및 영향력 증대 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 한국 시장에서의 신뢰도 및 인지도 향상 | ✴️ 비즈니스 네트워킹 기회 확대 | ✴️ 페이스북 인플루언서 프로그램 참여 자격 획득 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'followers_foreign', name: '프로필 팔로우 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 100/100,000개 | 1개당 20원 | 리필불가 | ✴️ 외국인 사용자로부터 페이스북 프로필의 팔로우를 증가시켜 계정의 인기도 향상 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 계정 권위성 및 신뢰도 향상 | ✴️ 콘텐츠 노출도 및 상호작용 증가 | ✴️ 국제 시장에서의 브랜드 인지도 향상 | ✴️ 다국어 콘텐츠로 글로벌 시장 공략 가능 | ✴️ 페이스북 인플루언서 프로그램 참여 자격 획득 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'likes_korean', name: '게시물 좋아요 (리얼 한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/50,000개 | 1개당 20원 | 리필불가 | ✴️ 리얼 한국인 사용자로부터 페이스북 게시물의 좋아요를 받아 게시물의 인기도 향상 | ✴️ 자연스러운 한국어 사용자로 구성되어 언팔에 의한 이탈 최소화 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 댓글 및 공유 가능성 증가 | ✴️ 페이스북 알고리즘에서 우선순위 상승 | ✴️ 브랜드 인지도 및 신뢰도 향상 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'likes_foreign', name: '게시물 좋아요 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/100,000개 | 1개당 20원 | 리필불가 | ✴️ 외국인 사용자로부터 페이스북 게시물의 좋아요를 받아 게시물의 인기도 향상 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 국제 시장에서의 콘텐츠 인기도 향상 | ✴️ 다국어 댓글 및 공유 가능성 증가 | ✴️ 페이스북 알고리즘에서 우선순위 상승 | ✴️ 글로벌 브랜드 인지도 및 신뢰도 향상 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'comments_korean', name: '게시물 랜덤 댓글 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 10/1,000개 | 1개당 200원 | 리필불가 | ✴️ 한국인 사용자로부터 페이스북 게시물에 랜덤 댓글을 달아 상호작용 증가 | ✴️ 자연스러운 한국어 댓글로 구성되어 현지 시장에서의 신뢰도 향상 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 댓글을 통한 추가 상호작용 유도 | ✴️ 페이스북 알고리즘에서 우선순위 상승 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 10명 단위 주문 가능' }
        ]
      case 'youtube':
        return [
          { id: 'followers_foreign', name: '구독자 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 100/100개 | 1개당 50원 | 리필불가 | ✴️ 외국인 사용자로부터 유튜브 채널의 구독자 수 증가 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 채널 인기도 및 권위성 향상 | ✴️ 유튜브 파트너 프로그램 참여 자격 획득 가능 | ✴️ 광고 수익 및 브랜드 협업 기회 확대 | ✴️ 다국어 콘텐츠로 글로벌 시장 공략 가능 | ✴️ 채널 추천 알고리즘에서 우선순위 상승 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'followers_korean', name: '구독자 (리얼 한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 50/1,000개 | 1개당 500원 | 리필불가 | ✴️ 리얼 한국인 사용자로부터 유튜브 채널의 구독자 수 증가 | ✴️ 자연스러운 한국어 사용자로 구성 | ✴️ 채널 인기도 및 권위성 향상 | ✴️ 언팔에 의한 이탈 최소화 | ✴️ 한국 시장에서의 신뢰도 및 인지도 향상 | ✴️ 유튜브 파트너 프로그램 참여 자격 획득 가능 | ✴️ 한국 시장에서의 브랜드 협업 기회 확대 | ✴️ 채널 추천 알고리즘에서 우선순위 상승 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 50명 단위 주문 가능' },
          { id: 'likes_foreign', name: '좋아요 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/5,000개 | 1개당 7원 | 리필불가 | ✴️ 외국인 사용자로부터 유튜브 동영상의 좋아요 수 증가 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 동영상 인기도 및 추천 알고리즘 향상 | ✴️ 동영상 노출도 및 검색 순위 상승 | ✴️ 댓글 및 공유 가능성 증가 | ✴️ 글로벌 시장에서의 콘텐츠 인기도 향상 | ✴️ 브랜드 인지도 및 신뢰도 향상 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'comments_korean', name: '댓글 (AI 랜덤 한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 10/10,000개 | 1개당 150원 | 리필불가 | ✴️ AI가 생성한 한국어 댓글을 달아 동영상의 상호작용 증가 | ✴️ 자연스러운 한국어 댓글으로 구성 | ✴️ 동영상 인기도 및 추천 알고리즘 향상 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 댓글을 통한 추가 상호작용 유도 | ✴️ 동영상 노출도 및 검색 순위 상승 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 10명 단위 주문 가능' },
          { id: 'views_foreign', name: '조회수 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/10,000,000개 | 1개당 7원 | 리필불가 | ✴️ 외국인 사용자로부터 유튜브 동영상의 조회수 증가 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 동영상 노출도 및 추천 알고리즘 향상 | ✴️ 동영상 검색 순위 및 추천 영상 등극 가능 | ✴️ 글로벌 시장에서의 콘텐츠 인기도 향상 | ✴️ 광고 수익 및 브랜드 협업 기회 확대 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 동영상 트렌딩 효과로 바이럴 확산 가능성 증대 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'views_korean', name: '조회수 (리얼 한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 4,000/100,000개 | 1개당 25원 | 리필불가 | ✴️ 리얼 한국인 사용자로부터 유튜브 동영상의 조회수 증가 | ✴️ 자연스러운 한국어 사용자로 구성 | ✴️ 동영상 노출도 및 추천 알고리즘 향상 | ✴️ 언팔에 의한 이탈 최소화 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 동영상 검색 순위 및 추천 영상 등극 가능 | ✴️ 한국 시장에서의 브랜드 협업 기회 확대 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 1,000명 단위 주문 가능' }
        ]
      default:
        return [
          { id: 'followers_korean', name: '팔로워 (한국인)', description: '한국인 팔로워를 늘려드리는 서비스입니다. 한국어 사용자로 구성되어 있어 더 자연스러운 팔로워 증가를 기대할 수 있습니다.' },
          { id: 'followers_foreign', name: '팔로워 (외국인)', description: '외국인 팔로워를 늘려드리는 서비스입니다. 글로벌 팔로워로 구성되어 있어 국제적인 영향력을 높일 수 있습니다.' },
          { id: 'likes_korean', name: '좋아요 (한국인)', description: '한국인 사용자로부터 좋아요를 받아 게시물의 인기도를 높여드리는 서비스입니다.' },
          { id: 'likes_foreign', name: '좋아요 (외국인)', description: '외국인 사용자로부터 좋아요를 받아 게시물의 인기도를 높여드리는 서비스입니다.' },
          { id: 'comments_korean', name: '댓글 (한국인)', description: '한국어 댓글을 달아 게시물의 인기도를 높여드리는 서비스입니다. 커스텀 댓글을 입력할 수 있습니다.' },
          { id: 'comments_foreign', name: '댓글 (외국인)', description: '외국어 댓글을 달아 게시물의 인기도를 높여드리는 서비스입니다.' },
          { id: 'views_korean', name: '조회수 (한국인)', description: '한국인 사용자로부터 조회수를 증가시켜 콘텐츠의 노출도를 높여드리는 서비스입니다.' },
          { id: 'views_foreign', name: '조회수 (외국인)', description: '외국인 사용자로부터 조회수를 증가시켜 콘텐츠의 노출도를 높여드리는 서비스입니다.' }
        ]
    }
  }
  
  const services = getServicesForPlatform(platform)
  
  // 🎯 완벽한 서비스 선택 핸들러
  const handleServiceSelect = (serviceId) => {
    console.log('=== 🎯 서비스 선택 시작 ===')
    console.log('선택된 서비스 ID:', serviceId)
    console.log('이전 selectedService:', selectedService)
    console.log('현재 플랫폼:', platform)
    
    // 1단계: 입력값 검증
    if (!serviceId || serviceId === 'undefined' || serviceId === undefined) {
      console.error('❌ 유효하지 않은 서비스 ID 입력:', serviceId)
      alert('유효한 서비스를 선택해주세요.')
      return
    }
    
    // 2단계: 서비스 유효성 검증
    const services = getServicesForPlatform(platform)
    const validServiceIds = services.map(s => s.id)
    
    if (!validServiceIds.includes(serviceId)) {
      console.error('❌ 존재하지 않는 서비스 ID:', serviceId)
      console.error('유효한 서비스 ID들:', validServiceIds)
      alert('선택한 서비스가 존재하지 않습니다. 다시 선택해주세요.')
      return
    }
    
    // 3단계: 서비스 설정 및 로깅
    console.log('✅ 유효한 서비스 선택 확인')
    console.log('이전 서비스:', selectedService)
    console.log('새로운 서비스:', serviceId)
    
    setSelectedService(serviceId)
    
    // 4단계: 설정 완료 확인
    console.log('🎉 서비스 선택 완료:', serviceId)
    
    // 5단계: 추가 검증
    setTimeout(() => {
      if (selectedService === serviceId) {
        console.log('✅ 서비스 상태 동기화 완료')
      } else {
        console.warn('⚠️ 서비스 상태 동기화 지연, 강제 설정 시도')
        forceSetValidService(serviceId)
      }
    }, 100)
  }
  
  // 포인트 로드
  const loadUserPoints = async () => {
    if (currentUser) {
      try {
        const response = await smmpanelApi.getUserPoints(currentUser.uid)
        setUserPoints(response.points || 0)
      } catch (error) {
        console.error('포인트 조회 실패:', error)
      }
    }
  }

  useEffect(() => {
    loadUserPoints()
  }, [currentUser])

  useEffect(() => {
    const price = calculatePrice(selectedService, quantity, platform)
    setTotalPrice(price)
    
    // 서비스가 변경되면 수량 옵션 업데이트
    const newQuantityOptions = getQuantityOptions(platform, selectedService)
    if (newQuantityOptions !== quantityOptions) {
      // 현재 선택된 수량이 새로운 옵션에 없으면 첫 번째 옵션으로 설정
      if (!newQuantityOptions.includes(quantity)) {
        setQuantity(newQuantityOptions[0])
      }
    }
  }, [selectedService, quantity, platform])

  // 포인트 사용 계산
  useEffect(() => {
    if (usePoints && userPoints > 0) {
      const maxPointsToUse = Math.min(userPoints, totalPrice)
      setPointsToUse(maxPointsToUse)
      setFinalPrice(totalPrice - maxPointsToUse)
    } else {
      setPointsToUse(0)
      setFinalPrice(totalPrice)
    }
  }, [usePoints, userPoints, totalPrice])

  // 포인트 부족 시 포인트 충전 페이지로 이동
  const handleInsufficientPoints = () => {
    const insufficientAmount = totalPrice - userPoints
    alert(`포인트가 부족합니다. ${insufficientAmount.toLocaleString()}P가 더 필요합니다. 포인트 충전 페이지로 이동합니다.`)
    navigate('/points')
  }
  
  // snspop API 서비스 ID 매핑
  const serviceIdMapping = {
    instagram: {
              followers_korean: 577,    // 인스타그램 팔로워 (한국인) - API ID: 577
      followers_foreign: 855,   // 인스타그램 팔로워 (외국인) - API ID: 855
      likes_korean: 790,        // 인스타그램 좋아요 (한국인) - API ID: 790
      likes_foreign: 458,       // 인스타그램 좋아요 (외국인) - API ID: 458
      comments_korean: 841,     // 인스타그램 댓글 (한국인) - API ID: 841
      comments_foreign: 645,    // 인스타그램 댓글 (외국인) - API ID: 645
      views_korean: 619,        // 인스타그램 조회수 (한국인) - API ID: 619
      views_foreign: 791        // 인스타그램 조회수 (외국인) - API ID: 791
    },
    tiktok: {
      likes_foreign: 244,      // 틱톡 외국인 좋아요 - API ID: 244
      followers_foreign: 702,  // 틱톡 외국인 계정 팔로워 - API ID: 702
      views_foreign: 245,      // 틱톡 외국인 조회수 - API ID: 245
      comments_foreign: 847    // 틱톡 외국인 랜덤 댓글 - API ID: 847
    },
    twitter: {
      followers_real: 780      // 트위터 리얼 팔로워 - API ID: 780
    },
    facebook: {
      followers_korean: 564,   // 페이스북 한국인 개인계정 팔로우 - API ID: 564
      followers_foreign: 818,  // 페이스북 외국인 프로필 팔로우 - API ID: 818
      likes_korean: 546,       // 페이스북 리얼 한국인 게시물 좋아요 - API ID: 546
      likes_foreign: 451,      // 페이스북 외국인 게시물 좋아요 - API ID: 451
      comments_korean: 292     // 페이스북 한국인 게시물 랜덤 댓글 - API ID: 292
    },
    youtube: {
                    followers_foreign: 150,    // 유튜브 외국인 채널 구독자
                    followers_korean: 872,     // 유튜브 리얼 한국인 채널 구독자
                    likes_foreign: 638,        // 유튜브 외국인 동영상 좋아요
                    comments_korean: 869,      // 유튜브 한국인 동영상 AI 랜덤 댓글
                    views_foreign: 833,        // 유튜브 외국인 동영상 조회수
                    views_korean: 731          // 유튜브 리얼 한국인 동영상 조회수
                  }
  }
  
  // 기본 수량 옵션
  const baseQuantityOptions = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
  
  // 서비스별 수량 옵션 반환 함수
  const getQuantityOptions = (platform, service) => {
    if (platform === 'instagram') {
      switch (service) {
        case 'followers_foreign': // 외국인 팔로워: 100-2000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000]
        case 'followers_korean': // 한국인 팔로워: 50-20000
          return [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000]
        case 'likes_foreign': // 외국인 좋아요: 100-50000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000]
        case 'likes_korean': // 한국인 좋아요: 50-10000
          return [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        case 'comments_korean': // 한국인 랜덤 댓글: 5-100
          return [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100]
        case 'comments_foreign': // 외국인 랜덤 댓글: 10-1000
          return [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
        case 'views_korean': // 한국인 조회수: 100-100000000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 150000, 200000, 250000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1500000, 2000000, 2500000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000, 15000000, 20000000, 25000000, 30000000, 40000000, 50000000, 60000000, 70000000, 80000000, 90000000, 100000000]
        case 'views_foreign': // 외국인 조회수: 100-100000000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 150000, 200000, 250000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1500000, 2000000, 2500000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000, 15000000, 20000000, 25000000, 30000000, 40000000, 50000000, 60000000, 70000000, 80000000, 90000000, 100000000]
        default:
          return baseQuantityOptions
      }
    } else if (platform === 'youtube') {
      switch (service) {
        case 'followers_foreign': // 외국인 구독자: 100-100
          return [100]
        case 'followers_korean': // 리얼 한국인 구독자: 50-1000
          return [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        case 'likes_foreign': // 외국인 좋아요: 100-5000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000]
        case 'comments_korean': // AI 랜덤 한국인 댓글: 10-10000
          return [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        case 'views_foreign': // 외국인 조회수: 100-10000000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 150000, 200000, 250000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1500000, 2000000, 2500000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000, 15000000, 20000000, 25000000, 30000000, 40000000, 50000000, 60000000, 70000000, 80000000, 90000000, 10000000]
        case 'views_korean': // 리얼 한국인 조회수: 4000-100000
          return [4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]
        default:
          return baseQuantityOptions
      }
    } else if (platform === 'tiktok') {
      switch (service) {
        case 'likes_foreign': // 외국인 좋아요: 100-100000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]
        case 'followers_foreign': // 외국인 계정 팔로워: 100-1000000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 150000, 200000, 250000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000]
        case 'views_foreign': // 외국인 조회수: 100-2000000000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 150000, 200000, 250000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1500000, 2000000, 2500000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000, 15000000, 20000000, 25000000, 30000000, 40000000, 50000000, 60000000, 70000000, 80000000, 90000000, 100000000, 150000000, 200000000, 250000000, 300000000, 400000000, 500000000, 600000000, 700000000, 800000000, 900000000, 1000000000, 1500000000, 2000000000]
        case 'comments_foreign': // 외국인 랜덤 댓글: 10-2000
          return [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000]
        default:
          return baseQuantityOptions
      }
    } else if (platform === 'twitter') {
      switch (service) {
        case 'followers_real': // 리얼 팔로워: 100-200000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 150000, 200000]
        default:
          return baseQuantityOptions
      }
    } else if (platform === 'facebook') {
      switch (service) {
        case 'followers_korean': // 한국인 개인계정 팔로우: 5-2500
          return [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500]
        case 'followers_foreign': // 외국인 프로필 팔로우: 100-1000000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 150000, 200000, 250000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000]
        case 'likes_korean': // 리얼 한국인 게시물 좋아요: 20-10000
          return [20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        case 'likes_foreign': // 외국인 게시물 좋아요: 100-100000
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]
        case 'comments_korean': // 한국인 게시물 랜덤 댓글: 10-10000
          return [10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        default:
          return baseQuantityOptions
      }
    }
    // 다른 플랫폼들은 기본 옵션 사용
    return baseQuantityOptions
  }
  
  const quantityOptions = getQuantityOptions(platform, selectedService)
  
  const discountTiers = [
    { min: 500, max: 999, discount: 10 },
    { min: 1000, max: 4999, discount: 15 },
    { min: 5000, max: 10000, discount: 20 }
  ]
  
  const getDiscount = (qty) => {
    const tier = discountTiers.find(t => qty >= t.min && qty <= t.max)
    return tier ? tier.discount : 0
  }
  
  const handleQuantityChange = (newQuantity) => {
    setQuantity(newQuantity)
  }
  
      // 🚀 완벽한 주문 생성 시스템
  const handlePurchase = async () => {
    console.log('=== 🚀 주문 생성 시작 ===')
    console.log('현재 상태:', {
      selectedService,
      platform,
      link: link?.trim(),
      quantity,
      userPoints,
      totalPrice,
      finalPrice
    })
    
    try {
      // 1단계: 서비스 상태 완벽 검증 및 복구
      console.log('🔍 1단계: 서비스 상태 검증 시작')
      const validatedService = validateAndRecoverService()
      
      if (!validatedService) {
        console.error('❌ 서비스 검증 실패')
        alert('서비스를 선택할 수 없습니다. 페이지를 새로고침해주세요.')
        return
      }
      
      console.log('✅ 서비스 검증 완료:', validatedService)
      
      // 2단계: 최종 서비스 상태 확인
      console.log('🔍 2단계: 최종 서비스 상태 확인')
      const services = getServicesForPlatform(platform)
      const validServiceIds = services.map(s => s.id)
      
      if (!validServiceIds.includes(validatedService)) {
        console.error('❌ 최종 서비스 검증 실패:', validatedService)
        console.error('유효한 서비스 ID들:', validServiceIds)
        alert('선택된 서비스가 유효하지 않습니다. 다시 선택해주세요.')
        return
      }
      
      console.log('✅ 최종 서비스 검증 완료:', validatedService)
      
      // 3단계: 서비스 상태 동기화 확인
      if (selectedService !== validatedService) {
        console.warn('⚠️ 서비스 상태 불일치 감지, 동기화 중...')
        setSelectedService(validatedService)
        
        // 상태 업데이트 대기
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      
            console.log('🎯 최종 사용할 서비스 ID:', validatedService)
      
      // 4단계: 포인트 검증
      console.log('🔍 4단계: 포인트 검증')
      if (usePoints && userPoints < totalPrice) {
        handleInsufficientPoints()
        return
      }

      // 5단계: 입력 검증
      console.log('🔍 5단계: 입력 검증')
      if (!link.trim()) {
        alert('링크를 입력해주세요!')
        return
      }
      
      if (((platform === 'instagram' && (selectedService === 'comments_korean' || selectedService === 'comments_foreign')) || 
           (platform === 'youtube' && selectedService === 'comments_korean') ||
           (platform === 'facebook' && selectedService === 'comments_korean')) && !comments.trim()) {
        alert('댓글 내용을 입력해주세요!')
        return
      }

      // Instagram 서비스별 수량 제한 검증
      if (platform === 'instagram') {
        switch (selectedService) {
          case 'followers_foreign': // 외국인 팔로워: 100-2000
            if (quantity < 100 || quantity > 2000) {
              alert('외국인 팔로워 서비스는 100개에서 2000개까지 주문 가능합니다.')
              return
            }
            break
          case 'followers_korean': // 한국인 팔로워: 50-20000
            if (quantity < 50 || quantity > 20000) {
              alert('한국인 팔로워 서비스는 50개에서 20000개까지 주문 가능합니다.')
              return
            }
            break
          case 'likes_foreign': // 외국인 좋아요: 100-50000
            if (quantity < 100 || quantity > 50000) {
              alert('외국인 좋아요 서비스는 100개에서 50000개까지 주문 가능합니다.')
              return
            }
            break
          case 'likes_korean': // 한국인 좋아요: 50-10000
            if (quantity < 50 || quantity > 10000) {
              alert('한국인 좋아요 서비스는 50개에서 10000개까지 주문 가능합니다.')
              return
            }
            break
          case 'comments_korean': // 한국인 랜덤 댓글: 5-100
            if (quantity < 5 || quantity > 100) {
              alert('한국인 랜덤 댓글 서비스는 5개에서 100개까지 주문 가능합니다.')
              return
            }
            break
          case 'comments_foreign': // 외국인 랜덤 댓글: 10-1000
            if (quantity < 10 || quantity > 1000) {
              alert('외국인 랜덤 댓글 서비스는 10개에서 1000개까지 주문 가능합니다.')
              return
            }
            break
          case 'views_korean': // 한국인 조회수: 100-100000000
            if (quantity < 100 || quantity > 100000000) {
              alert('한국인 조회수 서비스는 100개에서 100,000,000개까지 주문 가능합니다.')
              return
            }
            break
          case 'views_foreign': // 외국인 조회수: 100-100000000
            if (quantity < 100 || quantity > 100000000) {
              alert('외국인 조회수 서비스는 100개에서 100,000,000개까지 주문 가능합니다.')
              return
            }
            break
        }
      }

      // YouTube 서비스별 수량 제한 검증
      if (platform === 'youtube') {
        switch (selectedService) {
          case 'followers_foreign': // 외국인 구독자: 100-100
            if (quantity !== 100) {
              alert('외국인 구독자 서비스는 100개만 주문 가능합니다.')
              return
            }
            break
          case 'followers_korean': // 리얼 한국인 구독자: 50-1000
            if (quantity < 50 || quantity > 1000) {
              alert('리얼 한국인 구독자 서비스는 50개에서 1000개까지 주문 가능합니다.')
              return
            }
            break
          case 'likes_foreign': // 외국인 좋아요: 100-5000
            if (quantity < 100 || quantity > 5000) {
              alert('외국인 좋아요 서비스는 100개에서 5000개까지 주문 가능합니다.')
              return
            }
            break
          case 'comments_korean': // AI 랜덤 한국인 댓글: 10-10000
            if (quantity < 10 || quantity > 10000) {
              alert('AI 랜덤 한국인 댓글 서비스는 10개에서 10000개까지 주문 가능합니다.')
              return
            }
            break
          case 'views_foreign': // 외국인 조회수: 100-10000000
            if (quantity < 100 || quantity > 10000000) {
              alert('외국인 조회수 서비스는 100개에서 10,000,000개까지 주문 가능합니다.')
              return
            }
            break
          case 'views_korean': // 리얼 한국인 조회수: 4000-100000
            if (quantity < 4000 || quantity > 100000) {
              alert('리얼 한국인 조회수 서비스는 4000개에서 100,000개까지 주문 가능합니다.')
              return
            }
            break
        }
      }

      // TikTok 서비스별 수량 제한 검증
      if (platform === 'tiktok') {
        switch (selectedService) {
          case 'likes_foreign': // 외국인 좋아요: 100-100000
            if (quantity < 100 || quantity > 100000) {
              alert('외국인 좋아요 서비스는 100개에서 100,000개까지 주문 가능합니다.')
              return
            }
            break
          case 'followers_foreign': // 외국인 계정 팔로워: 100-1000000
            if (quantity < 100 || quantity > 1000000) {
              alert('외국인 계정 팔로워 서비스는 100개에서 1,000,000개까지 주문 가능합니다.')
              return
            }
            break
          case 'views_foreign': // 외국인 조회수: 100-2000000000
            if (quantity < 100 || quantity > 2000000000) {
              alert('외국인 조회수 서비스는 100개에서 2,000,000,000개까지 주문 가능합니다.')
              return
            }
            break
          case 'comments_foreign': // 외국인 랜덤 댓글: 10-2000
            if (quantity < 10 || quantity > 2000) {
              alert('외국인 랜덤 댓글 서비스는 10개에서 2,000개까지 주문 가능합니다.')
              return
            }
            break
        }
      }

      // Facebook 서비스별 수량 제한 검증
      if (platform === 'facebook') {
        switch (selectedService) {
          case 'followers_korean': // 개인계정 팔로우: 5-2500
            if (quantity < 5 || quantity > 2500) {
              alert('개인계정 팔로우 서비스는 5개에서 2,500개까지 주문 가능합니다.')
              return
            }
            break
          case 'followers_foreign': // 프로필 팔로우: 100-1000000
            if (quantity < 100 || quantity > 1000000) {
              alert('프로필 팔로우 서비스는 100개에서 1,000,000개까지 주문 가능합니다.')
              return
            }
            break
          case 'likes_korean': // 게시물 좋아요 (리얼 한국인): 100-1000000
            if (quantity < 100 || quantity > 1000000) {
              alert('게시물 좋아요 (리얼 한국인) 서비스는 100개에서 1,000,000개까지 주문 가능합니다.')
              return
            }
            break
          case 'likes_foreign': // 게시물 좋아요 (외국인): 100-1000000
            if (quantity < 100 || quantity > 1000000) {
              alert('게시물 좋아요 (외국인) 서비스는 100개에서 1,000,000개까지 주문 가능합니다.')
              return
            }
            break
          case 'comments_korean': // 게시물 랜덤 댓글 (한국인): 10-1000000
            if (quantity < 10 || quantity > 1000000) {
              alert('게시물 랜덤 댓글 (한국인) 서비스는 10개에서 1,000,000개까지 주문 가능합니다.')
              return
            }
            break
        }
      }

      // Twitter 서비스별 수량 제한 검증
      if (platform === 'twitter') {
        switch (selectedService) {
          case 'followers_real': // 리얼 팔로워: 100-200000
            if (quantity < 100 || quantity > 200000) {
              alert('리얼 팔로워 서비스는 100개에서 200,000개까지 주문 가능합니다.')
              return
            }
            break
        }
      }

      // KakaoTalk 서비스별 수량 제한 검증
      if (platform === 'kakaotalk') {
        switch (selectedService) {
          case 'friends_real': // 리얼 채널 친구 추가: 100-10000
            if (quantity < 100 || quantity > 10000) {
              alert('리얼 채널 친구 추가 서비스는 100개에서 10,000개까지 주문 가능합니다.')
              return
            }
            break
        }
      }


      
      setIsLoading(true)
      
      try {
        // 1단계: 서비스 상태 완벽 검증 및 복구
        console.log('🔍 1단계: 서비스 상태 검증 시작')
        const validatedService = validateAndRecoverService()
        
        if (!validatedService) {
          console.error('❌ 서비스 검증 실패')
          alert('서비스를 선택할 수 없습니다. 페이지를 새로고침해주세요.')
          return
        }
        
        console.log('✅ 서비스 검증 완료:', validatedService)
        
        // 2단계: 최종 서비스 상태 확인
        console.log('🔍 2단계: 최종 서비스 상태 확인')
        const services = getServicesForPlatform(platform)
        const validServiceIds = services.map(s => s.id)
        
        if (!validServiceIds.includes(validatedService)) {
          console.error('❌ 최종 서비스 검증 실패:', validatedService)
          console.error('유효한 서비스 ID들:', validServiceIds)
          alert('선택된 서비스가 유효하지 않습니다. 다시 선택해주세요.')
          return
        }
        
        console.log('✅ 최종 서비스 검증 완료:', validatedService)
        
        // 3단계: 서비스 상태 동기화 확인
        if (selectedService !== validatedService) {
          console.warn('⚠️ 서비스 상태 불일치 감지, 동기화 중...')
          setSelectedService(validatedService)
          
          // 상태 업데이트 대기
          await new Promise(resolve => setTimeout(resolve, 50))
        }
        
        console.log('🎯 최종 사용할 서비스 ID:', validatedService)
        
        console.log('=== handlePurchase 디버깅 ===')
        console.log('Platform:', platform)
        console.log('Selected Service:', selectedService)
        console.log('Validated Service:', validatedService)
        console.log('Services Array:', services)
        
        // 4단계: 포인트 검증
        console.log('🔍 4단계: 포인트 검증')
        if (usePoints && userPoints < totalPrice) {
          handleInsufficientPoints()
          return
        }

        // 5단계: 입력 검증
        console.log('🔍 5단계: 입력 검증')
        if (!link.trim()) {
          alert('링크를 입력해주세요!')
          return
        }
        
        // 안전한 값 준비
        const safeLink = link && typeof link === 'string' ? link.trim() : ''
        const safeQuantity = quantity && !isNaN(Number(quantity)) ? Number(quantity) : 0
        const safeComments = comments && typeof comments === 'string' ? comments.trim() : ''
        const safeExplanation = explanation && typeof explanation === 'string' ? explanation.trim() : ''
        
        // 6단계: 주문 데이터 생성
        console.log('🔍 6단계: 주문 데이터 생성')
        const orderData = {
          serviceId: validatedService, // 검증된 서비스 ID 사용
          link: safeLink,
          quantity: safeQuantity,
          runs: 1, // 기본 실행 횟수
          interval: 0, // 즉시 실행
          comments: safeComments, // 커스텀 댓글 (댓글 서비스인 경우)
          explanation: safeExplanation, // 설명 (추가 요청사항)
          username: '', // 사용자명 (구독 서비스인 경우)
          min: 0,
          max: 0,
          posts: 0,
          delay: 0,
          expiry: '',
          oldPosts: 0
        }
        
        console.log('✅ 주문 데이터 생성 완료:', orderData)

        // 7단계: 주문 데이터 변환
        console.log('🔍 7단계: 주문 데이터 변환')
        console.log('Order Data being sent:', orderData)

        const transformedData = transformOrderData(orderData)
        console.log('Transformed Data:', transformedData)
        
        // 8단계: SMM Panel API 호출
        console.log('🔍 8단계: SMM Panel API 호출')
        console.log('=== 🚀 SMM Panel API 호출 준비 ===')
        
        // API 호출 전 최종 검증
        if (!transformedData.service || transformedData.service === 'undefined') {
          console.error('❌ API 호출 전 서비스 검증 실패:', transformedData)
          alert('서비스 정보가 올바르지 않습니다. 다시 시도해주세요.')
          return
        }
        
        // 사용자 ID 준비
        const userId = currentUser?.uid || currentUser?.email || 'anonymous'
        console.log('사용자 ID:', userId)
        
        // 주문 데이터에 포인트 사용 정보 추가
        transformedData.price = finalPrice // 최종 결제 금액
        transformedData.pointsToUse = pointsToUse // 사용할 포인트
        
        console.log('🎯 최종 SMM Panel API 호출 데이터:', transformedData)
        console.log('API 엔드포인트: smmpanelApi.createOrder')
        
        // SMM Panel API 호출 시도
        let result
        try {
          console.log('📡 SMM Panel API 호출 시작...')
          result = await smmpanelApi.createOrder(transformedData, userId)
          console.log('📡 SMM Panel API 호출 완료')
        } catch (apiError) {
          console.error('❌ SMM Panel API 호출 실패:', apiError)
          
          // API 에러 상세 분석
          if (apiError.response) {
            console.error('SMM Panel API 응답 에러:', {
              status: apiError.response.status,
              data: apiError.response.data,
              headers: apiError.response.headers
            })
            
            // HTTP 상태 코드별 에러 메시지
            switch (apiError.response.status) {
              case 400:
                alert('잘못된 요청입니다. 입력 정보를 확인해주세요.')
                break
              case 401:
                alert('인증이 필요합니다. 로그인 후 다시 시도해주세요.')
                break
              case 403:
                alert('권한이 없습니다. 관리자에게 문의해주세요.')
                break
              case 404:
                alert('요청한 서비스를 찾을 수 없습니다.')
                break
              case 429:
                alert('요청이 너무 많습니다. 잠시 후 다시 시도해주세요.')
                break
              case 500:
                alert('서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')
                break
              default:
                alert(`SMM Panel API 오류가 발생했습니다. (${apiError.response.status})`)
            }
          } else if (apiError.request) {
            console.error('SMM Panel API 요청 에러:', apiError.request)
            alert('SMM Panel 서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.')
          } else {
            console.error('SMM Panel API 설정 에러:', apiError.message)
            alert('SMM Panel 요청 설정 중 오류가 발생했습니다.')
          }
          
          throw apiError
        }

        console.log('✅ 주문 생성 성공:', result)
        
        if (result.error) {
          alert(`주문 생성 실패: ${result.error}`)
        } else {
          // 주문 생성 완료, 포인트는 아직 차감되지 않음
          console.log('🎉 주문 생성 완료, 결제 대기 중:', result)

          // 주문 성공 시 결제 페이지로 이동
          const paymentData = {
            orderId: result.order,
            platform: platform,
            serviceName: services.find(s => s.id === validatedService)?.name || validatedService,
            quantity: quantity,
            unitPrice: platformInfo.unitPrice,
            totalPrice: finalPrice, // 포인트 차감 후 최종 금액
            pointsUsed: pointsToUse, // 사용된 포인트
            originalPrice: totalPrice, // 원래 가격
            link: link.trim(),
            comments: comments.trim(),
            explanation: explanation.trim(),
            discount: getDiscount(quantity)
          }
          
          console.log('💳 결제 데이터:', paymentData)
          console.log('🚀 결제 페이지로 이동 중...')
          
          try {
            // 결제 페이지로 이동하면서 주문 데이터 전달
            navigate(`/payment/${platform}`, { state: { orderData: paymentData } })
          } catch (navigationError) {
            console.error('❌ 네비게이션 에러:', navigationError)
            alert('결제 페이지로 이동 중 오류가 발생했습니다. 다시 시도해주세요.')
          }
        }
      } catch (error) {
        console.error('❌ 주문 생성 중 에러 발생:', error)
        const errorInfo = handleApiError(error)
        console.error('Order creation failed:', errorInfo)
        alert(`주문 생성 실패: ${errorInfo.message}`)
      } finally {
        setIsLoading(false)
      }
    } catch (error) {
      console.error('❌ 전체 주문 프로세스 에러:', error)
      alert('주문 처리 중 오류가 발생했습니다. 다시 시도해주세요.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="order-page">
      <div className="order-header">
        <h1>주문 생성</h1>
        <p>원하는 서비스를 선택하고 주문을 생성하세요</p>
      </div>

      <div className="order-content">
        {/* 플랫폼 선택 */}
        <div className="platform-selection">
          <h2>플랫폼 선택</h2>
          <div className="platform-grid">
            {Object.entries(platforms).map(([key, platform]) => (
              <div
                key={key}
                className={`platform-card ${selectedPlatform === key ? 'selected' : ''}`}
                onClick={() => handlePlatformSelect(key)}
              >
                <div className="platform-icon">
                  <img src={platform.icon} alt={platform.name} />
                </div>
                <div className="platform-info">
                  <h3>{platform.name}</h3>
                  <p>{platform.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 서비스 선택 */}
        {selectedPlatform && (
          <div className="service-selection">
            <h2>서비스 선택</h2>
            <div className="service-grid">
              {services.map((service) => (
                <div
                  key={service.id}
                  className={`service-card ${selectedService === service.id ? 'selected' : ''}`}
                  onClick={() => handleServiceSelect(service.id)}
                >
                  <div className="service-info">
                    <h3>{service.name}</h3>
                    <p>{service.description}</p>
                    <div className="service-price">
                      <span className="price">₩{service.price.toLocaleString()}</span>
                      <span className="per-1000">/1,000</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 주문 폼 */}
        {selectedService && (
          <div className="order-form">
            <h2>주문 정보 입력</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="link">링크</label>
                <input
                  type="url"
                  id="link"
                  value={link}
                  onChange={(e) => setLink(e.target.value)}
                  placeholder="https://..."
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="quantity">수량</label>
                <input
                  type="number"
                  id="quantity"
                  value={quantity}
                  onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
                  min="1"
                  required
                />
                <div className="quantity-info">
                  <span>최소: {platformInfo?.minQuantity || 1}</span>
                  <span>최대: {platformInfo?.maxQuantity || 100000}</span>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="comments">코멘트 (선택사항)</label>
                <textarea
                  id="comments"
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="원하는 코멘트를 입력하세요..."
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label htmlFor="explanation">설명 (선택사항)</label>
                <textarea
                  id="explanation"
                  value={explanation}
                  onChange={(e) => setExplanation(e.target.value)}
                  placeholder="추가 설명이 필요하다면 입력하세요..."
                  rows="3"
                />
              </div>

              {/* 포인트 사용 */}
              <div className="points-section">
                <h3>포인트 사용</h3>
                <div className="points-info">
                  <span>보유 포인트: {userPoints?.toLocaleString() || 0}점</span>
                  <span>주문 금액: ₩{totalPrice.toLocaleString()}</span>
                </div>
                <div className="points-input">
                  <input
                    type="number"
                    value={pointsToUse}
                    onChange={(e) => setPointsToUse(parseInt(e.target.value) || 0)}
                    min="0"
                    max={Math.min(userPoints || 0, totalPrice)}
                    placeholder="사용할 포인트"
                  />
                  <button
                    type="button"
                    onClick={() => setPointsToUse(Math.min(userPoints || 0, totalPrice))}
                    className="btn-max-points"
                  >
                    최대 사용
                  </button>
                </div>
                <div className="final-price">
                  <span>최종 결제 금액:</span>
                  <span className="price">₩{finalPrice.toLocaleString()}</span>
                </div>
              </div>

              <button
                type="submit"
                className="btn-submit"
                disabled={isLoading}
              >
                {isLoading ? '주문 생성 중...' : '주문 생성'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}

export default OrderPage