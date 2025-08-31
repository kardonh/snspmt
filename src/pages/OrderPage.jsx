import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ShoppingBag, ChevronDown, Star } from 'lucide-react'
import { getPlatformInfo, calculatePrice } from '../utils/platformUtils'
import { smmkingsApi, handleApiError, transformOrderData } from '../services/snspopApi'
import { useAuth } from '../contexts/AuthContext'
import './OrderPage.css'

// Force redeploy - Prevent rollback and fix deployment issues
// 강제 재배포 - 롤백 방지 및 배포 문제 해결
const OrderPage = () => {
  const { platform, serviceId } = useParams()
  const navigate = useNavigate()
  const { currentUser } = useAuth()
  const [selectedService, setSelectedService] = useState(serviceId || 'followers_korean')
  
  // 디버깅: 서비스 ID 확인
  useEffect(() => {
    console.log('=== OrderPage 디버깅 ===')
    console.log('URL 파라미터:', { platform, serviceId })
    console.log('초기 selectedService:', selectedService)
    console.log('사용 가능한 서비스:', services)
  }, [platform, serviceId, selectedService, services])
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
  
  // 포인트 로드
  const loadUserPoints = async () => {
    if (currentUser) {
      try {
        const response = await smmkingsApi.getUserPoints(currentUser.uid)
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
          return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 150000, 200000, 250000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1500000, 2000000, 2500000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000]
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
  
      const handlePurchase = async () => {
    // 포인트 검증
    if (usePoints && userPoints < totalPrice) {
      handleInsufficientPoints()
      return
    }

    // 입력 검증
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

      // 서비스 선택 검증 추가
      if (!selectedService || selectedService === 'undefined') {
        console.error('서비스가 선택되지 않음:', { selectedService, serviceId, platform })
        alert('주문할 서비스를 선택해주세요.')
        return
      }
      
      setIsLoading(true)
      
      try {
        // 올바른 서비스 ID 가져오기
        const serviceId = serviceIdMapping[platform]?.[selectedService]
        
        console.log('Platform:', platform)
        console.log('Selected Service:', selectedService)
        console.log('Service ID Mapping:', serviceIdMapping[platform])
        console.log('Selected Service ID:', serviceId)
        
        if (!serviceId) {
          console.error('서비스 ID 매핑 실패:', { platform, selectedService, serviceIdMapping })
          alert('지원하지 않는 서비스입니다.')
          return
        }

      const orderData = {
        serviceId,
          link: link.trim(),
        quantity,
        runs: 1, // 기본 실행 횟수
        interval: 0, // 즉시 실행
          comments: comments.trim(), // 커스텀 댓글 (댓글 서비스인 경우)
          explanation: explanation.trim(), // 설명 (추가 요청사항)
        username: '', // 사용자명 (구독 서비스인 경우)
        min: 0,
        max: 0,
        posts: 0,
        delay: 0,
        expiry: '',
        oldPosts: 0
      }

        console.log('Order Data being sent:', orderData)

      const transformedData = transformOrderData(orderData)
        console.log('Transformed Data:', transformedData)
        
      const userId = currentUser?.uid || currentUser?.email || 'anonymous'
      const result = await smmkingsApi.createOrder(transformedData, userId)

      console.log('Order created successfully:', result)
      
      if (result.error) {
        alert(`주문 생성 실패: ${result.error}`)
      } else {
        // 포인트 사용 시 포인트 차감
        if (usePoints && pointsToUse > 0) {
          try {
            const userId = currentUser?.uid || currentUser?.email || 'anonymous'
            const deductResult = await smmkingsApi.deductUserPoints(userId, pointsToUse)
            
            if (deductResult.success) {
              console.log('포인트 차감 성공:', deductResult)
              // 포인트 잔액 업데이트
              setUserPoints(deductResult.remainingPoints)
            } else {
              console.error('포인트 차감 실패:', deductResult)
              alert('포인트 차감에 실패했습니다.')
              return
            }
          } catch (error) {
            console.error('포인트 차감 중 오류:', error)
            alert('포인트 차감 중 오류가 발생했습니다.')
            return
          }
        }

        // 주문 성공 시 결제 페이지로 이동
        const paymentData = {
          orderId: result.order,
          platform: platform,
          serviceName: services.find(s => s.id === selectedService)?.name || selectedService,
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
        
        console.log('Payment data:', paymentData)
        console.log('Navigating to payment page...')
        
        try {
          // 결제 페이지로 이동하면서 주문 데이터 전달
          navigate(`/payment/${platform}`, { state: { orderData: paymentData } })
        } catch (navigationError) {
          console.error('Navigation error:', navigationError)
          alert('결제 페이지로 이동 중 오류가 발생했습니다. 다시 시도해주세요.')
        }
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
    try {
      // 장바구니 기능은 snspop API에 없으므로 로컬 스토리지에 저장
      const cartItem = {
        id: Date.now(),
        platform,
        service: selectedService,
        quantity,
        unitPrice: platformInfo.unitPrice,
        totalPrice,
        timestamp: new Date().toISOString()
      }

      const existingCart = JSON.parse(localStorage.getItem('snspop_cart') || '[]')
      existingCart.push(cartItem)
      localStorage.setItem('snspop_cart', JSON.stringify(existingCart))

      console.log('Added to cart successfully:', cartItem)
      alert('장바구니에 추가되었습니다!')
    } catch (error) {
      console.error('Add to cart failed:', error)
      alert('장바구니 추가 실패')
    }
  }

  return (
    <div className="order-page">
      <div className="order-header">
        <h1>{platformInfo.name} 서비스 주문</h1>
      </div>
      
      <div className="order-sections">
        {/* Section 1: Product Selection */}
        <section className="order-section">
          <h2>1 주문할 {platformInfo.name} 상품을 선택해 주세요</h2>
          <div className="service-buttons">
            {services.map(service => (
              <button
                key={service.id}
                className={`service-btn ${selectedService === service.id ? 'active' : ''}`}
                onClick={() => setSelectedService(service.id)}
              >
                {service.name}
              </button>
            ))}
          </div>
          <div className="product-intro">
            <h3>상품 소개</h3>
            <p>{services.find(s => s.id === selectedService)?.description}</p>
          </div>
        </section>
        
        {/* Section 2: Quantity Selection */}
        <section className="order-section">
          <h2>2 개수를 선택해 주세요</h2>
          <div className="quantity-selection">
            <div className="quantity-grid">
              {quantityOptions.map(option => (
                <button
                  key={option}
                  className={`quantity-option ${quantity === option ? 'selected' : ''}`}
                  onClick={() => handleQuantityChange(option)}
                >
                  {option.toLocaleString()}개
                </button>
              ))}
            </div>
          </div>
          <div className="quantity-info">
                  <p>수량 선택 가능</p>
            <p>1개당 {platformInfo.unitPrice}원</p>
                  {platform === 'instagram' && (
                    <div className="quantity-limit-notice">
                      {selectedService === 'followers_foreign' && (
                        <p>⚠️ 외국인 팔로워: 100개~2000개</p>
                      )}
                      {selectedService === 'followers_korean' && (
                        <p>⚠️ 한국인 팔로워: 50개~20000개</p>
                      )}
                      {selectedService === 'likes_foreign' && (
                        <p>⚠️ 외국인 좋아요: 100개~50000개</p>
                      )}
                      {selectedService === 'likes_korean' && (
                        <p>⚠️ 한국인 좋아요: 50개~10000개</p>
                      )}
                      {selectedService === 'comments_korean' && (
                        <p>⚠️ 한국인 랜덤 댓글: 5개~100개</p>
                      )}
                      {selectedService === 'comments_foreign' && (
                        <p>⚠️ 외국인 랜덤 댓글: 10개~1000개</p>
                      )}
                      {selectedService === 'views_korean' && (
                        <p>⚠️ 한국인 조회수: 100개~100,000,000개</p>
                      )}
                      {selectedService === 'views_foreign' && (
                        <p>⚠️ 외국인 조회수: 100개~100,000,000개</p>
                      )}
                    </div>
                  )}
                  {platform === 'youtube' && (
                    <div className="quantity-limit-notice">
                      {selectedService === 'followers_foreign' && (
                        <p>⚠️ 외국인 구독자: 100개</p>
                      )}
                      {selectedService === 'followers_korean' && (
                        <p>⚠️ 리얼 한국인 구독자: 50개~1000개</p>
                      )}
                      {selectedService === 'likes_foreign' && (
                        <p>⚠️ 외국인 좋아요: 100개~5000개</p>
                      )}
                      {selectedService === 'comments_korean' && (
                        <p>⚠️ AI 랜덤 한국인 댓글: 10개~10000개</p>
                      )}
                      {selectedService === 'views_foreign' && (
                        <p>⚠️ 외국인 조회수: 100개~10,000,000개</p>
                      )}
                      {selectedService === 'views_korean' && (
                        <p>⚠️ 리얼 한국인 조회수: 4000개~100,000개</p>
                      )}
                    </div>
                  )}
                  {platform === 'tiktok' && (
                    <div className="quantity-limit-notice">
                      {selectedService === 'likes_foreign' && (
                        <p>⚠️ 외국인 좋아요: 100개~100,000개</p>
                      )}
                      {selectedService === 'followers_foreign' && (
                        <p>⚠️ 외국인 계정 팔로워: 100개~1,000,000개</p>
                      )}
                      {selectedService === 'views_foreign' && (
                        <p>⚠️ 외국인 조회수: 100개~2,000,000,000개</p>
                      )}
                      {selectedService === 'comments_foreign' && (
                        <p>⚠️ 외국인 랜덤 댓글: 10개~2,000개</p>
                      )}
                    </div>
                  )}
                                     {platform === 'facebook' && (
                     <div className="quantity-limit-notice">
                       {selectedService === 'followers_korean' && (
                         <p>⚠️ 개인계정 팔로우: 5개~2,500개</p>
                       )}
                       {selectedService === 'followers_foreign' && (
                         <p>⚠️ 프로필 팔로우: 100개~1,000,000개</p>
                       )}
                       {selectedService === 'likes_korean' && (
                         <p>⚠️ 게시물 좋아요 (리얼 한국인): 20개~10,000개</p>
                       )}
                       {selectedService === 'likes_foreign' && (
                         <p>⚠️ 게시물 좋아요 (외국인): 100개~100,000개</p>
                       )}
                       {selectedService === 'comments_korean' && (
                         <p>⚠️ 게시물 랜덤 댓글 (한국인): 10개~10,000개</p>
                       )}
                     </div>
                   )}
                  {platform === 'twitter' && (
                    <div className="quantity-limit-notice">
                      {selectedService === 'followers_real' && (
                        <p>⚠️ 리얼 팔로워: 100개~200,000개</p>
                      )}
                    </div>
                  )}
                  {platform === 'kakaotalk' && (
                    <div className="quantity-limit-notice">
                      {selectedService === 'friends_real' && (
                        <p>⚠️ 리얼 채널 친구 추가: 100개~10,000개</p>
                      )}
                    </div>
                  )}
          </div>
          <div className="discount-info">
            <h3>할인 혜택</h3>
            {discountTiers.map(tier => (
              <p key={tier.min}>
                {tier.min.toLocaleString()}개 - {tier.max.toLocaleString()}개: {tier.discount}% 할인
              </p>
            ))}
          </div>
          <div className="total-price">
            <h3>총 금액</h3>
            <p className="price">{totalPrice.toLocaleString()}원</p>
            {getDiscount(quantity) > 0 && (
              <p className="discount-applied">{getDiscount(quantity)}% 할인 적용</p>
            )}
          </div>
        </section>
        
        {/* Section 3: Link Input */}
        <section className="order-section">
          <h2>3 링크를 입력해 주세요</h2>
          <div className="link-input">
            <input
              type="url"
              value={link}
              onChange={(e) => setLink(e.target.value)}
              placeholder={`${platformInfo.name} 게시물 URL 또는 사용자명을 입력하세요`}
              className="link-input-field"
            />
          </div>
          <div className="link-info">
            {platform === 'instagram' && (
              <p>예시: https://www.instagram.com/p/XXXXX/ (게시물) 또는 @username (사용자명)</p>
            )}
            {platform === 'youtube' && (
              <p>예시: https://www.youtube.com/watch?v=XXXXX (동영상) 또는 채널명</p>
            )}
            {platform === 'tiktok' && (
              <p>예시: https://www.tiktok.com/@username/video/XXXXX (동영상) 또는 @username (사용자명)</p>
            )}
          </div>
        </section>

        {/* Section 4: Comments Input (for comment service) */}
        {((platform === 'instagram' && (selectedService === 'comments_korean' || selectedService === 'comments_foreign')) || 
          (platform === 'youtube' && selectedService === 'comments_korean') ||
          (platform === 'facebook' && selectedService === 'comments_korean') ||
          (platform === 'tiktok' && selectedService === 'comments_foreign')) && (
          <section className="order-section">
            <h2>4 댓글 내용을 입력해 주세요</h2>
            <div className="comments-input">
              <textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="댓글 내용을 입력하세요 (최대 200자)"
                maxLength="200"
                className="comments-textarea"
                rows="4"
              />
              <div className="char-count">
                {comments.length}/200
              </div>
            </div>
          </section>
        )}

        {/* Section 5: Explanation Input */}
        <section className="order-section">
          <h2>5 추가 요청사항을 입력해 주세요</h2>
          <div className="explanation-input">
            <textarea
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder="추가 요청사항이나 특별한 요구사항이 있으시면 입력해주세요 (선택사항)"
              maxLength="500"
              className="explanation-textarea"
              rows="4"
            />
            <div className="char-count">
              {explanation.length}/500
            </div>
          </div>
        </section>

        {/* Section 5.5: Points Usage */}
        <section className="order-section">
          <h2>6 포인트 사용</h2>
          <div className="points-usage">
            <div className="points-info">
              <div className="current-points">
                <span>현재 포인트: {userPoints.toLocaleString()}P</span>
              </div>
              <div className="points-toggle">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={usePoints}
                    onChange={(e) => setUsePoints(e.target.checked)}
                    className="toggle-input"
                  />
                  <span className="toggle-slider"></span>
                  포인트 사용
                </label>
              </div>
            </div>
            
            {usePoints && (
              <div className="points-details">
                <div className="price-breakdown">
                  <div className="price-item">
                    <span>상품 가격:</span>
                    <span>{totalPrice.toLocaleString()}원</span>
                  </div>
                  <div className="price-item">
                    <span>사용할 포인트:</span>
                    <span>-{pointsToUse.toLocaleString()}P</span>
                  </div>
                  <div className="price-item final-price">
                    <span>최종 결제 금액:</span>
                    <span>{finalPrice.toLocaleString()}원</span>
                  </div>
                </div>
                
                {userPoints < totalPrice && (
                  <div className="insufficient-points">
                    <p>⚠️ 포인트가 부족합니다. {totalPrice - userPoints}P가 더 필요합니다.</p>
                    <button 
                      onClick={handleInsufficientPoints}
                      className="charge-points-btn"
                    >
                      포인트 충전하기
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
        
        {/* Section 7: Pre-order Checklist */}
        <section className="order-section">
          <h2 
            className="checklist-header"
            onClick={() => setShowChecklist(!showChecklist)}
          >
            7 주문 전 체크사항 꼭 읽어주세요
            <ChevronDown className={`chevron ${showChecklist ? 'rotated' : ''}`} />
          </h2>
          {showChecklist && (
            <div className="checklist-content">
              <ul>
                <li>주문하신 계정 정보가 정확한지 확인해주세요</li>
                <li>서비스 시작 후에는 취소가 불가능합니다</li>
                <li>서비스 완료까지 24-48시간이 소요될 수 있습니다</li>
                <li>문의사항이 있으시면 고객센터로 연락해주세요</li>
              </ul>
            </div>
          )}
        </section>
        

        
        {/* Customer Reviews */}
        <section className="reviews-section">
          <div className="reviews-header">
            <h3>146개의 실제 고객 후기</h3>
            <div className="rating">
              <span className="stars">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} size={20} fill="#FFD700" />
                ))}
              </span>
              <span className="rating-score">5.0</span>
            </div>
          </div>
          <div className="review-example">
            <p>"아주빠릅니다."</p>
            <span className="review-date">2025.08.07</span>
          </div>
        </section>
      </div>
      
      {/* Bottom Action Bar */}
      <div className="bottom-action-bar">
        <button className="cart-btn" onClick={handleAddToCart}>
          <ShoppingBag size={20} />
          장바구니
        </button>
        <button 
          className="purchase-btn" 
          onClick={handlePurchase}
          disabled={isLoading}
        >
          {isLoading ? '처리 중...' : '구매하기'}
        </button>
      </div>
    </div>
  )
}

export default OrderPage
