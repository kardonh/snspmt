import React, { useState, useEffect,useMemo } from 'react'
import { useLocation, Link, useNavigate } from 'react-router-dom'
import { 
  Star, 
  Info, 
  HelpCircle, 
  LogIn, 
  UserPlus, 
  FileText, 
  ChevronDown,
  ChevronUp,
  X,
  Shield,
  CreditCard,
  Package,
  Coins,
  Users
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useGuest } from '../contexts/GuestContext'
import { supabase } from '../supabase/client'
import './Sidebar.css'

const Sidebar = ({ onClose }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const { currentUser, logout, openLoginModal, openSignupModal } = useAuth()
  const { isGuest } = useGuest()

  const [businessInfoOpen, setBusinessInfoOpen] = useState(false)
  const [userPoints, setUserPoints] = useState(0)
  const [pointsLoading, setPointsLoading] = useState(false)
  const [hasReferralCode, setHasReferralCode] = useState(false)
  const [referralCodeLoading, setReferralCodeLoading] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  
  // isAdmin 상태 변경 추적
  useEffect(() => {
    console.log('🔄 Sidebar: isAdmin 상태 변경됨 - 새 값:', isAdmin, '타입:', typeof isAdmin)
  }, [isAdmin])

  // Debounce timer ref
  const fetchTimerRef = React.useRef(null)
  const lastFetchRef = React.useRef(0)
  const FETCH_COOLDOWN = 1000000 // 10 minutes minimum between fetches

  // 사용자 포인트 조회 함수 (with debounce)
  const fetchUserPoints = async (force = false) => {
    // currentUser가 없으면 포인트 조회하지 않음
    if (!currentUser?.uid) {
      setUserPoints(0)
      return
    }
    
    const now = Date.now()
    const timeSinceLastFetch = now - lastFetchRef.current
    
    // Prevent too frequent calls (unless forced)
    if (!force && timeSinceLastFetch < FETCH_COOLDOWN) {
      console.log(`⏭️ 포인트 조회 스킵 (${Math.round((FETCH_COOLDOWN - timeSinceLastFetch) / 1000)}초 후 가능)`)
      return
    }
    
    const userId = currentUser.uid
    lastFetchRef.current = now
    
    setPointsLoading(true)
    try {
      const response = await fetch(`${window.location.origin}/api/points?user_id=${userId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setUserPoints(data.points || 0)
      } else {
        setUserPoints(0)
      }
    } catch (error) {
      console.error('포인트 조회 실패:', error)
      setUserPoints(0)
    } finally {
      setPointsLoading(false)
    }
  }

  // 추천인 코드 확인 함수
  const checkReferralCode = async () => {
    if (!currentUser) return
    
    setReferralCodeLoading(true)
    try {
      // 사용자 이메일 가져오기 (추천인 코드는 이메일로 저장됨)
      const userEmail = currentUser.email || `${currentUser.uid}@example.com`
      const response = await fetch(`/api/referral/my-codes?user_id=${userEmail}`)
      
      if (response.ok) {
        const data = await response.json()
        setHasReferralCode(data.codes && data.codes.length > 0)
      } else {
        setHasReferralCode(false)
      }
    } catch (error) {
      console.error('추천인 코드 확인 실패:', error)
      setHasReferralCode(false)
    } finally {
      setReferralCodeLoading(false)
    }
  }

  // 포인트 업데이트 이벤트 핸들러 (force refresh)
  const handlePointsUpdate = () => {
    fetchUserPoints(true) // Force immediate fetch
  }

  // 관리자 권한 확인 함수
  const checkAdminStatus = async () => {
    console.log('🔍 Sidebar: checkAdminStatus 호출됨')
    console.log('🔍 Sidebar: currentUser:', currentUser)
    console.log('🔍 Sidebar: currentUser?.email:', currentUser?.email)
    
    if (!currentUser?.email) {
      console.log('⚠️ Sidebar: currentUser.email이 없어 관리자 권한 확인을 건너뜁니다.')
      setIsAdmin(false)
      return
    }
    
    try {
      console.log('🔍 Sidebar: 관리자 권한 확인 시작 - email:', currentUser.email)
      console.log('🔍 Sidebar: API 호출 전 - 현재 isAdmin:', isAdmin)
      
      // Supabase 세션 가져오기 (타임아웃 처리)
      let accessToken = null
      try {
        console.log('🔍 Sidebar: Supabase 세션 가져오기 시도...')
        const sessionPromise = supabase.auth.getSession()
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('세션 가져오기 타임아웃')), 3000) // 3초로 단축
        })
        
        const session = await Promise.race([sessionPromise, timeoutPromise])
        accessToken = session.data?.session?.access_token
        console.log('✅ Sidebar: Supabase 세션 가져오기 성공, 토큰:', accessToken ? '있음' : '없음')
      } catch (sessionError) {
        console.warn('⚠️ Sidebar: Supabase 세션 가져오기 실패 또는 타임아웃, localStorage에서 토큰 찾기:', sessionError.message)
        
        // localStorage에서 토큰 찾기
        const tokenKeys = [
          'supabase_access_token',
          'sb-access-token',
          `sb-${window.location.hostname === 'localhost' ? 'localhost' : 'supabase'}-auth-token`
        ]
        
        for (const key of tokenKeys) {
          const token = localStorage.getItem(key)
          if (token) {
            try {
              // JSON 파싱 시도
              const parsed = JSON.parse(token)
              accessToken = parsed?.access_token || parsed
            } catch {
              // 문자열 그대로 사용
              accessToken = token
            }
            if (accessToken) {
              console.log(`✅ Sidebar: localStorage에서 토큰 찾음 (${key})`)
              break
            }
          }
        }
        
        // localStorage의 모든 키 확인 (sb-로 시작하는 키들)
        if (!accessToken) {
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i)
            if (key && key.startsWith('sb-')) {
              try {
                const value = localStorage.getItem(key)
                const parsed = JSON.parse(value)
                if (parsed?.access_token) {
                  accessToken = parsed.access_token
                  console.log(`✅ Sidebar: localStorage에서 토큰 찾음 (${key})`)
                  break
                }
              } catch {
                // JSON 파싱 실패 시 무시
              }
            }
          }
        }
      }
      
      const headers = {
        'Content-Type': 'application/json'
      }
      
      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`
        console.log('✅ Sidebar: Authorization 토큰 설정됨')
      } else {
        console.log('⚠️ Sidebar: Authorization 토큰 없음 (X-User-Email만 사용)')
      }
      
      if (currentUser.email) {
        headers['X-User-Email'] = currentUser.email
        console.log('✅ Sidebar: X-User-Email 헤더 설정:', currentUser.email)
      }
      
      // API 호출에 타임아웃 추가
      const controller = new AbortController()
      const timeoutId = setTimeout(() => {
        console.error('⏰ Sidebar: API 호출 타임아웃 (10초) - 요청 취소')
        controller.abort()
      }, 10000) // 10초 타임아웃
      
      console.log('📡 Sidebar: API 호출 시작 - /api/users/check-admin')
      console.log('📡 Sidebar: 요청 헤더:', headers)
      
      let response
      try {
        const fetchPromise = fetch('/api/users/check-admin', {
          method: 'GET',
          headers,
          signal: controller.signal
        })
        
        console.log('📡 Sidebar: fetch Promise 생성됨, 응답 대기 중...')
        response = await fetchPromise
        clearTimeout(timeoutId)
        console.log('✅ Sidebar: 응답 받음 - 상태:', response.status, 'ok:', response.ok)
        console.log('📡 Sidebar: 관리자 권한 확인 응답 상태:', response.status)
      } catch (fetchError) {
        clearTimeout(timeoutId)
        if (fetchError.name === 'AbortError') {
          console.error('❌ Sidebar: API 호출 타임아웃 (10초)')
          setIsAdmin(false)
          return
        }
        console.error('❌ Sidebar: API 호출 실패:', fetchError)
        console.error('❌ Sidebar: 에러 상세:', {
          name: fetchError.name,
          message: fetchError.message,
          stack: fetchError.stack
        })
        setIsAdmin(false)
        return
      }
      
      if (response.ok) {
        const data = await response.json()
        console.log('📋 Sidebar: 관리자 권한 확인 응답 데이터:', JSON.stringify(data, null, 2))
        console.log('🔍 Sidebar: is_admin 값:', data.is_admin, '타입:', typeof data.is_admin)
        
        // debug 정보가 있으면 출력
        if (data.debug) {
          console.log('🔍 Sidebar: 백엔드 디버그 정보:', data.debug)
        }
        
        // 다양한 true 값 처리 (boolean true, 문자열 "true", 숫자 1 등)
        const isAdminValue = data.is_admin === true || 
                            data.is_admin === 'true' || 
                            data.is_admin === 1 || 
                            data.is_admin === '1' ||
                            String(data.is_admin).toLowerCase() === 'true'
        
        console.log('✅ Sidebar: 최종 isAdmin 값:', isAdminValue, '타입:', typeof isAdminValue)
        console.log('✅ Sidebar: setIsAdmin 호출 전 - 현재 isAdmin:', isAdmin)
        
        // 강제로 boolean으로 변환
        const finalIsAdmin = Boolean(isAdminValue)
        console.log('✅ Sidebar: 최종 boolean 변환:', finalIsAdmin)
        
        setIsAdmin(finalIsAdmin)
        
        // 상태 업데이트 확인을 위한 추가 로그
        setTimeout(() => {
          console.log('⏰ Sidebar: 100ms 후 isAdmin 상태 확인:', isAdmin)
        }, 100)
      } else {
        const errorText = await response.text()
        console.error('❌ Sidebar: 관리자 권한 확인 실패 - 상태:', response.status, '응답:', errorText)
        setIsAdmin(false)
      }
    } catch (error) {
      console.error('❌ Sidebar: 관리자 권한 확인 오류:', error)
      setIsAdmin(false)
    }
  }

  // 사용자가 로그인했을 때 포인트 조회 및 추천인 코드 확인
  useEffect(() => {
    console.log('🔄 Sidebar useEffect 실행 - currentUser:', currentUser?.email)
    console.log('🔄 Sidebar useEffect - currentUser 전체:', currentUser)
    if (currentUser) {
      console.log('✅ Sidebar: currentUser 있음 - 관리자 권한 확인 시작')
      fetchUserPoints()
      checkReferralCode()
      // 관리자 권한 확인을 명시적으로 호출
      console.log('🔍 Sidebar: checkAdminStatus 함수 호출 직전')
      checkAdminStatus()
    } else {
      console.log('⚠️ Sidebar: currentUser 없음 - 모든 상태 초기화')
      setUserPoints(0)
      setHasReferralCode(false)
      setIsAdmin(false)
    }

    // 포인트 업데이트 이벤트 리스너
    window.addEventListener('pointsUpdated', handlePointsUpdate)
    
    // storage 이벤트 리스너 (다른 탭에서 로그인/로그아웃 시)
    window.addEventListener('storage', (e) => {
      if (e.key === 'userId' || e.key === 'firebase_user_id') {
        fetchUserPoints()
      }
    })
    
    // 포커스 이벤트 리스너 (탭 전환 시)
    window.addEventListener('focus', fetchUserPoints)
    
    // 가시성 변경 이벤트 리스너
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        fetchUserPoints()
      }
    })

    return () => {
      window.removeEventListener('pointsUpdated', handlePointsUpdate)
      window.removeEventListener('storage', fetchUserPoints)
      window.removeEventListener('focus', fetchUserPoints)
      document.removeEventListener('visibilitychange', fetchUserPoints)
    }
  }, [currentUser])

  // 기본 메뉴 아이템
  const baseMenuItems = [
    { id: 'order', name: '주문하기', icon: Star, path: '/', color: '#3b82f6' },
    { id: 'orders', name: '주문내역', icon: FileText, path: '/orders', color: '#8b5cf6' },
    { id: 'points', name: '포인트 구매', icon: CreditCard, path: '/points', color: '#f59e0b' },
    { id: 'blog', name: '블로그', icon: FileText, path: '/blog', color: '#06b6d4' },
    { id: 'faq', name: '자주 묻는 질문', icon: HelpCircle, path: '/faq', color: '#10b981' },
    { id: 'service', name: '서비스 소개서', icon: FileText, path: '/service-guide.pdf', color: '#6b7280', external: true },
  ]

  // 추천인 대시보드 메뉴 (추천인 코드가 있는 사용자만)
  const referralMenuItem = { id: 'referral', name: '추천인 대시보드', icon: Users, path: '/referral', color: '#8b5cf6' }

  // 최종 메뉴 아이템 구성
  const filteredBaseMenuItems = (isGuest && !currentUser)
    ? baseMenuItems.filter(item => ['order', 'blog', 'faq', 'service'].includes(item.id)) // 게스트 모드에서는 주문하기, 블로그, FAQ, 서비스 소개서만 표시
    : baseMenuItems

  const menuItems = (hasReferralCode && !isGuest) 
    ? [...filteredBaseMenuItems.slice(0, 3), referralMenuItem, ...filteredBaseMenuItems.slice(3)]
    : filteredBaseMenuItems

  // 관리자 메뉴 아이템 (관리자 계정일 때만 표시)
  const adminMenuItems = [
    { id: 'admin', name: '관리자 대시보드', icon: Shield, path: '/admin', color: '#dc2626' }
  ]

  const handleSignOut = async () => {
    try {
      console.log('🔐 Sidebar 로그아웃 버튼 클릭');
      if (typeof logout === 'function') {
        await logout();
        console.log('✅ Sidebar 로그아웃 처리 완료');
        // 포인트 초기화
        setUserPoints(0);
        alert('로그아웃되었습니다. 게스트 모드로 전환됩니다.');
        // 모바일에서 사이드바가 열려있다면 닫기
        if (onClose) {
          onClose();
        }
        // 모바일에서 페이지 리로드하여 상태 완전히 초기화
        if (window.innerWidth <= 1200) {
          window.location.href = '/';
        } else {
          navigate('/');
        }
      } else {
        console.error('logout 함수가 정의되지 않았습니다.');
        alert('로그아웃 함수를 찾을 수 없습니다.');
      }
    } catch (error) {
      console.error('로그아웃 실패:', error);
      // 오류가 있어도 포인트 초기화
      setUserPoints(0);
      alert('로그아웃 중 오류가 발생했습니다.');
      // 모바일에서 오류 발생 시에도 페이지 리로드
      if (window.innerWidth <= 1200) {
        window.location.href = '/';
      }
    }
  }

  const handleMenuItemClick = () => {
    // 모바일에서만 사이드바 닫기 (onClose가 있을 때만)
    if (onClose && window.innerWidth <= 768) {
      onClose()
    }
  }

  return (
    <aside className="sidebar">
      {/* Mobile Close Button */}
      {onClose && (
        <button className="mobile-close-btn" onClick={onClose}>
          <X size={24} />
        </button>
      )}
      
      {/* Logo */}
      <div className="sidebar-logo">
        <img 
          src="/logo.png" 
          alt="Sociality" 
          className="logo-image" 
          onClick={() => navigate('/')}
          style={{ cursor: 'pointer' }}
        />
      </div>

      {/* User Status */}
      <div className="user-status">
        {currentUser ? (
          <div className="user-info">
            <span className="user-name">
              {currentUser?.displayName || currentUser?.email || '사용자'}
            </span>
              <div className="user-points">
                <Coins size={16} className="points-icon" />
                <span className="points-text">
                  {pointsLoading ? '로딩중...' : `${userPoints.toLocaleString()}P`}
                </span>
              </div>
            <button onClick={handleSignOut} className="logout-btn">로그아웃</button>
          </div>
        ) : (
          <div className="guest-info">
            <span className="guest-text">게스트 모드</span>
            <div className="auth-buttons">
              <button onClick={openLoginModal} className="login-btn">로그인</button>
              <button onClick={openSignupModal} className="signup-btn">회원가입</button>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Menu */}
      <nav className="sidebar-nav">
        {menuItems.map(({ id, name, icon: Icon, path, color, external }) => (
          external ? (
            <a
              key={id}
              href={path}
              target="_blank"
              rel="noopener noreferrer"
              className="sidebar-item"
              onClick={handleMenuItemClick}
            >
              <div className="sidebar-item-icon" style={{ color }}>
                <Icon size={20} />
              </div>
              <span className="sidebar-item-text">{name}</span>
            </a>
          ) : (
          <Link
            key={id}
            to={path}
            className={`sidebar-item ${location.pathname === path ? 'active' : ''}`}
            onClick={handleMenuItemClick}
          >
            <div className="sidebar-item-icon" style={{ color }}>
              <Icon size={20} />
            </div>
            <span className="sidebar-item-text">{name}</span>
          </Link>
          )
        ))}
        
        {/* 관리자 메뉴 (관리자 계정일 때만 표시) */}
        {(() => {
          console.log('🔍 Sidebar 렌더링 - isAdmin 상태:', isAdmin, '타입:', typeof isAdmin)
          console.log('🔍 Sidebar 렌더링 - currentUser:', currentUser?.email)
          return null
        })()}
        {isAdmin === true && (
          <>
            <div className="admin-separator"></div>
            {adminMenuItems.map(({ id, name, icon: Icon, path, color }) => (
              <Link
                key={id}
                to={path}
                className={`sidebar-item admin-item ${location.pathname === path ? 'active' : ''}`}
                onClick={handleMenuItemClick}
              >
                <div className="sidebar-item-icon" style={{ color }}>
                  <Icon size={20} />
                </div>
                <span className="sidebar-item-text">{name}</span>
              </Link>
            ))}
          </>
        )}
      </nav>

      {/* Business Information */}
      <div className="business-info">
        <button 
          className="business-info-toggle"
          onClick={() => setBusinessInfoOpen(!businessInfoOpen)}
        >
          <span>Sociality 사업자정보</span>
          {businessInfoOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        
        {businessInfoOpen && (
          <div className="business-info-content">
            <div className="info-item">
              <strong>상호명:</strong> 탬블(tamble)
            </div>
            <div className="info-item">
              <strong>대표:</strong> 서동현
            </div>
            <div className="info-item">
              <strong>주소:</strong> 충북 청주시 상당구 사직대로361번길 158-10 3R-7
            </div>
            <div className="info-item">
              <strong>사업자번호:</strong> 869-02-02736
            </div>
            <div className="info-item">
              <strong>통신판매:</strong> 2023-충북청주-3089호
            </div>
            <div className="info-item">
              <strong>이메일:</strong> tambleofficial@gmail.com
            </div>
            <div className="info-links">
              <a href="https://drive.google.com/file/d/1Nn3ABQFUbRSUpD25IAdyJrfjBbDn70Ji/view?usp=sharing" target="_blank">이용약관</a>
              <a href="https://drive.google.com/file/d/1PWCtiDv_tFrP2EyNVaQw4CY-pi0K5Hrc/view?usp=sharing" target="_blank">개인정보처리방침</a>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
