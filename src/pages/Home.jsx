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
  Sparkles
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { smmpanelApi, transformOrderData } from '../services/snspopApi'
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

  // 컴포넌트 마운트 시 기본 서비스 자동 선택
  useEffect(() => {
    if (selectedPlatform && selectedService && !selectedDetailedService) {
      const detailedServices = getDetailedServices(selectedPlatform, selectedService)
      if (detailedServices && detailedServices.length > 0) {
        setSelectedDetailedService(detailedServices[0])
        setQuantity(detailedServices[0].min)
      }
    }
  }, [selectedPlatform, selectedService, selectedDetailedService])

  // 인스타그램 세부 서비스 데이터
  const instagramDetailedServices = {
    popular_posts: [
      // 🎯 새로운 묶음 서비스 - 추천탭 상위노출 (셀프) - 진입단계
      { id: 1001, name: '🎯 추천탭 상위노출 (셀프) - 진입단계 [4단계 패키지]', price: 6610, min: 1, max: 1, time: '24-48시간', description: '진입단계 4단계 완전 패키지', package: true, steps: [
        { id: 122, name: '1단계: 실제 한국인 게시물 좋아요 [진입 단계]', price: 1800, quantity: 300, description: '🇰🇷 인스타그램 한국인 💎💎파워업 좋아요💖💖[💪인.게 최적화↑]' },
        { id: 329, name: '2단계: 파워 게시물 노출 + 도달 + 기타 유입', price: 3000, quantity: 10000, description: '5️⃣:[등록단계]파워게시물 노출 + 도달 + 홈 유입' },
        { id: 328, name: '3단계: 파워 게시물 저장 유입', price: 210, quantity: 1000, description: '4️⃣[등록단계]파워 게시물 저장 유입' },
        { id: 326, name: '4단계: 리얼 한국인 댓글 유입', price: 1600, quantity: 10, description: '2️⃣[상승단계] 리얼 한국인 댓글 유입' }
      ]},
      // 🎯 새로운 묶음 서비스 - 추천탭 상위노출 (셀프) - 유지단계  
      { id: 1002, name: '🎯 추천탭 상위노출 (셀프) - 유지단계 [2단계 패키지]', price: 3250, min: 1, max: 1, time: '12-24시간', description: '유지단계 2단계 완전 패키지', package: true, steps: [
        { id: 325, name: '1단계: 실제 한국인 게시물 좋아요 [진입 단계]', price: 3250, quantity: 250, description: '[상승단계]:리얼 한국인 좋아요' },
        { id: 331, name: '2단계: 게시물 노출+도달+홈 [✔연속 유입]', price: 0, quantity: 0, description: '게시물 노출+도달+홈 [✔연속 유입] 작업' }
      ]},
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
    likes_korean: [
      { id: 122, name: '🇰🇷 인스타그램 한국인 ❤️ 파워업 좋아요', price: 19, min: 30, max: 2500, time: '14시간 54분', description: '상세정보' },
      { id: 333, name: '🇰🇷 인스타그램 한국인 ❤️ 슈퍼프리미엄 좋아요', price: 29, min: 100, max: 1000, time: '데이터 부족', description: '상세정보' },
      { id: 275, name: '🇰🇷 인스타그램 한국인 ❤️ 좋아요 [남성]', price: 29, min: 30, max: 5000, time: '10분', description: '상세정보' },
      { id: 276, name: '🇰🇷 인스타그램 한국인 ❤️ 좋아요 [여성]', price: 29, min: 30, max: 5000, time: '9분', description: '상세정보' },
      { id: 277, name: '🇰🇷 인스타그램 한국인 ❤️ 좋아요 [20대]', price: 29, min: 30, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 279, name: '🇰🇷 인스타그램 한국인 ❤️ 좋아요 [20대남성]', price: 39, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 280, name: '🇰🇷 인스타그램 한국인 ❤️ 좋아요 [20대여성]', price: 39, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 278, name: '🇰🇷 인스타그램 한국인 ❤️ 좋아요 [30대]', price: 29, min: 30, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 281, name: '🇰🇷 인스타그램 한국인 ❤️ 좋아요 [30대남성]', price: 39, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 282, name: '🇰🇷 인스타그램 한국인 ❤️ 좋아요 [30대여성]', price: 39, min: 30, max: 2500, time: '데이터 부족', description: '상세정보' }
     ],
    likes_foreign: [
      { id: 116, name: '440 [🥇추천]인스타그램 리얼 외국인 좋아요💖[저속][업데이트서버_08월_18일]', price: 1200, min: 100, max: 100000, time: '5 시간 7 분' }
    ],
    followers_korean: [
      { id: 514, name: '🇰🇷 💯 리얼 한국인 팔로워 [일반]', price: 150, min: 30, max: 3000, time: '2시간 16분', description: '상세정보' },
      { id: 491, name: '🇰🇷 💯 리얼 한국인 팔로워 [디럭스]', price: 210, min: 10, max: 1000, time: '데이터 부족', description: '상세정보' },
      { id: 334, name: '🇰🇷 💯 리얼 한국인 팔로워 [프리미엄]', price: 270, min: 10, max: 40000, time: '1시간 3분', description: '상세정보' }
    ],
    views: [
      { id: 111, name: '🇰🇷인스타그램 한국인 동영상 조회수', price: 2, min: 100, max: 2147483647, time: '20시간 33분', description: '상세정보' },
      { id: 374, name: '🇰🇷인스타그램 한국인 노출(+도달+기타)', price: 8, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' },
      { id: 141, name: '🇰🇷인스타그램 한국인 저장', price: 40, min: 10, max: 1000000, time: '2분', description: '상세정보' },
      { id: 305, name: '🇰🇷 인스타그램 한국인 리그램', price: 450, min: 3, max: 3000, time: '6시간 12분', description: '상세정보' }
    ],
    comments_korean: [
      { id: 296, name: '🇰🇷 인스타그램 한국인 랜덤 댓글 [일반]', price: 260, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 297, name: '🇰🇷 인스타그램 한국인 랜덤 댓글 [여성]', price: 400, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 298, name: '🇰🇷 인스타그램 한국인 랜덤 댓글 [남성]', price: 400, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 299, name: '🇰🇷 인스타그램 한국인 랜덤 댓글 [20대]', price: 260, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 300, name: '🇰🇷 인스타그램 한국인 랜덤 댓글 [20대남성]', price: 400, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 301, name: '🇰🇷 인스타그램 한국인 랜덤 댓글 [20대여성]', price: 400, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 302, name: '🇰🇷 인스타그램 한국인 랜덤 댓글 [30대남성]', price: 400, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 303, name: '🇰🇷 인스타그램 한국인 랜덤 댓글 [30대여성]', price: 400, min: 5, max: 2500, time: '데이터 부족', description: '상세정보' },
      { id: 291, name: '🇰🇷 인스타그램 한국인 이모지 댓글', price: 260, min: 5, max: 1000, time: '데이터 부족', description: '상세정보' },
      { id: 339, name: '🇰🇷 인스타그램 한국인 커스텀 댓글 [일반]', price: 400, min: 5, max: 500, time: '6분', description: '상세정보' },
      { id: 340, name: '🇰🇷 인스타그램 한국인 커스텀 댓글 [남성]', price: 500, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
      { id: 341, name: '🇰🇷 인스타그램 한국인 커스텀 댓글 [여성]', price: 500, min: 5, max: 500, time: '6분', description: '상세정보' }
    ],
    regram_korean: [
      { id: 305, name: '🇰🇷 인스타그램 한국인 리그램🎯', price: 375000, min: 3, max: 3000, time: '7 시간 21 분' }
    ],
    followers_foreign: [
      { id: 475, name: '외국인 팔로워', price: 7500, min: 100, max: 20000, time: '15 시간 39 분' }
    ],
    exposure_save_share: [
      { id: 490, name: '🇰🇷인스타그램 리얼 한국인 스토리 공유🔗', price: 600000, min: 3, max: 500, time: '데이터가 충분하지 않습니다' },
      { id: 142, name: '🌐인스타그램 노출👣[+도달+기타][좋아요x]', price: 330, min: 100, max: 1000000, time: '22 분' },
      { id: 145, name: '🌐인스타그램 노출👣[+도달+홈+프로필+기타][좋아요x]', price: 900, min: 10, max: 1000000, time: '77 시간 42 분' },
      { id: 374, name: '🇰🇷인스타그램 한국인 노출👣[+도달+기타][좋아요x]', price: 3000, min: 100, max: 1000000, time: '데이터가 충분하지 않습니다' },
      { id: 141, name: '🇰🇷인스타그램 리얼 한국인 저장💾', price: 30000, min: 10, max: 1000000, time: '11 분' },
      { id: 147, name: '🌐인스타그램 저장💾', price: 300, min: 100, max: 1000000, time: '15 분' },
      { id: 312, name: '🌐인스타그램 저장💾', price: 300, min: 100, max: 50000, time: '5 분' },
      { id: 313, name: '🌐인스타그램 공유🔗', price: 1500, min: 100, max: 10000000, time: '7 분' }
    ],
    auto_exposure_save_share: [
      { id: 351, name: '🌐인스타그램 자동 저장💾', price: 150, min: 100, max: 1000000, time: '데이터가 충분하지 않습니다' },
      { id: 356, name: '🌐인스타그램 자동 노출👣[+도달+기타][좋아요x]', price: 300, min: 100, max: 100000, time: '데이터가 충분하지 않습니다' },
      { id: 357, name: '🌐인스타그램 자동 노출👣[+도달+홈+기타][좋아요x]', price: 900, min: 10, max: 1000000, time: '데이터가 충분하지 않습니다' },
      { id: 370, name: '🌐인스타그램 자동 공유🔗', price: 1500, min: 100, max: 10000000, time: '9 분' }
    ],
    live_streaming: [
      { id: 393, name: '🌐인스타그램 실시간 라이브 스트리밍 시청[15분]', price: 2250, min: 100, max: 30000, time: '데이터가 충분하지 않습니다' },
      { id: 394, name: '🌐인스타그램 실시간 라이브 스트리밍 시청[30분]', price: 4500, min: 100, max: 30000, time: '데이터가 충분하지 않습니다' },
      { id: 395, name: '🌐인스타그램 실시간 라이브 스트리밍 시청[60분]', price: 9000, min: 100, max: 30000, time: '데이터가 충분하지 않습니다' },
      { id: 396, name: '🌐인스타그램 실시간 라이브 스트리밍 시청[90분]', price: 13500, min: 100, max: 30000, time: '데이터가 충분하지 않습니다' },
      { id: 397, name: '🌐인스타그램 실시간 라이브 스트리밍 시청[120분]', price: 18000, min: 100, max: 30000, time: '데이터가 충분하지 않습니다' },
      { id: 398, name: '🌐인스타그램 실시간 라이브 스트리밍 시청[180분]', price: 27000, min: 100, max: 30000, time: '데이터가 충분하지 않습니다' },
      { id: 399, name: '🌐인스타그램 실시간 라이브 스트리밍 시청[240분]', price: 36000, min: 100, max: 30000, time: '데이터가 충분하지 않습니다' },
      { id: 400, name: '🌐인스타그램 실시간 라이브 스트리밍 시청[360분]', price: 54000, min: 100, max: 30000, time: '데이터가 충분하지 않습니다' },
      { id: 426, name: '🌐인스타그램 실시간 라이브 스트리밍 시청 + 좋아요 + 댓글', price: 30000, min: 20, max: 40000, time: '데이터가 충분하지 않습니다' }
    ],
    auto_likes: [
      { id: 348, name: '🇰🇷 인스타그램 한국인 💎💎파워업 자동 좋아요', price: 14, min: 50, max: 5000, time: '2시간 16분', description: '상세정보' },
      { id: 368, name: '🇰🇷 인스타그램 한국인 자동 좋아요', price: 28, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
      { id: 369, name: '🇰🇷 인스타그램 한국인 슈퍼프리미엄 자동 좋아요', price: 38, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
    ],
    auto_views: [
      { id: 349, name: '인스타그램 동영상 자동 조회수', price: 2, min: 100, max: 2147483647, time: '데이터 부족', description: '상세정보' }
    ],
    auto_comments: [
      { id: 350, name: '🇰🇷 인스타그램 한국인 자동 랜덤 댓글', price: 320, min: 3, max: 100, time: '10분', description: '상세정보' },
      { id: 358, name: '🌐인스타그램 외국인 자동 랜덤 이모지 댓글', price: 30, min: 10, max: 4000000, time: '데이터 부족', description: '상세정보' }
    ],

    // 스레드 세부 서비스 데이터
    threads: {
      likes_korean: [
        { id: 453, name: '🇰🇷 Threads 한국인 리얼 좋아요', price: 15, min: 50, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 454, name: '🇰🇷 Threads 한국인 리얼 팔로워', price: 75, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 457, name: '🇰🇷 Threads 한국인 리얼 댓글', price: 210, min: 5, max: 500, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 유튜브 세부 서비스 데이터
    youtube: {
      views: [
        { id: 371, name: '🌐유튜브 외국인 동영상 조회수', price: 6, min: 500, max: 10000000, time: '9시간 9분', description: '상세정보' },
        { id: 360, name: '🇰🇷유튜브 한국인 동영상 조회수', price: 28, min: 4000, max: 100000, time: '데이터 부족', description: '상세정보' },
        { id: 496, name: '🇰🇷유튜브 한국인 동영상 조회수(시청:20초)', price: 52, min: 10, max: 30000, time: '데이터 부족', description: '상세정보' }
      ],
      auto_views: [
        { id: 486, name: '🌐유튜브 외국인 동영상 자동 조회수', price: 6, min: 1000, max: 10000000, time: '데이터 부족', description: '상세정보' }
      ],
      likes: [
        { id: 136, name: '🌐유튜브 외국인 동영상 좋아요', price: 4, min: 100, max: 500000, time: '데이터 부족', description: '상세정보' },
        { id: 137, name: '🌐유튜브 외국인 동영상 좋아요', price: 6, min: 100, max: 500000, time: '데이터 부족', description: '상세정보' },
        { id: 489, name: '🇰🇷유튜브 한국인 동영상 좋아요', price: 100, min: 10, max: 1000, time: '데이터 부족', description: '상세정보' }
      ],
      auto_likes: [
        { id: 487, name: '🌐유튜브 외국인 동영상 자동 좋아요', price: 4, min: 20, max: 500000, time: '데이터 부족', description: '상세정보' }
      ],
      subscribers: [
        { id: 500, name: '🌐유튜브 외국인 채널 구독자', price: 100, min: 100, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 485, name: '🇰🇷유튜브 한국인 채널 구독자', price: 600, min: 50, max: 10000, time: '11시간 40분', description: '상세정보' },
        { id: 236, name: '🇰🇷유튜브 한국인 채널 구독자', price: 1000, min: 200, max: 10000, time: '데이터 부족', description: '상세정보' }
      ],
      comments_shares: [
        { id: 482, name: '🇰🇷유튜브 한국인 동영상 AI 랜덤 댓글', price: 70, min: 10, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 423, name: '🌐유튜브 외국인 랜덤 댓글', price: 46, min: 20, max: 11000, time: '데이터 부족', description: '상세정보' },
        { id: 138, name: '🌐유튜브 외국인 커스텀 댓글', price: 20, min: 5, max: 100000, time: '데이터 부족', description: '상세정보' },
        { id: 260, name: '🌐유튜브 외국인 이모지 댓글', price: 20, min: 10, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 261, name: '🇰🇷 유튜브 한국 소셜 공유', price: 12, min: 50, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 262, name: '🇰🇷유튜브 한국인 동영상 랜덤 댓글', price: 520, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 263, name: '🇰🇷유튜브 한국인 동영상 [남자] 랜덤 댓글', price: 800, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 264, name: '🇰🇷유튜브 한국인 동영상 [여자] 랜덤 댓글', price: 800, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 265, name: '🇰🇷유튜브 한국인 동영상 [20대] 랜덤 댓글', price: 800, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 266, name: '🇰🇷유튜브 한국인 동영상 [30대] 랜덤 댓글', price: 800, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 267, name: '🇰🇷유튜브 한국인 동영상 [20대][남자] 랜덤 댓글', price: 1040, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 268, name: '🇰🇷유튜브 한국인 동영상 [20대][여자] 랜덤 댓글', price: 1040, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 269, name: '🇰🇷유튜브 한국인 동영상 [30대][남자] 랜덤 댓글', price: 1040, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 270, name: '🇰🇷유튜브 한국인 동영상 [30대][여자] 랜덤 댓글', price: 1040, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 353, name: '🌐유튜브 댓글 좋아요', price: 30, min: 10, max: 10000, time: '데이터 부족', description: '상세정보' }
      ],
      live_streaming: [
        { id: 409, name: '🌐유튜브 실시간 라이브 스트리밍 시청[15분]', price: 2, min: 100, max: 100000, time: '15분', description: '상세정보' },
        { id: 410, name: '🌐유튜브 실시간 라이브 스트리밍 시청[30분]', price: 4, min: 100, max: 100000, time: '18분', description: '상세정보' },
        { id: 411, name: '🌐유튜브 실시간 라이브 스트리밍 시청[60분]', price: 8, min: 100, max: 100000, time: '51분', description: '상세정보' },
        { id: 412, name: '🌐유튜브 실시간 라이브 스트리밍 시청[90분]', price: 12, min: 100, max: 100000, time: '51분', description: '상세정보' },
        { id: 413, name: '🌐유튜브 실시간 라이브 스트리밍 시청[120분]', price: 16, min: 100, max: 100000, time: '25분', description: '상세정보' },
        { id: 414, name: '🌐유튜브 실시간 라이브 스트리밍 시청[180분]', price: 24, min: 100, max: 100000, time: '데이터 부족', description: '상세정보' },
        { id: 415, name: '🌐유튜브 실시간 라이브 스트리밍 랜덤 댓글', price: 30, min: 10, max: 500000, time: '데이터 부족', description: '상세정보' },
        { id: 416, name: '🌐유튜브 실시간 라이브 스트리밍 랜덤 긍정 이모지 댓글', price: 30, min: 10, max: 500000, time: '데이터 부족', description: '상세정보' },
        { id: 417, name: '🌐유튜브 실시간 라이브 스트리밍 커스텀 댓글', price: 30, min: 10, max: 500000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 페이스북 세부 서비스 데이터
    facebook: {
      foreign_services: [
        { id: 154, name: '🌐페이스북 외국인 페이지 좋아요+팔로워💘 👪R30[✔️페이지]', price: 10500, min: 100, max: 1000000, time: '데이터가 충분하지 않습니다' },
        { id: 156, name: '🌐페이스북 외국인 페이지 팔로우👪R30[✔️페이지]', price: 10500, min: 100, max: 500000, time: '데이터가 충분하지 않습니다' },
        { id: 314, name: '페이스북 외국인 프로필 팔로워👪R30[✔️프로필]', price: 10500, min: 100, max: 1000000, time: '데이터가 충분하지 않습니다' },
        { id: 318, name: '🌐페이스북 외국인 게시물 좋아요💘R30[✔️게시물]', price: 9000, min: 100, max: 100000, time: '데이터가 충분하지 않습니다' },
        { id: 319, name: '🌐페이스북 외국인 이모지 리액션[LOVE] ❤️', price: 6000, min: 50, max: 100000, time: '데이터가 충분하지 않습니다' }
      ],
      page_likes_korean: [
        { id: 226, name: '🇰🇷 페이스북 리얼 한국인 페이지 좋아요+팔로워 [일반]', price: 190, min: 20, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 227, name: '🇰🇷 페이스북 리얼 한국인 페이지 좋아요+팔로워 [남성]', price: 210, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 228, name: '🇰🇷 페이스북 리얼 한국인 페이지 좋아요+팔로워 [여성]', price: 210, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 229, name: '🇰🇷 페이스북 리얼 한국인 페이지 좋아요+팔로워 [20대]', price: 210, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 230, name: '🇰🇷 페이스북 리얼 한국인 페이지 좋아요+팔로워 [30대]', price: 210, min: 50, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      post_likes_korean: [
        { id: 198, name: '🇰🇷 페이스북 리얼 한국인 게시물 좋아요', price: 22, min: 30, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 199, name: '🇰🇷 페이스북 리얼 한국인 게시물 좋아요 [남성]', price: 30, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 200, name: '🇰🇷 페이스북 리얼 한국인 게시물 좋아요 [여성]', price: 30, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 201, name: '🇰🇷 페이스북 리얼 한국인 게시물 좋아요 [20대]', price: 30, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 202, name: '🇰🇷 페이스북 리얼 한국인 게시물 좋아요 [30대]', price: 30, min: 20, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      post_comments_korean: [
        { id: 207, name: '🇰🇷 페이스북 리얼 한국인 게시물 랜덤 댓글 [일반]', price: 190, min: 5, max: 10000, time: '데이터 부족', description: '상세정보' },
        { id: 209, name: '🇰🇷 페이스북 리얼 한국인 게시물 랜덤 댓글 [남성]', price: 220, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 210, name: '🇰🇷 페이스북 리얼 한국인 게시물 랜덤 댓글 [여성]', price: 220, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 211, name: '🇰🇷 페이스북 리얼 한국인 게시물 랜덤 댓글 [20대]', price: 220, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 212, name: '🇰🇷 페이스북 리얼 한국인 게시물 랜덤 댓글 [30대]', price: 220, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ],
      profile_follows_korean: [
        { id: 217, name: '🇰🇷 페이스북 리얼 한국인 개인계정 팔로우', price: 190, min: 5, max: 500, time: '데이터 부족', description: '상세정보' },
        { id: 219, name: '🇰🇷 페이스북 리얼 한국인 개인계정 팔로우 [여성]', price: 210, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 220, name: '🇰🇷 페이스북 리얼 한국인 개인계정 팔로우 [20대]', price: 210, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' },
        { id: 221, name: '🇰🇷 페이스북 리얼 한국인 개인계정 팔로우 [30대]', price: 210, min: 5, max: 5000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 틱톡 세부 서비스 데이터
    tiktok: {
      likes_foreign: [
        { id: 458, name: '🇰🇷 틱톡 외국인 리얼 좋아요', price: 1.5, min: 100, max: 1000000, time: '10분', description: '상세정보' }
      ],
      followers_foreign: [
        { id: 476, name: '🇰🇷 틱톡 외국인 리얼 팔로워 [중속]', price: 7, min: 100, max: 1000000, time: '7시간 12분', description: '상세정보' },
        { id: 478, name: '🇰🇷 틱톡 외국인 리얼 팔로워 [중고속]', price: 9, min: 100, max: 1000000, time: '데이터 부족', description: '상세정보' }
      ],
      views_korean: [
        { id: 497, name: '🇰🇷 틱톡 리얼 한국인 조회수 [15초]', price: 21, min: 100, max: 30000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 트위터 세부 서비스 데이터
    twitter: {
      followers_foreign: [
        { id: 197, name: '트위터(X) 외국인 팔로워', price: 21, min: 100, max: 200000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 카카오/네이버 세부 서비스 데이터
    kakao_naver: {
      kakao_services: [
        { id: 271, name: 'K사 채널 친구추가', price: 200, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
      ],
      naver_services: [
        { id: 157, name: 'N사 블로그 팔로워', price: 190, min: 20, max: 1500, time: '데이터 부족', description: '상세정보' },
        { id: 159, name: 'N사 블로그 공감', price: 39, min: 1, max: 1500, time: '2시간 5분', description: '상세정보' },
        { id: 160, name: 'N사 블로그 댓글', price: 340, min: 3, max: 1500, time: '데이터 부족', description: '상세정보' },
        { id: 162, name: 'N사 카페 가입', price: 210, min: 20, max: 1500, time: '데이터 부족', description: '상세정보' },
        { id: 163, name: 'N사 카페 댓글', price: 390, min: 3, max: 1500, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 텔레그램 세부 서비스 데이터
    telegram: {
      subscribers: [
        { id: 190, name: '텔레그램 채널 구독자', price: 5, min: 100, max: 50000, time: '데이터 부족', description: '상세정보' }
      ],
      views: [
        { id: 191, name: '텔레그램 게시물 조회수', price: 0.17, min: 50, max: 10000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 왓츠앱 세부 서비스 데이터
    whatsapp: {
      followers: [
        { id: 442, name: '왓츠앱 채널 팔로워', price: 15, min: 100, max: 10000, time: '데이터 부족', description: '상세정보' }
      ]
    },

    // 네이버 세부 서비스 데이터
    naver: {
      n_k_services: [
        { id: 271, name: 'K사 리얼 채널 친구 추가👫', price: 300000, min: 100, max: 10000, time: '데이터가 충분하지 않습니다' },
        { id: 157, name: 'N사 리얼 포스트 팔로워👪', price: 285000, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 158, name: 'N사 리얼 블로그 이웃 추가👫', price: 285000, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 159, name: 'N사 리얼 블로그 공감💝', price: 58500, min: 1, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 160, name: 'N사 리얼 블로그 댓글💬', price: 510000, min: 3, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 161, name: 'N사 리얼 블로그 스크랩🗂', price: 510000, min: 3, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 167, name: 'N사 리얼 블로그 검색 공감💝', price: 180000, min: 5, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 168, name: 'N사 리얼 블로그 검색 댓글💬', price: 705000, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 162, name: 'N사 리얼 카페 가입👫', price: 315000, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 163, name: 'N사 리얼 카페 댓글💬', price: 585000, min: 3, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 164, name: 'N사 리얼 인플루언서 팬하기👫', price: 390000, min: 50, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 166, name: 'N사 리얼 TV좋아요💖', price: 78000, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 169, name: 'N사 리얼 플레이스 저장💾', price: 300000, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 170, name: 'N사 리얼 플레이스 공유🔗', price: 360000, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 174, name: 'N사 리얼 플레이스 방문+체류 트래픽🔋', price: 94500, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 177, name: 'N사 리얼 플레이스 검색 알림받기📢', price: 360000, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 178, name: 'N사 리얼 플레이스 검색+방문+체류 트래픽🔋', price: 120000, min: 20, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 179, name: 'N사 리얼 스토어팜 상품찜📌', price: 195000, min: 50, max: 1500, time: '데이터가 충분하지 않습니다' },
        { id: 474, name: 'N사 TV 조회수🎬', price: 2700, min: 1000, max: 100000, time: '데이터가 충분하지 않습니다' }
      ]
    },

    // 틱톡 세부 서비스 데이터
    tiktok: {
      tiktok_services: [
        { id: 458, name: '틱톡 외국인 리얼 좋아요💘🚀', price: 2250, min: 100, max: 1000000, time: '50 분' },
        { id: 192, name: '틱톡 외국인 리얼 좋아요💘🚀', price: 2250, min: 100, max: 100000, time: '데이터가 충분하지 않습니다' },
        { id: 194, name: '틱톡 외국인 조회수🎬', price: 180, min: 100, max: 100000000, time: '2 시간 29 분' },
        { id: 476, name: '틱톡 외국인 리얼 계정 팔로워👪🚀[🥇고품질][✔중속]', price: 10500, min: 100, max: 1000000, time: '1 시간 52 분' },
        { id: 478, name: '틱톡 외국인 리얼 계정 팔로워👪🚀[🥇고품질][✔중고속]', price: 13500, min: 100, max: 1000000, time: '13 분' },
        { id: 488, name: '🇰🇷틱톡 리얼 한국인 랜덤 댓글💬', price: 420000, min: 3, max: 100, time: '데이터가 충분하지 않습니다' },
        { id: 421, name: '틱톡 외국인 저장💾', price: 450, min: 100, max: 2147483647, time: '데이터가 충분하지 않습니다' },
        { id: 422, name: '틱톡 외국인 공유🔗', price: 750, min: 100, max: 2147483647, time: '데이터가 충분하지 않습니다' }
      ],
      tiktok_live_streaming: [
        { id: 427, name: '🌐TikTok[틱톡] 실시간 라이브 스트리밍 이모지[Emoji] 댓글💬', price: 5400, min: 10, max: 10000, time: '데이터가 충분하지 않습니다' },
        { id: 429, name: '🌐TikTok[틱톡] 실시간 라이브 스트리밍 커스텀 댓글💬[✔️직접입력]', price: 6000, min: 10, max: 5000, time: '데이터가 충분하지 않습니다' },
        { id: 430, name: '🌐TikTok[틱톡] 실시간 라이브 스트리밍 100% 리얼 좋아요💖[🥇수량당 100개 이상]', price: 270000, min: 5, max: 1000, time: '데이터가 충분하지 않습니다' }
      ]
    },

    // 트위터 세부 서비스 데이터
    twitter: {
      twitter_services: [
        { id: 197, name: '트위터 외국인 팔로워R30♻️', price: 31500, min: 100, max: 200000, time: '데이터가 충분하지 않습니다' }
      ]
    },

    // 텔레그램 세부 서비스 데이터
    telegram: {
      telegram_services: [
        { id: 190, name: '텔레그램 채널 구독자👫T1', price: 7500, min: 100, max: 50000, time: '데이터가 충분하지 않습니다' },
        { id: 437, name: '텔레그램 채널 구독자👫T3', price: 6000, min: 100, max: 100000, time: '4 분' },
        { id: 191, name: '텔레그램 게시물 조회수', price: 255, min: 50, max: 10000, time: '데이터가 충분하지 않습니다' }
      ]
    },

    // 왓츠앱 세부 서비스 데이터
    whatsapp: {
      whatsapp_services: [
        { id: 442, name: '왓츠앱 채널 팔로워👫', price: 22500, min: 100, max: 10000, time: '데이터가 충분하지 않습니다' }
      ]
    }
  }
  
  // 세부 서비스 목록 가져오기
  const getDetailedServices = (platform, serviceType) => {
    if (platform === 'top-exposure' && serviceType === 'popular_posts') {
      return instagramDetailedServices.popular_posts
    }
    if (platform === 'instagram' && instagramDetailedServices[serviceType]) {
      return instagramDetailedServices[serviceType]
    }
    if (platform === 'threads' && instagramDetailedServices.threads && instagramDetailedServices.threads[serviceType]) {
      return instagramDetailedServices.threads[serviceType]
    }
    if (platform === 'youtube' && instagramDetailedServices.youtube && instagramDetailedServices.youtube[serviceType]) {
      return instagramDetailedServices.youtube[serviceType]
    }
    if (platform === 'facebook' && instagramDetailedServices.facebook && instagramDetailedServices.facebook[serviceType]) {
      return instagramDetailedServices.facebook[serviceType]
    }
    if (platform === 'naver' && instagramDetailedServices.naver && instagramDetailedServices.naver[serviceType]) {
      return instagramDetailedServices.naver[serviceType]
    }
    if (platform === 'tiktok' && instagramDetailedServices.tiktok && instagramDetailedServices.tiktok[serviceType]) {
      return instagramDetailedServices.tiktok[serviceType]
    }
    if (platform === 'twitter' && instagramDetailedServices.twitter && instagramDetailedServices.twitter[serviceType]) {
      return instagramDetailedServices.twitter[serviceType]
    }
    if (platform === 'telegram' && instagramDetailedServices.telegram && instagramDetailedServices.telegram[serviceType]) {
      return instagramDetailedServices.telegram[serviceType]
    }
    if (platform === 'whatsapp' && instagramDetailedServices.whatsapp && instagramDetailedServices.whatsapp[serviceType]) {
      return instagramDetailedServices.whatsapp[serviceType]
    }
    // 기존 로직 사용
    return getDetailedServicesLegacy(platform, serviceType)
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
        return selectedService.price * quantity // 1개당 가격
      }
    }
    return 0
  }

  const platforms = [
    { id: 'recommended', name: '추천서비스', icon: Star, color: '#f59e0b' },
    { id: 'event', name: '이벤트', icon: Package, color: '#8b5cf6' },
    { id: 'top-exposure', name: '상위노출', icon: Trophy, color: '#f59e0b' },
    { id: 'instagram', name: '인스타그램', icon: Instagram, color: '#e4405f' },
    { id: 'youtube', name: '유튜브', icon: Youtube, color: '#ff0000' },
    { id: 'facebook', name: '페이스북', icon: Facebook, color: '#1877f2' },
    { id: 'tiktok', name: '틱톡', icon: MessageCircle, color: '#000000' },
    { id: 'threads', name: '스레드', icon: MessageSquare, color: '#000000' },
    { id: 'twitter', name: '트위터', icon: Twitter, color: '#1da1f2' },
    { id: 'kakao', name: '카카오', icon: MessageCircle, color: '#fbbf24' },
    { id: 'telegram', name: '텔레그램', icon: MessageCircle, color: '#0088cc' },
    { id: 'whatsapp', name: '왓츠앱', icon: MessageSquare, color: '#25d366' },
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
          { id: 'popular_posts', name: '🎯 추천탭 상위노출 서비스', description: '인스타그램 추천탭 상위노출 패키지 서비스' }
        ]
      case 'instagram':
        return [
          { id: 'popular_posts', name: '💗인스타그램 인기게시물 등록[업데이트]', description: '인기게시물 등록 및 상위 노출 서비스' },
          { id: 'likes_korean', name: '🇰🇷인스타그램 한국인 좋아요', description: '한국인 좋아요 서비스' },
          { id: 'likes_foreign', name: '🌐인스타그램 외국인 좋아요', description: '외국인 좋아요 서비스' },
          { id: 'followers_korean', name: '🇰🇷인스타그램 한국인 팔로워', description: '한국인 팔로워 서비스' },
          { id: 'views', name: '🌐🇰🇷인스타그램 조회수', description: '동영상 조회수 서비스' },
          { id: 'comments_korean', name: '🌐🇰🇷인스타그램 댓글', description: '댓글 서비스' },
          { id: 'regram_korean', name: '🇰🇷인스타그램 한국인 리그램', description: '한국인 리그램 서비스' },
          { id: 'followers_foreign', name: '🌐인스타그램 외국인 팔로워', description: '외국인 팔로워 서비스' },
          { id: 'exposure_save_share', name: '🇰🇷🌐인스타그램 [노출/도달/저장/공유]', description: '노출, 도달, 저장, 공유 서비스' },
          { id: 'auto_exposure_save_share', name: '🇰🇷🌐인스타그램 자동 노출/도달/저장/공유/기타', description: '자동 노출, 도달, 저장, 공유 서비스' },
          { id: 'live_streaming', name: '🌐인스타그램 실시간 라이브 스트리밍 시청', description: '실시간 라이브 스트리밍 시청 서비스' },
          { id: 'auto_likes', name: '🇰🇷🌐인스타그램 자동 좋아요', description: '자동 좋아요 서비스' },
          { id: 'auto_views', name: '🇰🇷🌐인스타그램 자동 조회수', description: '자동 조회수 서비스' },
          { id: 'auto_comments', name: '🇰🇷🌐인스타그램 자동 댓글', description: '자동 댓글 서비스' }
        ]
      case 'youtube':
        return [
          { id: 'views', name: '🇰🇷🌐유튜브 조회수', description: '동영상 조회수 서비스' },
          { id: 'auto_views', name: '🇰🇷🌐유튜브 자동 조회수', description: '자동 조회수 서비스' },
          { id: 'likes', name: '🇰🇷🌐유튜브 좋아요', description: '동영상 좋아요 서비스' },
          { id: 'auto_likes', name: '🇰🇷🌐유튜브 자동 좋아요', description: '자동 좋아요 서비스' },
          { id: 'subscribers', name: '🇰🇷🌐유튜브 채널 구독자', description: '채널 구독자 서비스' },
          { id: 'comments_shares', name: '🇰🇷🌐유튜브 댓글/공유/기타', description: '댓글, 공유, 기타 서비스' },
          { id: 'live_streaming', name: '🌐유튜브 실시간 라이브 스트리밍 시청', description: '실시간 라이브 스트리밍 시청 서비스' }
        ]
      case 'tiktok':
        return [
          { id: 'tiktok_services', name: '🇰🇷🌐TikTok[틱톡]', description: '틱톡 서비스' },
          { id: 'tiktok_live_streaming', name: '🌐TikTok[틱톡] 실시간 라이브 스트리밍 시청', description: '실시간 라이브 스트리밍 시청 서비스' }
        ]
      case 'facebook':
        return [
          { id: 'foreign_services', name: '🌐페이스북 외국인 서비스', description: '외국인 서비스' },
          { id: 'page_likes_korean', name: '🇰🇷페이스북 한국인 페이지 좋아요', description: '한국인 페이지 좋아요 서비스' },
          { id: 'post_likes_korean', name: '🇰🇷페이스북 한국인 게시물 좋아요', description: '한국인 게시물 좋아요 서비스' },
          { id: 'post_comments_korean', name: '🇰🇷페이스북 한국인 게시물 댓글', description: '한국인 게시물 댓글 서비스' },
          { id: 'profile_follows_korean', name: '🇰🇷페이스북 한국인 개인계정 팔로우', description: '한국인 개인계정 팔로우 서비스' }
        ]
      case 'threads':
        return [
          { id: 'likes_korean', name: '🌐스레드[THREADS] 서비스', description: '스레드 서비스' }
        ]
      case 'naver':
        return [
          { id: 'n_k_services', name: 'N사 / K사 서비스', description: '네이버/카카오 서비스' }
        ]
      case 'twitter':
        return [
          { id: 'twitter_services', name: '🌐Twitter[트위터][X][엑스]', description: '트위터 서비스' }
        ]
      case 'telegram':
        return [
          { id: 'telegram_services', name: '🌐Telegram[텔레그램]', description: '텔레그램 서비스' }
        ]
      case 'whatsapp':
        return [
          { id: 'whatsapp_services', name: '🌐Whatsapp[왓츠앱]', description: '왓츠앱 서비스' }
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
    // 기본 서비스 목록 (실제로는 API에서 가져와야 함)
    return [
      { id: 'followers_korean', name: '한국인 팔로워', price: 1000, min: 10, max: 10000 },
      { id: 'likes_korean', name: '한국인 좋아요', price: 500, min: 10, max: 10000 },
      { id: 'comments_korean', name: '한국인 댓글', price: 2000, min: 5, max: 1000 }
    ]
  }

  // 서비스 타입별 세부 서비스 목록 (기존 로직 유지)
  const getDetailedServicesLegacy = (platform, serviceType) => {
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
    
    let basePrice = 0
    
    // 인스타그램, 스레드, 유튜브, 페이스북, 네이버, 틱톡, 트위터, 텔레그램, 왓츠앱의 경우 새로운 가격 계산 로직 사용
    if (selectedPlatform === 'instagram' || selectedPlatform === 'threads' || selectedPlatform === 'youtube' || selectedPlatform === 'facebook' || selectedPlatform === 'naver' || selectedPlatform === 'tiktok' || selectedPlatform === 'twitter' || selectedPlatform === 'telegram' || selectedPlatform === 'whatsapp') {
      basePrice = selectedDetailedService.price * quantity // 1개당 가격
    } else {
      // 기존 SMM KINGS 가격 사용
      basePrice = selectedDetailedService.price * quantity
    }
    
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



  const handleHelpClick = () => {
    alert('주문 방법에 대한 상세한 가이드를 확인할 수 있습니다.')
  }



  const handlePurchase = async () => {
    try {
      console.log('🚀 주문 생성 시작')
      console.log('Current User:', currentUser)
      console.log('Selected Detailed Service:', selectedDetailedService)
      console.log('Quantity:', quantity)
      console.log('Total Price:', totalPrice)
      
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

      if (((selectedPlatform === 'instagram' && (selectedService === 'comments_korean' || selectedService === 'comments_foreign')) || 
           (selectedPlatform === 'youtube' && selectedService === 'comments_korean')) && (!comments || !comments.trim())) {
        alert('댓글 내용을 입력해주세요!')
        return
      }

      // selectedDetailedService가 undefined인 경우 강제로 기본값 설정
      if (!selectedDetailedService || (!selectedDetailedService.id && !selectedDetailedService.smmkings_id)) {
        console.error('⚠️ selectedDetailedService가 undefined입니다:', selectedDetailedService)
        alert('서비스 선택에 문제가 있습니다. 페이지를 새로고침하고 다시 시도해주세요.')
        return
      }
    } catch (error) {
      console.error('❌ 주문 생성 초기 검증 오류:', error)
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
        max: 0,
        posts: 0,
        delay: 0,
        expiry: '',
        oldPosts: 0
      }

      console.log('=== 주문 데이터 생성 ===')
      console.log('Order Data:', orderData)
      console.log('Selected Detailed Service:', selectedDetailedService)

      console.log('Order Data for Backend API:', orderData)
      
      // 백엔드 API 호출 (SMM Panel 변환 없이 직접 전송)
      const response = await fetch('/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': userId
        },
        body: JSON.stringify(orderData)
      })

      const result = await response.json()
      console.log('API Response:', result)

      if (!response.ok) {
        throw new Error(result.error || '주문 생성에 실패했습니다.')
      }

      if (result.error) {
        alert(`주문 생성 실패: ${result.error}`)
      } else {
        // 주문 생성 성공 후 포인트 결제 페이지로 이동
        console.log('✅ 주문 생성 성공, 포인트 결제 페이지로 이동:', result)
        
        // 사용자 포인트 조회
        let userPoints = null
        try {
          const pointsResponse = await fetch(`/api/points?user_id=${userId}`)
          if (pointsResponse.ok) {
            userPoints = await pointsResponse.json()
            console.log('사용자 포인트:', userPoints)
          }
        } catch (error) {
          console.error('포인트 조회 오류:', error)
        }

        // 주문 데이터에 서비스 이름 추가
        const orderDataWithService = {
          ...orderData,
          service_name: selectedDetailedService?.name || '선택된 서비스',
          unit_price: selectedDetailedService?.price || 0,
          total_price: safeTotalPrice
        }

        // 기존 결제 페이지로 이동
        navigate(`/payment/${selectedPlatform}`, { 
          state: { 
            orderData: {
              ...orderDataWithService,
              orderId: result.order_id || result.order,
              userId: userId,
              platform: selectedPlatform,
              service: selectedService,
              detailedService: selectedDetailedService,
              quantity: safeQuantity,
              unitPrice: selectedDetailedService?.price || 0,
              totalPrice: safeTotalPrice,
              link: safeLink,
              comments: safeComments,
              explanation: explanation || ''
            },
            userPoints: userPoints
          }
        })
        return
      }
    } catch (error) {
      console.error('Order creation error:', error)
      alert(`주문 생성 실패: ${error.message}`)
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
        <span className="step-number">1</span>
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
        
        {/* Service Selection */}
        <div className="service-category">
          <h3 className="category-title">
            <span className="step-number">2</span>
            {platforms.find(p => p.id === selectedPlatform)?.name} 서비스
          </h3>
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
          <h3>
            <span className="step-number">3</span>
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
                      최소: {service.min.toLocaleString()} ~ 최대: {service.max.toLocaleString()}
                    </div>
                  </div>
                  <div className="detailed-service-price">
                    {(selectedPlatform === 'instagram' || selectedPlatform === 'threads' || selectedPlatform === 'youtube' || selectedPlatform === 'facebook' || selectedPlatform === 'naver' || selectedPlatform === 'tiktok' || selectedPlatform === 'twitter' || selectedPlatform === 'telegram' || selectedPlatform === 'whatsapp') ? 
                      `₩${service.price.toFixed(2)}` : 
                      `${service.price.toFixed(2)}원`
                    }
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
          <h3>
            <span className="step-number">4</span>
            주문 정보 입력
          </h3>
          
          
          {/* Quantity Selection */}
          <div className="form-group">
            <label>수량 선택</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => {
                const newQuantity = parseInt(e.target.value) || 0
                if (newQuantity >= selectedDetailedService.min && newQuantity <= selectedDetailedService.max) {
                  handleQuantityChange(newQuantity)
                }
              }}
              min={selectedDetailedService.min}
              max={selectedDetailedService.max}
              className="quantity-input-field"
              placeholder={`최소 ${selectedDetailedService.min.toLocaleString()} ~ 최대 ${selectedDetailedService.max.toLocaleString()}`}
            />
            <div className="quantity-hint">
              최소: {selectedDetailedService.min.toLocaleString()} ~ 최대: {selectedDetailedService.max.toLocaleString()}
            </div>
          </div>

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

          {selectedDetailedService && selectedDetailedService.package && selectedDetailedService.steps && (
            <div className="package-steps">
              <h3>📦 패키지 구성</h3>
              <div className="steps-container">
                {selectedDetailedService.steps.map((step, index) => (
                  <div key={step.id} className="package-step">
                    <div className="step-header">
                      <span className="step-number">{index + 1}</span>
                      <span className="step-name">{step.name}</span>
                      <span className="step-price">{step.price.toLocaleString()}원</span>
                    </div>
                    <div className="step-details">
                      <p className="step-description">{step.description}</p>
                      <p className="step-quantity">수량: {step.quantity.toLocaleString()}개</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="package-total">
                <strong>총 패키지 가격: {selectedDetailedService.price.toLocaleString()}원</strong>
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

    </div>
  )
}

export default Home
