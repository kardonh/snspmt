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
import { snspopApi, handleApiError, transformOrderData } from '../services/snspopApi'
import './Home.css'

const Home = () => {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const [selectedPlatform, setSelectedPlatform] = useState('instagram')
  const [selectedServiceType, setSelectedServiceType] = useState('recommended')
  const [selectedService, setSelectedService] = useState('followers_korean')
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
    { id: 'naver', name: 'N포털', icon: Globe, color: '#03c75a', description: 'N포털 서비스' },
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
          { id: 'followers_korean', name: '팔로워 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 100/20,000개 | 1개당 120원 | 리필불가 | ✴️ 인스타그램 업데이트로 인해 검토를 위한 플래그 지정을 꺼주세요 (설정 > 친구 팔로우 및 초대 > 검토를 위해 플래그 지정 끄기) | ✴️ 하루 약 500~1000명 팔로워 증가 | ✴️ 한국인 프로필 유저들로 유입되어 언팔에 의한 이탈 없음 | ✴️ 한국 시장에서의 신뢰도 및 인지도 향상 | ✴️ 인스타그램 인플루언서 프로그램 참여 자격 획득 가능 | ✴️ 브랜드 협업 및 수익화 기회 확대 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | ✴️ 계정 권위성 및 신뢰도 향상 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'followers_foreign', name: '팔로워 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200명 | 최소/최대: 100/2,000개 | 1개당 1원 | 리필불가 | ✴️ 인스타그램 업데이트로 인해 검토를 위한 플래그 지정을 꺼주세요 (설정 > 친구 팔로우 및 초대 > 검토를 위해 플래그 지정 끄기) | ✴️ 하루 약 500~1000명 팔로워 증가 | ✴️ 글로벌 팔로워로 구성되어 국제적인 영향력 향상 | ✴️ 국제 시장에서의 브랜드 인지도 향상 | ✴️ 다국어 콘텐츠로 글로벌 시장 공략 가능 | ✴️ 인스타그램 인플루언서 프로그램 참여 자격 획득 가능 | ✴️ 브랜드 협업 및 수익화 기회 확대 | ✴️ 계정 권위성 및 신뢰도 향상 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'likes_korean', name: '좋아요 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 50/10,000개 | 1개당 7원 | 리필불가 | ✴️ 한국인 사용자로부터 좋아요를 받아 게시물의 인기도 향상 | ✴️ 자연스러운 한국어 사용자로 구성 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 댓글 및 공유 가능성 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 50명 단위 주문 가능' },
          { id: 'likes_foreign', name: '좋아요 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/50,000개 | 1개당 1원 | 리필불가 | ✴️ 외국인 사용자로부터 좋아요를 받아 게시물의 인기도 향상 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 국제 시장에서의 콘텐츠 인기도 향상 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 다국어 댓글 및 공유 가능성 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 글로벌 브랜드 인지도 및 신뢰도 향상 | ✴️ 해시태그 트렌딩 효과로 바이럴 확산 가능성 증대 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'comments_korean', name: '댓글 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 5/100개 | 1개당 200원 | 리필불가 | ✴️ 한국어 댓글을 달아 게시물의 상호작용 증가 | ✴️ 커스텀 댓글 입력 가능 | ✴️ 자연스러운 한국어 사용자로 구성 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 댓글을 통한 추가 상호작용 유도 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | ✴️ 게시물 노출도 및 상호작용 증가 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 5명 단위 주문 가능' },
          { id: 'comments_foreign', name: '댓글 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 10/1,000개 | 1개당 50원 | 리필불가 | ✴️ 외국어 댓글을 달아 게시물의 상호작용 증가 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 국제 시장에서의 콘텐츠 인기도 향상 | ✴️ 다국어 댓글로 국제적 소통 증대 | ✴️ 게시물 노출도 및 상호작용 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 글로벌 브랜드 인지도 및 신뢰도 향상 | ✴️ 해시태그 트렌딩 효과로 바이럴 확산 가능성 증대 | ✴️ 지역별 타겟팅으로 특정 국가 시장 공략 가능 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 10명 단위 주문 가능' },
          { id: 'views_korean', name: '조회수 (한국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/100,000,000개 | 1개당 1원 | 리필불가 | ✴️ 한국인 사용자로부터 조회수를 증가시켜 콘텐츠의 노출도 향상 | ✴️ 자연스러운 한국어 사용자로 구성 | ✴️ 한국 시장에서의 콘텐츠 인기도 향상 | ✴️ 스토리 및 릴스 노출도 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 한국 시장 공략 가능 | ✴️ 스토리 광고 및 브랜드 협업 기회 확대 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' },
          { id: 'views_foreign', name: '조회수 (외국인)', description: '품질: 고품질 | 시작시간: 5분 | 하루유입량: 100~200개 | 최소/최대: 100/100,000,000개 | 1개당 0.5원 | 리필불가 | ✴️ 외국인 사용자로부터 조회수를 증가시켜 콘텐츠의 노출도 향상 | ✴️ 글로벌 사용자로 구성되어 국제적인 영향력 향상 | ✴️ 국제 시장에서의 콘텐츠 인기도 향상 | ✴️ 스토리 및 릴스 노출도 증가 | ✴️ 인스타그램 알고리즘에서 우선순위 상승 | ✴️ 글로벌 브랜드 인지도 및 신뢰도 향상 | ✴️ 지역별 타겟팅으로 특정 국가 시장 공략 가능 | ✴️ 해시태그 트렌딩 효과로 바이럴 확산 가능성 증대 | ✴️ 스토리 광고 및 브랜드 협업 기회 확대 | 계정공개 필수, 비공개 계정 작업 불가 | 주문접수 후 취소/변경/환불 불가 | 100명 단위 주문 가능' }
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
      case 'naver':
        return [
          { id: 'under_development', name: '제작중', description: '현재 서비스 개발 중입니다. 곧 새로운 서비스로 찾아뵙겠습니다.' }
        ]
      case 'threads':
        return [
          { id: 'threads_service', name: '스레드 서비스', description: '스레드 플랫폼 서비스입니다.' }
        ]
      case 'news-media':
        return [
          { id: 'news_service', name: '뉴스 언론 보도', description: '뉴스 언론 보도 서비스입니다.' }
        ]
      case 'experience-group':
        return [
          { id: 'experience_service', name: '체험단 서비스', description: '체험단 서비스입니다.' }
        ]
      case 'kakao':
        return [
          { id: 'kakao_service', name: '카카오 서비스', description: '카카오 플랫폼 서비스입니다.' }
        ]
      case 'store-marketing':
        return [
          { id: 'store_service', name: '스토어 마케팅', description: '스토어 마케팅 서비스입니다.' }
        ]
      case 'app-marketing':
        return [
          { id: 'app_service', name: '앱 마케팅', description: '앱 마케팅 서비스입니다.' }
        ]
      case 'seo-traffic':
        return [
          { id: 'seo_service', name: 'SEO 트래픽', description: 'SEO 트래픽 서비스입니다.' }
        ]
      case 'other':
        return [
          { id: 'other_service', name: '기타 서비스', description: '기타 서비스입니다.' }
        ]
      case 'recommended':
      case 'event':
      case 'top-exposure':
      case 'account-management':
      case 'package':
        return [
          { id: 'general_service', name: '일반 서비스', description: '일반적인 서비스입니다.' }
        ]
      default:
        return [
          { id: 'default_service', name: '기본 서비스', description: '선택된 플랫폼에 대한 기본 서비스입니다.' }
        ]
    }
  }

  const platformInfo = getPlatformInfo(selectedPlatform)
  const services = getServicesForPlatform(selectedPlatform)

  // snspop API 서비스 ID 매핑
  const serviceIdMapping = {
    instagram: {
      followers_korean: 577,
      followers_foreign: 855,
      likes_korean: 790,
      likes_foreign: 458,
      comments_korean: 841,
      comments_foreign: 645,
      views_korean: 619,
      views_foreign: 791
    },
    youtube: {
      followers_foreign: 150,
      followers_korean: 872,
      likes_foreign: 638,
      comments_korean: 869,
      views_foreign: 833,
      views_korean: 731
    }
  }

  // 수량 옵션 생성
  const getQuantityOptions = (platform, service) => {
    if (platform === 'instagram') {
      switch (service) {
        case 'followers_foreign': return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000]
        case 'followers_korean': return [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000]
        case 'likes_foreign': return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000]
        case 'likes_korean': return [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        case 'comments_korean': return [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100]
        case 'comments_foreign': return [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
        default: return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
      }
    } else if (platform === 'youtube') {
      switch (service) {
        case 'followers_foreign': return [100]
        case 'followers_korean': return [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        case 'likes_foreign': return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000]
        case 'comments_korean': return [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        case 'views_foreign': return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 150000, 200000, 250000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1500000, 2000000, 2500000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000]
        case 'views_korean': return [4000, 5000, 6000, 7000, 8000, 9000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]
        default: return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
      }
    } else if (platform === 'naver') {
      return [1] // 제작중이므로 수량 옵션을 1개로 제한
    } else if (['recommended', 'event', 'top-exposure', 'account-management', 'package', 'other', 'threads', 'news-media', 'experience-group', 'kakao', 'store-marketing', 'app-marketing', 'seo-traffic'].includes(platform)) {
      return [1, 5, 10, 20, 50, 100] // 서비스 유형들은 기본 수량 옵션
    }
    return [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
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

  // 가격 계산
  useEffect(() => {
    const price = calculatePrice(selectedService, quantity, selectedPlatform)
    setTotalPrice(price)
  }, [selectedService, quantity, selectedPlatform])

  const handlePlatformSelect = (platformId) => {
    setSelectedPlatform(platformId)
    setSelectedServiceType('recommended')
    
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
    const newQuantityOptions = getQuantityOptions(selectedPlatform, serviceId)
    if (!newQuantityOptions.includes(quantity)) {
      setQuantity(newQuantityOptions[0])
    }
  }

  const handleQuantityChange = (newQuantity) => {
    setQuantity(newQuantity)
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
      const serviceId = serviceIdMapping[selectedPlatform]?.[selectedService]
      
      if (!serviceId) {
        alert('지원하지 않는 서비스입니다.')
        return
      }

      const orderData = {
        serviceId,
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
      const result = await snspopApi.createOrder(transformedData, userId)

      if (result.error) {
        alert(`주문 생성 실패: ${result.error}`)
      } else {
        const paymentData = {
          orderId: result.order,
          platform: selectedPlatform,
          serviceName: services.find(s => s.id === selectedService)?.name || selectedService,
          quantity: quantity,
          unitPrice: platformInfo.unitPrice,
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
        quantity,
        unitPrice: platformInfo.unitPrice,
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
        <h3>세부 서비스를 선택해주세요</h3>
        
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
      
                {/* Order Form */}
      {selectedService && (
        <div className="order-form">
          <h3>주문 정보 입력</h3>
          
          {/* Service Description */}
          <div className="service-description">
            <h4>선택된 서비스</h4>
            <p>{services.find(s => s.id === selectedService)?.description}</p>
          </div>
          
          {/* Quantity Selection */}
          <div className="form-group">
            <label>수량 선택</label>
            <div className="quantity-controls">
              <button 
                className="quantity-btn" 
                onClick={() => {
                  const currentIndex = quantityOptions.indexOf(quantity)
                  if (currentIndex > 0) {
                    handleQuantityChange(quantityOptions[currentIndex - 1])
                  }
                }}
                disabled={quantityOptions.indexOf(quantity) === 0}
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
                  const currentIndex = quantityOptions.indexOf(quantity)
                  if (currentIndex < quantityOptions.length - 1) {
                    handleQuantityChange(quantityOptions[currentIndex + 1])
                  }
                }}
                disabled={quantityOptions.indexOf(quantity) === quantityOptions.length - 1}
              >
                +
              </button>
                  </div>
            <div className="quantity-info">
              <p>1개당 {platformInfo.unitPrice}원</p>
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
