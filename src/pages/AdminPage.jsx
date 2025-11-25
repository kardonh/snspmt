import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Users, 
  ShoppingCart, 
  BarChart3,
  Settings, 
  Search, 
  CheckCircle,
  XCircle,
  X,
  Eye,
  Download,
  RefreshCw,
  TrendingUp,
  DollarSign,
  Activity,
  Info,
  UserPlus,
  Bell,
  File,
  Edit,
  Trash2,
  Package,
  Tag
} from 'lucide-react'
import ReferralRegistration from '../components/ReferralRegistration'
import AdminServiceManagement from '../components/AdminServiceManagement'
import AdminUserManagement from '../components/AdminUserManagement'
import AdminCouponManagement from '../components/AdminCouponManagement'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../supabase/client'
import { 
  saveReferralCode, 
  getReferralCodes, 
  saveReferral, 
  getReferrals, 
  getCommissions 
} from '../utils/referralStorage'
import './AdminPage.css'

const AdminPage = () => {
  const navigate = useNavigate()
  const { currentUser } = useAuth()
  const [isAdmin, setIsAdmin] = useState(null)  // null: 체크 중, true: 관리자, false: 일반 사용자
  const [checkingAdmin, setCheckingAdmin] = useState(true)
  
  // 관리자 권한 체크
  useEffect(() => {
    let timeoutId = null
    let abortController = null
    let isMounted = true
    
    const checkAdminAccess = async () => {
      console.log('🔍 관리자 권한 체크 시작...')
      
      if (!currentUser) {
        console.log('⚠️ currentUser가 없습니다.')
        if (isMounted) {
          setIsAdmin(false)
          setCheckingAdmin(false)
        }
        return
      }
      
      try {
        // 먼저 AuthContext에서 currentUser의 email 사용 (가장 확실함)
        let userEmail = null
        if (currentUser && currentUser.email) {
          userEmail = currentUser.email
          console.log('✅ AuthContext에서 email 획득:', userEmail)
        }
        
        // localStorage에서 토큰 확인
        console.log('🔍 localStorage에서 토큰 확인...')
        let accessToken = null
        
        // 여러 가능한 localStorage 키 확인
        const tokenKeys = [
          'supabase_access_token',
          'sb-access-token',
          `sb-${window.location.hostname === 'localhost' ? 'localhost' : 'supabase'}-auth-token`
        ]
        
        // localStorage의 모든 키 확인 (sb-로 시작하는 키들)
        try {
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i)
            if (key && (key.includes('auth-token') || key.includes('access-token'))) {
              const value = localStorage.getItem(key)
              try {
                const parsed = JSON.parse(value)
                if (parsed && parsed.access_token) {
                  accessToken = parsed.access_token
                  console.log(`✅ localStorage에서 토큰 발견: ${key}`)
                  break
                }
              } catch {
                // JSON이 아니면 그대로 사용
                if (value && value.length > 50) {
                  accessToken = value
                  console.log(`✅ localStorage에서 토큰 발견 (문자열): ${key}`)
                  break
                }
              }
            }
          }
        } catch (e) {
          console.warn('⚠️ localStorage 검색 중 오류:', e)
        }
        
        // localStorage에서 직접 찾지 못했으면 Supabase 세션 가져오기 시도 (타임아웃 설정)
        if (!accessToken) {
          console.log('🔍 localStorage에 토큰 없음, Supabase 세션 가져오기...')
          try {
            // Supabase 세션 가져오기에 타임아웃 설정 (3초)
            const sessionPromise = supabase.auth.getSession()
            const timeoutPromise = new Promise((_, reject) => {
              setTimeout(() => reject(new Error('세션 가져오기 타임아웃')), 3000)
            })
            
            const session = await Promise.race([sessionPromise, timeoutPromise])
            accessToken = session?.data?.session?.access_token
            console.log('🔍 세션에서 토큰 획득:', !!accessToken)
          } catch (sessionError) {
            console.warn('⚠️ 세션 가져오기 실패 (무시하고 계속):', sessionError.message)
            // Supabase 오류는 무시하고 email만으로 진행
          }
        }
        
        // email이 없으면 API 호출 불가
        if (!userEmail) {
          console.warn('⚠️ email을 찾을 수 없습니다.')
          if (isMounted) {
            setIsAdmin(false)
            setCheckingAdmin(false)
          }
          return
        }
        
        console.log('🔍 API 호출 준비 완료 - email:', userEmail, '토큰 존재:', !!accessToken)
        
        // AbortController로 요청 취소 가능하게 만들기
        abortController = new AbortController()
        
        // 타임아웃 설정 (10초로 증가 - 네트워크 지연 대응)
        timeoutId = setTimeout(() => {
          console.warn('⏱️ API 호출 타임아웃 (10초 초과)')
          if (abortController) {
            abortController.abort()
          }
        }, 10000)
        
        // 백엔드 API로 관리자 권한 확인
        console.log('🔍 /api/users/check-admin 호출 중...')
        const headers = {
          'Content-Type': 'application/json'
        }
        
        // 토큰이 있으면 Authorization 헤더 추가
        if (accessToken) {
          headers['Authorization'] = `Bearer ${accessToken}`
        }
        
        // email이 있으면 X-User-Email 헤더 추가 (백엔드에서 사용 가능)
        if (userEmail) {
          headers['X-User-Email'] = userEmail
        }
        
        const response = await fetch('/api/users/check-admin', {
          method: 'GET',
          headers: headers,
          signal: abortController.signal
        })
        
        // 타임아웃 클리어
        if (timeoutId) {
          clearTimeout(timeoutId)
          timeoutId = null
        }
        
        if (!isMounted) {
          console.log('⚠️ 컴포넌트가 언마운트되어 응답 무시')
          return
        }
        
        console.log('✅ API 응답 받음, status:', response.status)
        
        // 응답이 성공이든 실패든 항상 JSON 파싱 시도
        let data
        try {
          data = await response.json()
        } catch (parseError) {
          console.error('❌ 응답 JSON 파싱 실패:', parseError)
          data = { is_admin: false, error: '응답 파싱 실패' }
        }
        
        console.log('✅ 관리자 권한 확인 응답:', data, 'status:', response.status)
        
        // 디버깅 정보 출력
        if (data.debug) {
          console.log('🔍 디버깅 정보:', data.debug)
          if (data.debug.jwt_user_id && data.debug.user_external_uid) {
            console.log(`🔍 JWT user_id: ${data.debug.jwt_user_id}`)
            console.log(`🔍 DB external_uid: ${data.debug.user_external_uid}`)
            if (data.debug.jwt_user_id !== data.debug.user_external_uid) {
              console.error('❌ JWT의 user_id와 DB의 external_uid가 일치하지 않습니다!')
              console.error('   이것이 관리자 접속이 안 되는 원인일 수 있습니다.')
            }
          }
        }
        
        if (isMounted) {
          // 응답이 성공이든 실패든 is_admin 값으로 설정
          const adminStatus = data.is_admin === true
          setIsAdmin(adminStatus)
          setCheckingAdmin(false)
          
          console.log(`✅ 관리자 권한 체크 완료 - isAdmin: ${adminStatus}`)
          
          if (response.status !== 200 || data.error) {
            console.warn('⚠️ 관리자 권한 확인 경고:', data.error || '알 수 없는 오류')
          }
          
          if (!data.is_admin && data.debug) {
            console.error('❌ 관리자 권한이 없습니다. 디버깅 정보를 확인하세요.')
          }
          
          // 관리자 권한이 확인되면 데이터 로드 시작
          if (adminStatus) {
            console.log('✅ 관리자 권한 확인됨, 데이터 로드 시작...')
          }
        }
      } catch (error) {
        // 타임아웃 클리어
        if (timeoutId) {
          clearTimeout(timeoutId)
          timeoutId = null
        }
        
        // AbortError는 React Strict Mode에서 정상적인 동작이므로 조용히 처리
        if (error.name === 'AbortError') {
          // AbortError는 무시하고 조용히 종료
          return
        }
        
        console.error('❌ 관리자 권한 체크 오류 발생!')
        console.error('❌ 오류 타입:', error.name)
        console.error('❌ 오류 메시지:', error.message)
        console.error('❌ 전체 오류 객체:', error)
        
        // AbortError는 React Strict Mode에서 정상적인 동작 (컴포넌트 언마운트 시 요청 취소)
        if (error.name === 'AbortError') {
          // AbortError는 무시 (컴포넌트가 언마운트되었거나 cleanup이 실행된 경우)
          console.log('ℹ️ API 호출이 취소되었습니다 (컴포넌트 언마운트 또는 cleanup)')
          // AbortError는 상태를 변경하지 않음 (이미 언마운트되었거나 다음 렌더링에서 처리됨)
          return
        } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
          console.error('❌ 네트워크 오류 또는 CORS 문제일 수 있습니다.')
          console.error('❌ API 서버가 실행 중인지 확인하세요.')
        } else {
          console.error('❌ 알 수 없는 오류:', error)
          if (error.stack) {
            console.error('❌ 스택 트레이스:', error.stack)
          }
        }
        
        if (isMounted) {
          setIsAdmin(false)
          setCheckingAdmin(false)
        }
      }
    }
    
    checkAdminAccess()
    
    // 클린업 함수
    return () => {
      console.log('🧹 관리자 권한 체크 클린업')
      isMounted = false
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      if (abortController) {
        abortController.abort()
      }
    }
  }, [currentUser])
  
  // 추가 안전장치: 10초 이상 checkingAdmin이 true면 자동으로 false로 변경
  useEffect(() => {
    if (checkingAdmin) {
      const fallbackTimeout = setTimeout(() => {
        console.warn('⚠️ 관리자 권한 체크가 10초 이상 지연되었습니다. 자동으로 일반 사용자로 처리합니다.')
        console.warn('⚠️ 이는 네트워크 문제이거나 백엔드 서버가 응답하지 않는 것일 수 있습니다.')
        setIsAdmin(false)
        setCheckingAdmin(false)
      }, 10000)
      
      return () => clearTimeout(fallbackTimeout)
    }
  }, [checkingAdmin])
  
  // 관리자 API 호출 헬퍼 함수 - Authorization 헤더 사용
  const adminFetch = async (url, options = {}) => {
    try {
      console.log(`📡 adminFetch 호출: ${url}`)
      
      // 토큰 가져오기 (여러 방법 시도)
      let accessToken = null
      
      // 방법 1: Supabase 세션에서 가져오기 (타임아웃 증가)
      try {
        const sessionPromise = supabase.auth.getSession()
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('세션 가져오기 타임아웃')), 5000)
        })
        const session = await Promise.race([sessionPromise, timeoutPromise])
        accessToken = session.data?.session?.access_token
        if (accessToken) {
          console.log(`🔑 토큰 획득 (Supabase 세션): ${accessToken.substring(0, 20)}...`)
        }
      } catch (tokenError) {
        console.warn('⚠️ Supabase 세션에서 토큰 가져오기 실패:', tokenError.message)
      }
      
      // 방법 2: localStorage에서 직접 가져오기
      if (!accessToken) {
        try {
          // 모든 localStorage 키 확인
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i)
            if (key && (key.includes('supabase') || key.includes('auth') || key.includes('token'))) {
              const stored = localStorage.getItem(key)
              if (stored) {
                try {
                  const parsed = JSON.parse(stored)
                  if (parsed && parsed.access_token) {
                    accessToken = parsed.access_token
                    console.log(`🔑 토큰 획득 (localStorage: ${key}): ${accessToken.substring(0, 20)}...`)
                    break
                  }
                } catch (e) {
                  // JSON이 아니면 그냥 문자열로 사용 (JWT는 보통 eyJ로 시작)
                  if (stored.startsWith('eyJ')) {
                    accessToken = stored
                    console.log(`🔑 토큰 획득 (localStorage: ${key}, raw): ${accessToken.substring(0, 20)}...`)
                    break
                  }
                }
              }
            }
          }
        } catch (localStorageError) {
          console.warn('⚠️ localStorage에서 토큰 가져오기 실패:', localStorageError.message)
        }
      }
      
      if (!accessToken) {
        console.warn('⚠️ 토큰을 찾을 수 없습니다. X-User-Email 헤더로 진행합니다.')
      }
      
      const defaultHeaders = {
        'Content-Type': 'application/json'
      }
      
      if (accessToken) {
        defaultHeaders['Authorization'] = `Bearer ${accessToken}`
        console.log(`🔑 Authorization 헤더 추가: Bearer ${accessToken.substring(0, 20)}...`)
      }
      
      // currentUser의 email 추가 (필수)
      const userEmail = currentUser?.email || currentUser?.user?.email
      if (userEmail) {
        defaultHeaders['X-User-Email'] = userEmail
        console.log(`📧 X-User-Email 헤더 추가: ${userEmail}`)
      } else {
        console.warn('⚠️ currentUser.email이 없습니다. 인증이 실패할 수 있습니다.')
        console.warn('⚠️ currentUser 객체:', currentUser)
      }
      
      console.log(`📤 요청 헤더 키:`, Object.keys(defaultHeaders))
      
      const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers
      }
    })
      
      console.log(`📥 응답 상태: ${response.status} ${response.statusText}`)
      
      return response
    } catch (error) {
      console.error(`❌ adminFetch 오류 (${url}):`, error)
      throw error
    }
  }
  
  // ⚠️ 중요: React Hooks 규칙 - 모든 hooks는 조건부 return 전에 선언되어야 함
  // 상태 관리
  const [activeTab, setActiveTab] = useState('dashboard')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  
  // 탭별 상태 유지를 위한 상태
  const [tabStates, setTabStates] = useState({
    dashboard: { lastUpdate: null },
    users: { searchTerm: '', lastUpdate: null },
    orders: { searchTerm: '', lastUpdate: null },
    purchases: { searchTerm: '', statusFilter: 'all', lastUpdate: null },
    referrals: { lastUpdate: null },
    notices: { lastUpdate: null }
  })

  // 대시보드 데이터
  const [dashboardData, setDashboardData] = useState({
    totalUsers: 0,
    totalOrders: 0,
    totalRevenue: 0,
    pendingPurchases: 0,
    todayOrders: 0,
    todayRevenue: 0,
    monthlyRevenue: 0
  })

  // 사용자 데이터
  const [users, setUsers] = useState([])

  // 주문 데이터
  const [orders, setOrders] = useState([])

  // 포인트 구매 신청 데이터
  const [pendingPurchases, setPendingPurchases] = useState([])

  // 추천인 데이터
  const [referrals, setReferrals] = useState([])
  const [showReferralModal, setShowReferralModal] = useState(false)
  const [showReferralDetailModal, setShowReferralDetailModal] = useState(false)
  const [selectedReferralCode, setSelectedReferralCode] = useState(null)
  const [filteredPurchases, setFilteredPurchases] = useState([])
  
  // 공지사항 데이터
  const [notices, setNotices] = useState([])
  const [showNoticeModal, setShowNoticeModal] = useState(false)
  const [editingNotice, setEditingNotice] = useState(null)
  const [noticeForm, setNoticeForm] = useState({
    title: '',
    content: '',
    image_url: '',
    login_popup_image_url: '',
    popup_type: 'notice', // 'notice' or 'login'
    is_active: true
  })
  const [uploadingImage, setUploadingImage] = useState(false)
  const [referralCodes, setReferralCodes] = useState([])
  const [referralCommissions, setReferralCommissions] = useState([])
  
  // 추천인 커미션 관리 상태
  const [commissionOverview, setCommissionOverview] = useState([])
  const [commissionStats, setCommissionStats] = useState({})
  const [paymentHistory, setPaymentHistory] = useState([])
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [selectedReferrer, setSelectedReferrer] = useState(null)
  const [paymentData, setPaymentData] = useState({
    amount: '',
    payment_method: 'bank_transfer',
    notes: ''
  })

  // 관리자 권한 확인 후 데이터 로드
  useEffect(() => {
    // 관리자 권한이 확인되고 로딩이 완료된 경우에만 데이터 로드
    console.log(`🔍 데이터 로드 체크 - isAdmin: ${isAdmin}, checkingAdmin: ${checkingAdmin}`)
    if (isAdmin === true && checkingAdmin === false) {
      console.log('✅ 관리자 권한 확인 완료, 데이터 로드 시작...')
      try {
    loadAdminData()
    loadReferralData()
    loadCommissionData()
      } catch (error) {
        console.error('❌ 데이터 로드 중 오류:', error)
      }
    } else if (isAdmin === false && checkingAdmin === false) {
      console.log('⚠️ 관리자 권한이 없어 데이터 로드를 건너뜁니다.')
    } else {
      console.log('⏳ 관리자 권한 확인 대기 중...')
    }
  }, [isAdmin, checkingAdmin])

  // 탭 변경 시 해당 탭 데이터 로드
  useEffect(() => {
    if (activeTab === 'purchases') {
      loadPendingPurchases()
    }
  }, [activeTab])

  // 구매 신청 검색 및 상태 필터링
  useEffect(() => {
    const searchTerm = tabStates.purchases.searchTerm || ''
    const statusFilter = tabStates.purchases.statusFilter || 'all'
    
    const filtered = (pendingPurchases || []).filter(purchase => {
      try {
        // 상태 필터링
        if (statusFilter !== 'all') {
          const purchaseStatus = purchase.status || 'pending'
          if (statusFilter === 'pending' && purchaseStatus !== 'pending') {
            return false
          }
          if (statusFilter === 'approved' && purchaseStatus !== 'approved') {
            return false
          }
          if (statusFilter === 'rejected' && purchaseStatus !== 'rejected') {
            return false
          }
        }
        
        // 검색어 필터링
        if (searchTerm) {
          const userId = String(purchase?.userId || '')
          const email = String(purchase?.email || '')
          const buyerName = String(purchase?.buyerName || '')
          const searchLower = String(searchTerm || '').toLowerCase()
          
          return userId.toLowerCase().includes(searchLower) ||
                 email.toLowerCase().includes(searchLower) ||
                 buyerName.toLowerCase().includes(searchLower)
        }
        
        return true
      } catch (error) {
        return false
      }
    })
    setFilteredPurchases(filtered)
  }, [pendingPurchases, tabStates.purchases.searchTerm, tabStates.purchases.statusFilter])

  // 검색어 업데이트 함수들
  const updateSearchTerm = (tab, searchTerm) => {
    setTabStates(prev => ({
      ...prev,
      [tab]: { ...prev[tab], searchTerm }
    }))
  }

  // 날짜 포맷팅 함수
  const formatDate = (dateString) => {
    if (!dateString || dateString === 'N/A') return 'N/A'
    try {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch (error) {
      return dateString
    }
  }

  // 안전한 숫자 포맷팅 함수
  const formatNumber = (value) => {
    if (value === null || value === undefined || isNaN(value)) return '0'
    try {
      return Number(value).toLocaleString()
    } catch (error) {
      return '0'
    }
  }

  // 관리자 데이터 로드
  const loadAdminData = async () => {
    console.log('🔄 loadAdminData 시작...')
    setIsLoading(true)
    setError(null)

    try {
      console.log('📊 대시보드 통계 로드 시작...')
      // 대시보드 통계 로드
      await loadDashboardStats()
      console.log('✅ 대시보드 통계 로드 완료')
      
      console.log('📦 주문 데이터 로드 시작...')
      // 주문 데이터 로드
      await loadOrders()
      console.log('✅ 주문 데이터 로드 완료')
      
      console.log('💰 포인트 구매 신청 로드 시작...')
      // 포인트 구매 신청 로드
      await loadPendingPurchases()
      console.log('✅ 포인트 구매 신청 로드 완료')
      
      setLastUpdate(new Date().toLocaleString())
      console.log('✅ loadAdminData 완료')
    } catch (error) {
      console.error('❌ loadAdminData 오류:', error)
      setError('데이터를 불러오는 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
      console.log('🏁 loadAdminData 종료 (isLoading: false)')
    }
  }

  // 대시보드 통계 로드
  const loadDashboardStats = async () => {
    try {
      console.log('📡 /api/admin/stats API 호출 중...')
      const response = await adminFetch('/api/admin/stats')
      console.log('📡 /api/admin/stats 응답 상태:', response.status)
      
      if (response.ok) {
        const data = await response.json()
        console.log('📊 대시보드 통계 데이터:', data)
        setDashboardData({
          totalUsers: data.total_users || 0,
          totalOrders: data.total_orders || 0,
          totalRevenue: data.total_revenue || 0,
          pendingPurchases: data.pending_purchases || 0,
          todayOrders: data.today_orders || 0,
          todayRevenue: data.today_revenue || 0,
          monthlyRevenue: data.monthly_sales || 0
        })
        console.log('✅ 대시보드 데이터 설정 완료')
      } else {
        const errorText = await response.text().catch(() => '')
        console.error('❌ 대시보드 통계 로드 실패:', response.status, errorText)
      }
    } catch (error) {
      console.error('❌ 대시보드 통계 로드 오류:', error)
    }
  }

  // 사용자 데이터 로드
  const loadUsers = async () => {
    try {
      const response = await adminFetch('/api/admin/users')
      
      if (response.ok) {
      const data = await response.json()
        // API 응답을 프론트엔드 형식으로 변환
        const transformedUsers = Array.isArray(data.users) ? 
          data.users.map(user => ({
            userId: user.user_id || user.userId,
            email: user.email,
            name: user.name || user.displayName,
            points: user.points || 0,
            createdAt: user.created_at || user.createdAt,
            lastActivity: user.last_activity || user.lastActivity || user.last_login || 'N/A'
          })) : []
        
        setUsers(transformedUsers)
      }
    } catch (error) {
      setUsers([])
    }
  }

  // 주문 데이터 로드
  const loadOrders = async () => {
    try {
      console.log('📡 /api/admin/transactions API 호출 중...')
      const response = await adminFetch('/api/admin/transactions')
      console.log('📡 /api/admin/transactions 응답 상태:', response.status)
      
      if (response.ok) {
        const data = await response.json()
        console.log('📦 주문 데이터 원본:', data)
        // API 응답을 프론트엔드 형식으로 변환
        const transformedOrders = Array.isArray(data.transactions || data.orders) ? 
          (data.transactions || data.orders).map(order => ({
            orderId: order.order_id || order.orderId || order.id,
            userId: order.user_id || order.userId,
            platform: order.platform || order.service_platform || 'N/A',
            service: order.service_name || order.service || order.service_type || 'N/A',
            serviceId: order.service_id || order.serviceId || 'N/A',
            quantity: order.quantity || order.service_quantity || 0,
            amount: order.price || order.amount || order.total_price || 0,
            status: order.status || 'pending',
            createdAt: order.created_at || order.createdAt || order.order_date,
            link: (order.link && order.link !== 'N/A' && order.link !== 'null' && order.link.trim() !== '') 
              ? order.link 
              : 'N/A',
            comments: order.comments || order.remarks || 'N/A',
            smmPanelOrderId: order.smm_panel_order_id || order.smmPanelOrderId || null
          })) : []
        
        console.log('✅ 변환된 주문 데이터:', transformedOrders.length, '개')
        setOrders(transformedOrders)
      } else {
        const errorText = await response.text().catch(() => '')
        console.error('❌ 주문 데이터 로드 실패:', response.status, errorText)
        setOrders([])
      }
    } catch (error) {
      console.error('❌ 주문 데이터 로드 오류:', error)
      setOrders([])
    }
  }

  // 포인트 구매 신청 로드
  const loadPendingPurchases = async () => {
    try {
      console.log('🔍 포인트 구매 신청 목록 로드 시작')
      const response = await adminFetch('/api/admin/purchases')
      
      if (response.ok) {
        const data = await response.json()
        console.log('✅ 포인트 구매 신청 데이터:', data)
        // API 응답을 프론트엔드 형식으로 변환
        const transformedPurchases = Array.isArray(data.purchases) ? 
          data.purchases.map(purchase => ({
            id: purchase.id,
            userId: purchase.user_id,
            email: purchase.email || 'N/A',
            points: purchase.amount,
            amount: purchase.price,
            createdAt: purchase.created_at,
            status: purchase.status,
            buyerName: purchase.buyer_name || 'N/A',
            bankInfo: purchase.bank_info || 'N/A'
          })) : []
        
        console.log(`✅ 변환된 포인트 구매 신청: ${transformedPurchases.length}건`)
        setPendingPurchases(transformedPurchases)
        setFilteredPurchases(transformedPurchases)
      } else {
        const errorData = await response.json().catch(() => ({}))
        console.error('❌ 포인트 구매 신청 목록 조회 실패:', response.status, errorData)
        setPendingPurchases([])
        setFilteredPurchases([])
      }
    } catch (error) {
      console.error('❌ 포인트 구매 신청 목록 로드 오류:', error)
      setPendingPurchases([])
      setFilteredPurchases([])
    }
  }

  // 포인트 구매 신청 승인
  const handleApprovePurchase = async (purchaseId) => {
    try {
      const response = await adminFetch(`/api/admin/purchases/${purchaseId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: 'approved' })
      })

      if (response.ok) {
        alert('포인트 구매 신청이 승인되었습니다.')
        // 현재 상태를 유지하면서 특정 항목만 업데이트
        setPendingPurchases(prevPurchases => 
          prevPurchases.map(purchase => 
            purchase.id === purchaseId 
              ? { ...purchase, status: 'approved' }
              : purchase
          )
        )
        // 통계만 업데이트 (전체 데이터 새로고침 없이)
        loadDashboardStats()
      } else {
        alert('승인 처리 중 오류가 발생했습니다.')
      }
    } catch (error) {
      alert('승인 처리 중 오류가 발생했습니다.')
    }
  }

  // 포인트 구매 신청 거절
  const handleRejectPurchase = async (purchaseId) => {
    try {
      const response = await adminFetch(`/api/admin/purchases/${purchaseId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: 'rejected' })
      })

      if (response.ok) {
        alert('포인트 구매 신청이 거절되었습니다.')
        // 현재 상태를 유지하면서 특정 항목만 업데이트
        setPendingPurchases(prevPurchases => 
          prevPurchases.map(purchase => 
            purchase.id === purchaseId 
              ? { ...purchase, status: 'rejected' }
              : purchase
          )
        )
        // 통계만 업데이트 (전체 데이터 새로고침 없이)
        loadDashboardStats()
      } else {
        alert('거절 처리 중 오류가 발생했습니다.')
      }
    } catch (error) {
      alert('거절 처리 중 오류가 발생했습니다.')
    }
  }

  // 데이터 내보내기 함수
  // 공지사항 데이터 로드
  const loadNotices = async () => {
    try {
      const response = await adminFetch('/api/admin/notices')
      if (response.ok) {
        const data = await response.json()
        setNotices(data.notices || [])
      }
    } catch (error) {
      console.error('팝업 로드 실패:', error)
    }
  }

  // 이미지 업로드
  const handleImageUpload = async (file, type = 'notice') => {
    try {
      setUploadingImage(true)
      
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await adminFetch('/api/admin/upload-image', {
        method: 'POST',
        body: formData
      })
      
      if (response.ok) {
        const data = await response.json()
        if (type === 'login') {
          setNoticeForm({...noticeForm, login_popup_image_url: data.image_url})
        } else {
          setNoticeForm({...noticeForm, image_url: data.image_url})
        }
        alert('이미지가 업로드되었습니다.')
      } else {
        const errorData = await response.json()
        alert(`이미지 업로드 실패: ${errorData.error}`)
      }
    } catch (error) {
      alert('이미지 업로드 중 오류가 발생했습니다.')
    } finally {
      setUploadingImage(false)
    }
  }

  // 공지사항 생성/수정
  const handleNoticeSubmit = async () => {
    try {
      setIsLoading(true)
      
      const url = editingNotice 
        ? `/api/admin/notices/${editingNotice.id}`
        : '/api/admin/notices'
      
      const method = editingNotice ? 'PUT' : 'POST'
      
      const response = await adminFetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(noticeForm)
      })
      
      if (response.ok) {
        await loadNotices()
        setShowNoticeModal(false)
        setEditingNotice(null)
        setNoticeForm({
          title: '',
          content: '',
          image_url: '',
          login_popup_image_url: '',
          popup_type: 'notice',
          is_active: true
        })
        alert(editingNotice ? '팝업이 수정되었습니다.' : '팝업이 생성되었습니다.')
      } else {
        const errorData = await response.json()
        alert(`오류: ${errorData.error}`)
      }
    } catch (error) {
      alert('팝업 처리 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 공지사항 삭제
  const handleDeleteNotice = async (noticeId) => {
    if (!confirm('정말로 이 팝업을 삭제하시겠습니까?')) return
    
    try {
      const response = await adminFetch(`/api/admin/notices/${noticeId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        await loadNotices()
        alert('팝업이 삭제되었습니다.')
      } else {
        const errorData = await response.json()
        alert(`오류: ${errorData.error}`)
      }
    } catch (error) {
      alert('팝업 삭제 중 오류가 발생했습니다.')
    }
  }

  // 공지사항 수정 모달 열기
  const handleEditNotice = (notice) => {
    setEditingNotice(notice)
    setNoticeForm({
      title: notice.title || '',
      content: notice.content || '',
      image_url: notice.image_url || '',
      login_popup_image_url: notice.login_popup_image_url || '',
      popup_type: notice.popup_type || 'notice',
      is_active: notice.is_active !== undefined ? notice.is_active : true
    })
    setShowNoticeModal(true)
  }

  // 주문 상태 텍스트 변환
  const getOrderStatusText = (status) => {
    switch (status?.toLowerCase()) {
      case 'pending':
        return '주문 접수'
      case 'processing':
      case 'in_progress':
        return '작업중'
      case 'completed':
        return '작업완료'
      default:
        return '주문 접수'
    }
  }

  // 주문 상태 클래스 변환 (4개 상태로 통일)
  const getOrderStatusClass = (status) => {
    switch (status) {
      case '주문 실행완료':
        return 'completed'
      case '주문 실행중':
        return 'processing'
      case '주문발송':
        return 'pending'
      case '주문 미처리':
        return 'canceled'
      default:
        return 'pending'
    }
  }


  // 주문 접수 처리
  const handleOrderReceive = async (orderId) => {
    if (!confirm('이 주문을 접수 처리하시겠습니까?')) return
    
    try {
      setIsLoading(true)
      const response = await adminFetch(`/api/orders/${orderId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: 'processing' })
      })
      
      if (response.ok) {
        await loadOrders()
        alert('주문이 접수되었습니다.')
      } else {
        const errorData = await response.json().catch(() => ({ error: '알 수 없는 오류' }))
        alert(`오류: ${errorData.error || '주문 접수 실패'}`)
      }
    } catch (error) {
      console.error('주문 접수 오류:', error)
      alert('주문 접수 처리 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 강제완료 처리
  const handleForceComplete = async (orderId) => {
    if (!confirm('이 주문을 강제완료 처리하시겠습니까?')) return
    
    try {
      setIsLoading(true)
      const response = await adminFetch(`/api/orders/${orderId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: 'completed' })
      })
      
      if (response.ok) {
        await loadOrders()
        alert('주문이 강제완료 처리되었습니다.')
      } else {
        const errorData = await response.json().catch(() => ({ error: '알 수 없는 오류' }))
        alert(`오류: ${errorData.error || '강제완료 실패'}`)
      }
    } catch (error) {
      console.error('강제완료 오류:', error)
      alert('강제완료 처리 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 추천인 데이터 로드
  const loadReferralData = async () => {
    try {
      console.log('🔄 추천인 데이터 로드 시작...')
      
      // 서버에서 데이터 로드
      const [codesResponse, referralsResponse, payoutRequestsResponse] = await Promise.all([
        adminFetch('/api/admin/referral/codes'),
        adminFetch('/api/admin/referral/list'),
        adminFetch('/api/admin/payout-requests')
      ])
      
      console.log('📡 API 응답 상태:', {
        codes: codesResponse.status,
        referrals: referralsResponse.status,
        payoutRequests: payoutRequestsResponse.status
      })
      
      if (codesResponse.ok) {
        const codesData = await codesResponse.json()
        console.log('📋 추천인 코드 API 응답:', codesData)
        setReferralCodes(codesData.codes || [])
        console.log('✅ 추천인 코드 데이터 로드 완료:', codesData.codes?.length || 0, '개')
      } else {
        console.error('❌ 추천인 코드 로드 실패:', codesResponse.status)
        setReferralCodes([])
      }
      
      if (referralsResponse.ok) {
        const referralsData = await referralsResponse.json()
        console.log('📋 추천인 목록 API 응답:', referralsData)
        setReferrals(referralsData.referrals || [])
        console.log('✅ 추천인 목록 데이터 로드 완료:', referralsData.referrals?.length || 0, '개')
      } else {
        console.error('❌ 추천인 목록 로드 실패:', referralsResponse.status)
        setReferrals([])
      }
      
      if (payoutRequestsResponse.ok) {
        const payoutData = await payoutRequestsResponse.json()
        console.log('📋 커미션 환급 신청 API 응답:', payoutData)
        // payout_requests를 referralCommissions에 매핑 (기존 구조 유지)
        const mappedCommissions = (payoutData.payout_requests || []).map(req => ({
          request_id: req.request_id,
          referred_user_id: req.referrer_name || req.referrer_email || 'N/A',
          purchase_amount: 0, // 환급 신청이므로 구매 금액은 0
          commission_amount: parseFloat(req.amount) || 0,
          commission_rate: 0, // 환급 신청이므로 커미션율은 없음
          created_at: req.created_at || req.requested_at,
          status: req.status || 'requested',
          referrer_email: req.referrer_email,
          referrer_name: req.referrer_name,
          phone: req.phone,
          bank_name: req.bank_name,
          account_number: req.account_number,
          user_id: req.user_id
        }))
        setReferralCommissions(mappedCommissions)
        console.log('✅ 커미션 환급 신청 데이터 로드 완료:', mappedCommissions.length || 0, '개')
      } else {
        console.error('❌ 커미션 환급 신청 로드 실패:', payoutRequestsResponse.status)
        setReferralCommissions([])
      }
      
      console.log('🎉 추천인 데이터 로드 완료!')
    } catch (error) {
      console.error('추천인 데이터 로드 실패:', error)
      // 폴백으로 로컬 스토리지 사용
      const codes = getReferralCodes()
      const referrals = getReferrals()
      const commissions = getCommissions()
      
      setReferralCodes(codes)
      setReferrals(referrals)
      setReferralCommissions(commissions)
    }
  }

  // 커미션 데이터 로드 (환급신청 포함)
  const loadCommissionData = async () => {
    console.log('🔄 loadCommissionData 시작...')
    try {
      console.log('📡 커미션 관련 API 호출 중...')
      const [overviewResponse, historyResponse, payoutRequestsResponse] = await Promise.all([
        adminFetch('/api/admin/referral/commission-overview'),
        adminFetch('/api/admin/referral/payment-history'),
        adminFetch('/api/admin/payout-requests')
      ])
      
      console.log('📡 커미션 API 응답 상태:', {
        overview: overviewResponse.status,
        history: historyResponse.status,
        payoutRequests: payoutRequestsResponse.status
      })
      
      if (overviewResponse.ok) {
        const overviewData = await overviewResponse.json()
        console.log('📊 커미션 개요 데이터:', overviewData)
        setCommissionOverview(overviewData.overview || [])
        setCommissionStats(overviewData.stats || {})
        console.log('✅ 커미션 개요 데이터 설정 완료')
      } else {
        console.error('❌ 커미션 개요 로드 실패:', overviewResponse.status)
      }
      
      if (historyResponse.ok) {
        const historyData = await historyResponse.json()
        console.log('📊 결제 내역 데이터:', historyData)
        setPaymentHistory(historyData.payments || historyData.payout_requests || [])
        console.log('✅ 결제 내역 데이터 설정 완료')
      } else {
        console.error('❌ 결제 내역 로드 실패:', historyResponse.status)
      }
      
      if (payoutRequestsResponse.ok) {
        const payoutData = await payoutRequestsResponse.json()
        console.log('📊 환급 신청 데이터:', payoutData)
        setPaymentHistory(payoutData.payout_requests || payoutData.requests || [])
        console.log('✅ 환급 신청 데이터 설정 완료')
      } else {
        console.error('❌ 환급 신청 로드 실패:', payoutRequestsResponse.status)
      }
      
      console.log('✅ loadCommissionData 완료')
    } catch (error) {
      console.error('❌ 커미션 데이터 로드 실패:', error)
    }
  }

  // 환급신청 승인
  const handleApprovePayoutRequest = async (requestId) => {
    if (!confirm('환급신청을 승인하시겠습니까?')) return
    
    try {
      const response = await adminFetch(`/api/admin/payout-requests/${requestId}/approve`, {
        method: 'PUT'
      })
      
      if (response.ok) {
        await loadReferralData() // 환급 신청 목록 새로고침
        alert('환급신청이 승인되었습니다.')
      } else {
        const errorData = await response.json()
        alert(`승인 실패: ${errorData.error}`)
      }
    } catch (error) {
      console.error('환급신청 승인 실패:', error)
      alert('환급신청 승인에 실패했습니다.')
    }
  }
  
  // 환급신청 거절
  const handleRejectPayoutRequest = async (requestId) => {
    if (!confirm('환급신청을 거절하시겠습니까?')) return
    
    try {
      const response = await adminFetch(`/api/admin/payout-requests/${requestId}/reject`, {
        method: 'PUT'
      })
      
      if (response.ok) {
        await loadReferralData() // 환급 신청 목록 새로고침
        alert('환급신청이 거절되었습니다.')
      } else {
        const errorData = await response.json()
        alert(`거절 실패: ${errorData.error}`)
      }
    } catch (error) {
      console.error('환급신청 거절 실패:', error)
      alert('환급신청 거절에 실패했습니다.')
    }
  }

  // 추천인별 커미션 비율 변경
  const handleUpdateCommissionRate = async (referrerEmail, referrerUserId, currentRate) => {
    const newRate = prompt(`커미션 비율을 입력하세요 (0~1, 현재: ${(currentRate * 100).toFixed(1)}%):`, currentRate);
    
    if (newRate === null) return; // 취소
    
    const rate = parseFloat(newRate);
    if (isNaN(rate) || rate < 0 || rate > 1) {
      alert('커미션 비율은 0과 1 사이의 값이어야 합니다.');
      return;
    }
    
    try {
      setIsLoading(true);
      const response = await adminFetch('/api/admin/referral/update-commission-rate', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          referrer_email: referrerEmail,
          referrer_user_id: referrerUserId,
          commission_rate: rate
        })
      });
      
      if (response.ok) {
        await loadCommissionData();
        alert(`커미션 비율이 ${(rate * 100).toFixed(1)}%로 변경되었습니다.`);
      } else {
        const errorData = await response.json();
        alert(`오류: ${errorData.error}`);
      }
    } catch (error) {
      alert('커미션 비율 변경 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  // 커미션 환급 처리
  const handleCommissionPayment = async () => {
    try {
      const response = await adminFetch('/api/admin/referral/pay-commission', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          referrer_email: selectedReferrer.referrer_email,
          amount: parseFloat(paymentData.amount),
          payment_method: paymentData.payment_method,
          notes: paymentData.notes
        })
      })

      if (response.ok) {
        alert('커미션이 성공적으로 환급되었습니다!')
        setShowPaymentModal(false)
        setSelectedReferrer(null)
        setPaymentData({ amount: '', payment_method: 'bank_transfer', notes: '' })
        loadCommissionData() // 데이터 새로고침
      } else {
        const errorData = await response.json()
        alert(`환급 실패: ${errorData.error}`)
      }
    } catch (error) {
      console.error('커미션 환급 실패:', error)
      alert('커미션 환급 중 오류가 발생했습니다.')
    }
  }

  // 환급 모달 열기
  const openPaymentModal = (referrer) => {
    setSelectedReferrer(referrer)
    setPaymentData({
      amount: referrer.unpaid_commission.toString(),
      payment_method: 'bank_transfer',
      notes: ''
    })
    setShowPaymentModal(true)
  }

  // 모든 추천인 코드 활성화
  const handleActivateAllCodes = async () => {
    try {
      const response = await adminFetch('/api/admin/referral/activate-all', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (response.ok) {
        const result = await response.json()
        alert(result.message)
        
        // 강제 새로고침 - 즉시 실행
        await loadReferralData()
        console.log('🔄 추천인 데이터 강제 새로고침 완료')
        
        // 추가 새로고침 - 3초 후
        setTimeout(async () => {
          await loadReferralData()
          console.log('🔄 추천인 데이터 추가 새로고침 완료')
        }, 3000)
      } else {
        const errorData = await response.json()
        alert(`활성화 실패: ${errorData.error}`)
      }
    } catch (error) {
      console.error('코드 활성화 오류:', error)
      alert('코드 활성화 중 오류가 발생했습니다.')
    }
  }

  // 추천인 등록 성공 핸들러
  const handleReferralRegistrationSuccess = async (result) => {
    try {
      // 서버에 추천인 등록
      const response = await adminFetch('/api/admin/referral/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: result.email,
          name: result.name,
          phone: result.phone
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        // 데이터 다시 로드
        await loadReferralData()
        alert(`추천인이 성공적으로 등록되었습니다!\n이메일: ${data.email}\n추천인 코드: ${data.referralCode}`)
      } else {
        const errorData = await response.json()
        alert(`추천인 등록 실패: ${errorData.error}`)
      }
    } catch (error) {
      console.error('추천인 등록 실패:', error)
      alert('추천인 등록 중 오류가 발생했습니다.')
    }
  }

  
  // 추천인 코드 삭제
  const handleDeleteReferralCode = async (code, user_id) => {
    if (!confirm(`정말로 추천인 코드 "${code}"를 삭제하시겠습니까?`)) {
      return
    }
    
    try {
      const response = await adminFetch(`/api/admin/referral/codes/${code}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        await loadReferralData()
        alert('추천인 코드가 삭제되었습니다.')
      } else {
        const errorData = await response.json()
        alert(`삭제 실패: ${errorData.error}`)
      }
    } catch (error) {
      console.error('추천인 코드 삭제 실패:', error)
      alert('추천인 코드 삭제에 실패했습니다.')
    }
  }

  const handleExportData = async (type) => {
    let dataToExport = [];
    let filename = '';

    if (type === 'users') {
      dataToExport = users.map(user => ({
        '사용자 ID': user.userId,
        '이메일': user.email,
        '포인트': user.points,
        '가입일': user.createdAt,
        '마지막 활동': user.lastActivity
      }));
      filename = 'users_data.csv';
    } else if (type === 'orders') {
      dataToExport = orders.map(order => ({
        '주문 ID': order.orderId,
        '플랫폼': order.platform,
        '서비스': order.service,
        '수량': order.quantity,
        '금액': order.amount,
        '링크': order.link,
        '상태': order.status,
        '주문일': order.createdAt
      }));
      filename = 'orders_data.csv';
    } else if (type === 'purchases') {
      dataToExport = pendingPurchases.map(purchase => ({
        '신청 ID': purchase.id,
        '사용자 ID': purchase.userId,
        '이메일': purchase.email,
        '구매자 이름': purchase.buyerName,
        '은행 정보': purchase.bankInfo,
        '결제 금액': purchase.amount,
        '신청일': purchase.createdAt,
        '상태': purchase.status
      }));
      filename = 'purchase_requests_data.csv';
    }

    if (dataToExport.length === 0) {
      alert('내보낼 데이터가 없습니다.');
      return;
    }

    const csvContent = 'data:text/csv;charset=utf-8,' + dataToExport.map(row => 
      Object.values(row).map(val => `"${val}"`).join(',')
    ).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // 검색 필터링 함수들 (안전한 처리)
  const filteredUsers = (users || []).filter(user => {
    try {
      const userId = String(user?.userId || '')
      const email = String(user?.email || '')
      const searchTerm = String(tabStates.users.searchTerm || '').toLowerCase()
      
      return userId.toLowerCase().includes(searchTerm) ||
             email.toLowerCase().includes(searchTerm)
    } catch (error) {
      console.error('사용자 필터링 오류:', error, user)
      return false
    }
  })

  const filteredOrders = (orders || []).filter(order => {
    try {
      const orderId = String(order?.orderId || '')
      const platform = String(order?.platform || '')
      const service = String(order?.service || '')
      const searchTerm = String(tabStates.orders.searchTerm || '').toLowerCase()
      const selectedFilter = tabStates.orders.selectedFilter || '전체'
      
      // 검색어 필터링
      const matchesSearch = orderId.toLowerCase().includes(searchTerm) || 
                           platform.toLowerCase().includes(searchTerm) ||
                           service.toLowerCase().includes(searchTerm)
      
      // 상태 필터링
      let matchesFilter = true
      if (selectedFilter !== '전체') {
        const orderStatusText = getOrderStatusText(order.status)
        matchesFilter = orderStatusText === selectedFilter
      }
      
      return matchesSearch && matchesFilter
    } catch (error) {
      console.error('주문 필터링 오류:', error, order)
      return false
    }
  })

  // filteredPurchases는 상태 변수로 이미 선언되어 있음

  // 탭 렌더링
  const renderDashboard = () => (
    <div className="dashboard-content">
      <div className="dashboard-grid">
        <div className="stat-card">
          <div className="stat-icon users">
            <Users size={24} />
            </div>
          <div className="stat-content">
            <h3>총 사용자</h3>
            <p className="stat-number">{formatNumber(dashboardData.totalUsers)}</p>
            <p className="stat-label">전체 등록된 사용자</p>
            </div>
            </div>

        <div className="stat-card">
          <div className="stat-icon orders">
            <ShoppingCart size={24} />
            </div>
          <div className="stat-content">
            <h3>총 주문</h3>
            <p className="stat-number">{formatNumber(dashboardData.totalOrders)}</p>
            <p className="stat-label">전체 주문 건수</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon pending">
            <Activity size={24} />
                </div>
          <div className="stat-content">
            <h3>대기 중인 구매</h3>
            <p className="stat-number">{dashboardData.pendingPurchases}</p>
            <p className="stat-label">승인 대기 건수</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon today">
            <TrendingUp size={24} />
      </div>
          <div className="stat-content">
            <h3>오늘 주문</h3>
            <p className="stat-number">{dashboardData.todayOrders}</p>
            <p className="stat-label">오늘 신규 주문</p>
            </div>
            </div>

        <div className="stat-card">
          <div className="stat-icon today-revenue">
            <BarChart3 size={24} />
            </div>
          <div className="stat-content">
            <h3>오늘 매출</h3>
            <p className="stat-number">₩{formatNumber(dashboardData.todayRevenue)}</p>
            <p className="stat-label">오늘 신규 매출</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon monthly-revenue">
            <TrendingUp size={24} />
          </div>
          <div className="stat-content">
            <h3>월 매출</h3>
            <p className="stat-number">₩{formatNumber(dashboardData.monthlyRevenue)}</p>
            <p className="stat-label">총 포인트 - 총원가</p>
          </div>
        </div>
      </div>

      <div className="dashboard-actions">
        <div className="action-buttons">
          <button 
            className="btn-export"
            onClick={() => handleExportData('users')}
            title="사용자 데이터 내보내기"
          >
            <Download size={16} />
            사용자 내보내기
          </button>
          <button 
            className="btn-export"
            onClick={() => handleExportData('orders')}
            title="주문 데이터 내보내기"
          >
              <Download size={16} />
            주문 내보내기
            </button>
          <button 
            className="btn-export"
            onClick={() => handleExportData('purchases')}
            title="구매 신청 데이터 내보내기"
          >
              <Download size={16} />
            구매 신청 내보내기
            </button>
        </div>
      </div>

      <div className="dashboard-info">
        <div className="info-card">
          <div className="info-header">
            <Info size={20} />
            <h4>시스템 정보</h4>
          </div>
          <div className="info-content">
            <p><strong>마지막 업데이트:</strong> {lastUpdate}</p>
            <p><strong>데이터 상태:</strong> <span className="status-ok">정상</span></p>
            <p><strong>API 연결:</strong> <span className="status-ok">연결됨</span></p>
          </div>
        </div>
            </div>
                    </div>
  )

  // renderUsers 함수는 AdminUserManagement 컴포넌트로 대체됨

  const renderOrders = () => (
    <div className="tab-content">
      <div className="orders-header">
        <h2>주문내역 수정</h2>
        <p>아래 사진과 내역 수정</p>
      </div>
      
      <div className="orders-management">
        <div className="order-filters">
          <div className="filter-tabs">
            <button 
              className={`filter-tab ${tabStates.orders.selectedFilter === '전체' ? 'active' : ''}`}
              onClick={() => updateFilter('orders', '전체')}
            >
              전체
            </button>
            <button 
              className={`filter-tab ${tabStates.orders.selectedFilter === '주문 접수' ? 'active' : ''}`}
              onClick={() => updateFilter('orders', '주문 접수')}
            >
              주문 접수
            </button>
            <button 
              className={`filter-tab ${tabStates.orders.selectedFilter === '작업중' ? 'active' : ''}`}
              onClick={() => updateFilter('orders', '작업중')}
            >
              작업중
            </button>
            <button 
              className={`filter-tab ${tabStates.orders.selectedFilter === '작업완료' ? 'active' : ''}`}
              onClick={() => updateFilter('orders', '작업완료')}
            >
              작업완료
            </button>
          </div>
          
      <div className="search-bar">
        <Search size={20} />
        <input
          type="text"
              placeholder="주문조회"
          value={tabStates.orders.searchTerm}
          onChange={(e) => updateSearchTerm('orders', e.target.value)}
        />
            <button className="refresh-btn" onClick={() => loadOrders()}>
              <RefreshCw size={16} />
              새로고침
            </button>
          </div>
        </div>
          </div>

      <div className="orders-list">
            {filteredOrders.length > 0 ? (
              filteredOrders.map((order, index) => (
            <div key={index} className="order-item">
              <div className="order-header">
                <div className="order-info">
                  <h3>주문번호: {order.orderId || 'N/A'}</h3>
                  <p>주문일: {formatDate(order.createdAt)}</p>
                </div>
                <div className="order-actions">
                  <button className="btn-details">
                    <Eye size={16} />
                    상세보기
                  </button>
                </div>
              </div>
              
              <div className="order-content">
                <div className="service-info">
                  <div className="info-row">
                    <span className="label">서비스:</span>
                    <span className="value">{order.service || 'N/A'}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">서비스 ID:</span>
                    <span className="value">{order.serviceId || 'N/A'}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">수량:</span>
                    <span className="value">{formatNumber(order.quantity)}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">가격:</span>
                    <span className="value">₩{formatNumber(order.amount)}</span>
                  </div>
                </div>
                
                {/* 주문 진행현황 표시 */}
                {(order.smmPanelOrderId || order.packageSteps) && (
                  <div className="order-progress">
                    <h4>주문 진행현황:</h4>
                    {order.packageSteps && order.packageSteps.length > 0 ? (
                      <div className="package-progress">
                        <div className="progress-bar">
                          <div className="progress-fill" style={{width: `${order.progressPercentage || 0}%`}}></div>
                        </div>
                        <div className="progress-text">
                          {order.currentStatus || '대기중'} ({order.completedSteps || 0}/{order.totalSteps || 0})
                        </div>
                        
                        <div className="package-steps">
                          {order.packageSteps.map((step, stepIndex) => (
                            <div key={stepIndex} className={`step ${step.completed ? 'completed' : step.current ? 'current' : 'pending'}`}>
                              <div className="step-number">{stepIndex + 1}</div>
                              <div className="step-content">
                                <div className="step-title">{step.title}</div>
                                <div className="step-description">{step.description}</div>
                                <div className="step-quantity">{step.quantity}</div>
                                {step.schedule && <div className="step-schedule">{step.schedule}</div>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="simple-progress">
                        <div className="progress-info">
                          <span className="status-label">상태:</span>
                          <span className={`status-value ${getOrderStatusClass(order.status)}`}>
                            {getOrderStatusText(order.status)}
                          </span>
                        </div>
                        {order.smmPanelOrderId && (
                          <div className="smm-order-id">
                            <span className="label">SMM 주문번호:</span>
                            <span className="value">{order.smmPanelOrderId}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
                
                <div className="order-actions-buttons">
                  <span className={`status-badge ${getOrderStatusClass(order.status)}`}>
                    {getOrderStatusText(order.status)}
                  </span>
                  {order.status === 'pending' && (
                    <button 
                      className="action-btn order-receive"
                      onClick={() => handleOrderReceive(order.orderId)}
                    >
                      주문 접수
                    </button>
                  )}
                  {order.status !== 'completed' && order.status !== '주문 실행완료' && (
                    <button 
                      className="action-btn force-complete"
                      onClick={() => handleForceComplete(order.orderId)}
                    >
                      강제완료
                    </button>
                  )}
                </div>
                
                <div className="order-link">
                  <span className="label">링크:</span>
                  <span className="value">
                    {order.link && order.link !== 'N/A' ? (
                      <a href={order.link} target="_blank" rel="noopener noreferrer">
                        {order.link}
                      </a>
                    ) : 'N/A'}
                    </span>
                </div>
              </div>
            </div>
              ))
            ) : (
          <div className="no-orders">
            <p>{orders.length === 0 ? '주문 데이터를 불러오는 중...' : '검색 결과가 없습니다.'}</p>
          </div>
        )}
            </div>
                    </div>
  )

  const renderPurchases = () => (
    <div className="tab-content">
      <div className="search-bar" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
          <Search size={20} />
          <input
            type="text"
            placeholder="구매자 이름, 이메일로 검색..."
            value={tabStates.purchases.searchTerm}
            onChange={(e) => updateSearchTerm('purchases', e.target.value)}
            style={{ flex: 1 }}
          />
        </div>
        <select
          value={tabStates.purchases.statusFilter || 'all'}
          onChange={(e) => {
            setTabStates(prev => ({
              ...prev,
              purchases: { ...prev.purchases, statusFilter: e.target.value }
            }))
          }}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            border: '1px solid #ddd',
            fontSize: '14px',
            cursor: 'pointer'
          }}
        >
          <option value="all">전체 상태</option>
          <option value="pending">대기중</option>
          <option value="approved">승인됨</option>
          <option value="rejected">거절됨</option>
        </select>
      </div>

      <div className="data-table">
        <table>
          <thead>
            <tr>
              <th>신청 ID</th>
              <th>이메일</th>
              <th>구매자 이름</th>
              <th>은행 정보</th>
              <th>결제 금액</th>
              <th>현금영수증 정보</th>
              <th>신청일</th>
              <th>상태</th>
              <th>작업</th>
            </tr>
          </thead>
          <tbody>
            {filteredPurchases.length === 0 ? (
              <tr>
                <td colSpan="9" style={{ textAlign: 'center', padding: '2rem' }}>
                  {pendingPurchases.length === 0 ? (
                    <div>
                      <p>포인트 구매 신청이 없습니다.</p>
                      <button 
                        onClick={loadPendingPurchases}
                        style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}
                      >
                        새로고침
                      </button>
                    </div>
                  ) : (
                    <p>검색 결과가 없습니다.</p>
                  )}
                </td>
              </tr>
            ) : (
              filteredPurchases.map((purchase, index) => (
                <tr key={index}>
                  <td>{purchase.id || 'N/A'}</td>
                  <td>{purchase.email || 'N/A'}</td>
                  <td>{purchase.buyerName || 'N/A'}</td>
                  <td>{purchase.bankInfo || 'N/A'}</td>
                  <td>₩{formatNumber(purchase.amount)}</td>
                  <td>
                    {purchase.business_registration_number ? (
                      <div className="business-info">
                        <div>사업자등록번호: {purchase.business_registration_number}</div>
                        <div>사업자명: {purchase.business_name || 'N/A'}</div>
                        <div className={`business-status ${purchase.business_status || 'individual'}`}>
                          {purchase.business_status === 'business' ? '사업자' : '개인'}
                        </div>
                      </div>
                    ) : (
                      <span className="business-status individual">개인</span>
                    )}
                  </td>
                  <td>{formatDate(purchase.createdAt)}</td>
                  <td>
                    <span className={`status ${purchase.status || 'pending'}`}>
                      {purchase.status === 'approved' ? '승인됨' : 
                       purchase.status === 'rejected' ? '거절됨' : '대기중'}
                    </span>
                  </td>
                  <td>
                    {purchase.status === 'pending' && (
                      <div className="action-buttons">
                        <button
                          className="btn-approve"
                          onClick={() => handleApprovePurchase(purchase.id)}
                          title="승인"
                        >
                          <CheckCircle size={16} />
                        </button>
                        <button
                          className="btn-reject"
                          onClick={() => handleRejectPurchase(purchase.id)}
                          title="거절"
                        >
                          <XCircle size={16} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )

  // 추천인 관리 탭 렌더링
  const renderReferrals = () => (
    <div className="referral-management">
      <div className="referral-header">
        <h2>추천인 관리</h2>
        <div className="referral-actions">
          <div className="action-group">
            <button 
              onClick={() => setShowReferralModal(true)}
              className="admin-button success"
            >
              <UserPlus size={16} />
              이메일로 추천인 등록
            </button>
            <button 
              onClick={handleActivateAllCodes}
              className="admin-button warning"
            >
              <CheckCircle size={16} />
              모든 코드 활성화
            </button>
            <button 
              onClick={() => {
                loadReferralData()
                alert('데이터를 새로고침했습니다!')
              }}
              className="admin-button primary"
            >
              <RefreshCw size={16} />
              강제 새로고침
            </button>
          </div>
        </div>
      </div>

      <div className="referral-grid">
        <div className="referral-codes-section">
          <h3>발급된 추천인 코드</h3>
          <div className="referral-codes-table">
            <table>
              <thead>
                <tr>
                  <th>코드</th>
                  <th>이메일</th>
                  <th>상태</th>
                  <th>사용 횟수</th>
                  <th>총 커미션</th>
                  <th>생성일</th>
                  <th>작업</th>
                </tr>
              </thead>
              <tbody>
                {referralCodes.map((code, index) => (
                  <tr key={index}>
                    <td className="code-cell">
                      <span className="referral-code">{code.code}</span>
                      {code.user_id && (
                        <span className="user-id-badge">(사용자 ID: {code.user_id})</span>
                      )}
                    </td>
                    <td>{code.email || '-'}</td>
                    <td>
                      <span className={`status-badge ${code.is_active ? 'active' : 'inactive'}`}>
                        {(() => {
                          console.log(`🔍 코드 ${code.code} 상태:`, code.is_active, typeof code.is_active)
                          // is_active가 undefined이면 기본적으로 활성으로 처리
                          if (code.is_active === undefined || code.is_active === null) {
                            console.log(`⚠️ 코드 ${code.code}의 is_active가 undefined/null입니다. 기본값 true로 설정`)
                            return '활성'
                          }
                          if (code.is_active === true || code.is_active === 1 || code.is_active === 'true' || code.is_active === '1') {
                            return '활성'
                          } else {
                            return '비활성'
                          }
                        })()}
                      </span>
                    </td>
                    <td>{code.usage_count}</td>
                    <td className="commission-amount">
                      {formatNumber(code.total_commission)}원
                    </td>
                    <td>{code.createdAt ? new Date(code.createdAt).toLocaleDateString() : '날짜 없음'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button
                          className="btn-icon btn-info"
                          onClick={() => {
                            setSelectedReferralCode(code)
                            setShowReferralDetailModal(true)
                          }}
                          title="세부정보"
                          style={{ backgroundColor: '#667eea', color: 'white' }}
                        >
                          <Eye size={16} />
                        </button>
                        <button
                          className="btn-icon btn-danger"
                          onClick={() => handleDeleteReferralCode(code.code, code.user_id)}
                          title="삭제"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
                  </div>
                    </div>

        <div className="referral-commissions-section">
          <h3>커미션 환급 신청</h3>
          <div className="commissions-table">
            <table>
              <thead>
                <tr>
                  <th>신청 ID</th>
                  <th>이름</th>
                  <th>이메일</th>
                  <th>전화번호</th>
                  <th>은행명</th>
                  <th>계좌번호</th>
                  <th>환급 금액</th>
                  <th>상태</th>
                  <th>신청일</th>
                  <th>작업</th>
                </tr>
              </thead>
              <tbody>
                {referralCommissions.length === 0 ? (
                  <tr>
                    <td colSpan="10" style={{ textAlign: 'center', padding: '2rem' }}>
                      <p>커미션 환급 신청이 없습니다.</p>
                    </td>
                  </tr>
                ) : (
                  referralCommissions.map((request, index) => (
                    <tr key={index}>
                      <td>{request.request_id || index + 1}</td>
                      <td>{request.referrer_name || 'N/A'}</td>
                      <td>{request.referrer_email || 'N/A'}</td>
                      <td>{request.phone || 'N/A'}</td>
                      <td>{request.bank_name || 'N/A'}</td>
                      <td>{request.account_number || 'N/A'}</td>
                      <td className="commission-amount">
                        {formatNumber(request.commission_amount || request.amount || 0)}원
                      </td>
                      <td>
                        <span className={`status ${request.status || 'requested'}`}>
                          {request.status === 'approved' ? '승인됨' : 
                           request.status === 'rejected' ? '거절됨' : 
                           request.status === 'requested' || request.status === 'pending' ? '대기중' : '대기중'}
                        </span>
                      </td>
                      <td>{request.created_at ? new Date(request.created_at).toLocaleDateString('ko-KR') : '날짜 없음'}</td>
                      <td>
                        {(request.status === 'requested' || request.status === 'pending') && (
                          <div className="action-buttons" style={{ display: 'flex', gap: '8px' }}>
                            <button
                              className="btn-icon btn-approve"
                              onClick={() => handleApprovePayoutRequest(request.request_id)}
                              title="승인"
                              style={{ backgroundColor: '#10b981', color: 'white' }}
                            >
                              <CheckCircle size={16} />
                            </button>
                            <button
                              className="btn-icon btn-reject"
                              onClick={() => handleRejectPayoutRequest(request.request_id)}
                              title="거절"
                              style={{ backgroundColor: '#ef4444', color: 'white' }}
                            >
                              <XCircle size={16} />
                            </button>
                          </div>
                        )}
                        {(request.status === 'approved' || request.status === 'rejected') && (
                          <span style={{ color: '#666', fontSize: '12px' }}>
                            {request.status === 'approved' ? '승인 완료' : '거절됨'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
                    </div>
                  </div>
            </div>

      <div className="referral-stats">
        <div className="stat-card">
          <h4>총 발급 코드</h4>
          <span className="stat-number">{referralCodes.length}</span>
                  </div>
        <div className="stat-card">
          <h4>총 커미션 지급</h4>
          <span className="stat-number">
            {formatNumber(referralCommissions.reduce((sum, c) => sum + (c.commission_amount || 0), 0))}원
          </span>
                      </div>
        <div className="stat-card">
          <h4>활성 코드</h4>
          <span className="stat-number">
            {referralCodes.filter(c => c.is_active).length}
          </span>
                    </div>
                </div>
              </div>
  )


  const renderNotices = () => (
    <div className="notices-management">
      <div className="notices-header">
        <h2>팝업 관리</h2>
        <button 
          className="create-notice-btn"
          onClick={() => {
            setEditingNotice(null)
            setNoticeForm({
              title: '',
              content: '',
              image_url: '',
              login_popup_image_url: '',
              popup_type: 'notice',
              is_active: true
            })
            setShowNoticeModal(true)
          }}
        >
          <Bell size={16} />
          새 팝업 작성
        </button>
      </div>

      <div className="notices-list">
        {notices.length === 0 ? (
          <div className="empty-state">
            <Bell size={48} />
            <p>등록된 팝업이 없습니다.</p>
          </div>
        ) : (
          notices.map(notice => (
            <div key={notice.id} className="notice-item">
              <div className="notice-header">
                <h3>{notice.popup_type === 'login' ? '로그인 팝업' : '공지사항 팝업'}</h3>
                <div className="notice-actions">
                  <button 
                    className="notice-action-btn edit"
                    onClick={() => handleEditNotice(notice)}
                    title="수정"
                  >
                    <Edit size={16} />
                  </button>
                  <button 
                    className="notice-action-btn delete"
                    onClick={() => handleDeleteNotice(notice.id)}
                    title="삭제"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <div className="notice-content">
                {notice.image_url && (
                  <div className="notice-image-wrapper">
                    <img 
                      src={notice.image_url} 
                      alt="공지사항 이미지" 
                      className="notice-image"
                      onError={(e) => {
                        e.target.style.display = 'none'
                        e.target.nextSibling.style.display = 'block'
                      }}
                    />
                    <div className="image-error-fallback" style={{display: 'none'}}>
                      <div className="error-icon">⚠️</div>
                      <p>이미지를 불러올 수 없습니다</p>
                    </div>
                  </div>
                )}
              </div>
              <div className="notice-footer">
                <span className={`status-badge ${notice.is_active ? 'active' : 'inactive'}`}>
                  {notice.is_active ? '활성' : '비활성'}
                </span>
                <span className="notice-date">
                  {new Date(notice.created_at).toLocaleDateString('ko-KR')}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )

  // 관리자 권한 체크 중이거나 관리자가 아닌 경우 처리 (모든 hooks 선언 후)
  if (checkingAdmin) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div style={{ fontSize: '18px', color: '#333' }}>
          관리자 권한 확인 중...
        </div>
        <div style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>
          응답이 없으면 자동으로 일반 사용자로 처리됩니다.
        </div>
        <div style={{ 
          width: '40px', 
          height: '40px', 
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #667eea',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></div>
      </div>
    )
  }
  
  if (isAdmin === false) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '20px',
        padding: '20px',
        textAlign: 'center'
      }}>
        <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#dc2626' }}>
          접근 권한이 없습니다
        </div>
        <div style={{ fontSize: '16px', color: '#666' }}>
          관리자 권한이 필요합니다.
        </div>
        <button 
          onClick={() => navigate('/')}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: '#667eea',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer'
          }}
        >
          홈으로 돌아가기
        </button>
      </div>
    )
  }

    return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>관리자 대시보드</h1>
        <div className="header-actions">
          <button 
            className="btn-refresh"
            onClick={() => {
              if (activeTab === 'dashboard') {
                loadDashboardStats()
              } else if (activeTab === 'orders') {
                loadOrders()
              } else if (activeTab === 'purchases') {
                loadPendingPurchases()
              } else if (activeTab === 'referrals') {
                loadReferralData()
              }
              setLastUpdate(new Date().toLocaleString())
            }}
            disabled={isLoading}
          >
            <RefreshCw size={16} className={isLoading ? 'spinning' : ''} />
            새로고침
          </button>
          {lastUpdate && (
            <span className="last-update">
              마지막 업데이트: {lastUpdate}
            </span>
            )}
          </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="admin-tabs">
        <button
          className={`tab-button ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <BarChart3 size={20} />
          대시보드
        </button>
        <button
          className={`tab-button ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          <Users size={20} />
          사용자 관리
        </button>
        <button
          className={`tab-button ${activeTab === 'orders' ? 'active' : ''}`}
          onClick={() => setActiveTab('orders')}
        >
          <ShoppingCart size={20} />
          주문 관리
        </button>
                  <button
          className={`tab-button ${activeTab === 'purchases' ? 'active' : ''}`}
          onClick={() => setActiveTab('purchases')}
                  >
          <Activity size={20} />
          포인트 구매 신청
                  </button>
                  <button
          className={`tab-button ${activeTab === 'referrals' ? 'active' : ''}`}
          onClick={() => setActiveTab('referrals')}
                  >
          <TrendingUp size={20} />
          추천인 관리
                  </button>
                  <button
          className={`tab-button ${activeTab === 'blog' ? 'active' : ''}`}
          onClick={() => setActiveTab('blog')}
                  >
          <File size={20} />
          블로그 관리
                  </button>
                  <button
          className={`tab-button ${activeTab === 'services' ? 'active' : ''}`}
          onClick={() => setActiveTab('services')}
                  >
          <Package size={20} />
          서비스 관리
                  </button>
                  <button
          className={`tab-button ${activeTab === 'notices' ? 'active' : ''}`}
          onClick={() => setActiveTab('notices')}
                  >
          <Bell size={20} />
          팝업 관리
                  </button>
                  <button
          className={`tab-button ${activeTab === 'coupons' ? 'active' : ''}`}
          onClick={() => setActiveTab('coupons')}
                  >
          <Tag size={20} />
          쿠폰 관리
                  </button>
                </div>

      <div className="admin-content">
        {isLoading ? (
          <div className="loading">
            <RefreshCw size={24} className="spinning" />
            데이터를 불러오는 중...
          </div>
        ) : (
          <>
            {activeTab === 'dashboard' && renderDashboard()}
            {activeTab === 'users' && <AdminUserManagement adminFetch={adminFetch} />}
            {activeTab === 'orders' && renderOrders()}
            {activeTab === 'purchases' && renderPurchases()}
            {activeTab === 'referrals' && renderReferrals()}
            {activeTab === 'coupons' && <AdminCouponManagement adminFetch={adminFetch} />}
            {activeTab === 'blog' && (
              <div className="blog-management">
                <div className="blog-header">
                  <h2>블로그 관리</h2>
                  <p>블로그 글을 작성하고 관리할 수 있습니다.</p>
                </div>
                <div className="blog-redirect">
                  <p>블로그 관리는 별도 페이지에서 진행됩니다.</p>
                  <button 
                    className="admin-button"
                    onClick={() => navigate('/admin/blog')}
                  >
                    <File size={16} />
                    블로그 관리 페이지로 이동
                  </button>
                </div>
              </div>
            )}
            {activeTab === 'services' && (
              <AdminServiceManagement adminFetch={adminFetch} />
            )}
            {activeTab === 'notices' && renderNotices()}
          </>
        )}
      </div>

      {/* 추천인 등록 모달 */}
      {showReferralModal && (
        <ReferralRegistration
          onClose={() => setShowReferralModal(false)}
          onSuccess={handleReferralRegistrationSuccess}
        />
      )}

      {/* 커미션 환급 모달 */}
      {showPaymentModal && selectedReferrer && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>커미션 환급</h3>
              <button 
                className="modal-close"
                onClick={() => setShowPaymentModal(false)}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>추천인</label>
                <div className="referrer-info">
                  <div className="referrer-avatar">👤</div>
                  <div>
                    <div className="referrer-name">{selectedReferrer.referrer_name || '이름 없음'}</div>
                    <div className="referrer-email">{selectedReferrer.referrer_email}</div>
                  </div>
                </div>
              </div>
              
              <div className="form-group">
                <label>환급 금액</label>
                <input
                  type="number"
                  value={paymentData.amount}
                  onChange={(e) => setPaymentData({...paymentData, amount: e.target.value})}
                  placeholder="환급할 금액을 입력하세요"
                  className="admin-input"
                />
              </div>
              
              <div className="form-group">
                <label>환급 방법</label>
                <select
                  value={paymentData.payment_method}
                  onChange={(e) => setPaymentData({...paymentData, payment_method: e.target.value})}
                  className="admin-input"
                >
                  <option value="bank_transfer">계좌이체</option>
                  <option value="kakao_pay">카카오페이</option>
                  <option value="toss">토스</option>
                  <option value="cash">현금</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>메모</label>
                <textarea
                  value={paymentData.notes}
                  onChange={(e) => setPaymentData({...paymentData, notes: e.target.value})}
                  placeholder="환급 관련 메모를 입력하세요"
                  className="admin-input"
                  rows="3"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button 
                className="admin-button secondary"
                onClick={() => setShowPaymentModal(false)}
              >
                취소
              </button>
              <button 
                className="admin-button primary"
                onClick={handleCommissionPayment}
                disabled={!paymentData.amount || parseFloat(paymentData.amount) <= 0}
              >
                환급 처리
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 추천인 세부정보 모달 */}
      {showReferralDetailModal && selectedReferralCode && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h3>추천인 세부정보</h3>
              <button 
                className="modal-close"
                onClick={() => {
                  setShowReferralDetailModal(false)
                  setSelectedReferralCode(null)
                }}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>추천인 코드</label>
                <div className="referral-code-display" style={{ 
                  padding: '12px', 
                  backgroundColor: '#f0f0f0', 
                  borderRadius: '8px',
                  fontFamily: 'monospace',
                  fontSize: '18px',
                  fontWeight: 'bold'
                }}>
                  {selectedReferralCode.code}
                </div>
              </div>

              <div className="form-group">
                <label>이메일</label>
                <input
                  type="email"
                  value={selectedReferralCode.email || ''}
                  readOnly
                  className="admin-input"
                  style={{ backgroundColor: '#f5f5f5' }}
                />
              </div>

              <div className="form-group">
                <label>이름</label>
                <input
                  type="text"
                  value={selectedReferralCode.name || ''}
                  readOnly
                  className="admin-input"
                  style={{ backgroundColor: '#f5f5f5' }}
                />
              </div>

              <div className="form-group">
                <label>상태</label>
                <div>
                  <span className={`status-badge ${selectedReferralCode.is_active || selectedReferralCode.isActive ? 'active' : 'inactive'}`}>
                    {selectedReferralCode.is_active || selectedReferralCode.isActive ? '활성' : '비활성'}
                  </span>
                </div>
              </div>

              <div className="form-group">
                <label>사용 횟수</label>
                <input
                  type="text"
                  value={selectedReferralCode.usage_count || 0}
                  readOnly
                  className="admin-input"
                  style={{ backgroundColor: '#f5f5f5' }}
                />
              </div>

              <div className="form-group">
                <label>총 커미션</label>
                <input
                  type="text"
                  value={`${formatNumber(selectedReferralCode.total_commission || 0)}원`}
                  readOnly
                  className="admin-input"
                  style={{ backgroundColor: '#f5f5f5' }}
                />
              </div>

              <div className="form-group">
                <label>생성일</label>
                <input
                  type="text"
                  value={selectedReferralCode.createdAt ? new Date(selectedReferralCode.createdAt).toLocaleString('ko-KR') : '날짜 없음'}
                  readOnly
                  className="admin-input"
                  style={{ backgroundColor: '#f5f5f5' }}
                />
              </div>

              <div className="form-group">
                <label>커미션 비율 (%)</label>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={((selectedReferralCode.commission_rate || 0.1) * 100).toFixed(1)}
                    onChange={(e) => {
                      const value = parseFloat(e.target.value)
                      if (!isNaN(value) && value >= 0 && value <= 100) {
                        setSelectedReferralCode({
                          ...selectedReferralCode,
                          commission_rate: value / 100
                        })
                      }
                    }}
                    className="admin-input"
                    style={{ flex: 1 }}
                  />
                  <button
                    className="admin-button primary"
                    onClick={async () => {
                      try {
                        const newRate = (selectedReferralCode.commission_rate || 0.1)
                        console.log('🔄 커미션 비율 업데이트 요청:', {
                          email: selectedReferralCode.email,
                          user_id: selectedReferralCode.user_id,
                          code: selectedReferralCode.code,
                          rate: newRate
                        })
                        
                        const requestBody = {
                          referrer_email: selectedReferralCode.email,
                          commission_rate: newRate
                        }
                        
                        // user_id가 있으면 추가
                        if (selectedReferralCode.user_id || selectedReferralCode.id) {
                          requestBody.referrer_user_id = selectedReferralCode.user_id || selectedReferralCode.id
                        }
                        
                        const response = await adminFetch('/api/admin/referral/update-commission-rate', {
                          method: 'PUT',
                          headers: {
                            'Content-Type': 'application/json'
                          },
                          body: JSON.stringify(requestBody)
                        })
                        
                        if (response.ok) {
                          await loadReferralData()
                          alert(`커미션 비율이 ${(newRate * 100).toFixed(1)}%로 변경되었습니다.`)
                          setShowReferralDetailModal(false)
                          setSelectedReferralCode(null)
                        } else {
                          const errorData = await response.json()
                          alert(`오류: ${errorData.error}`)
                        }
                      } catch (error) {
                        console.error('커미션 비율 변경 실패:', error)
                        alert('커미션 비율 변경 중 오류가 발생했습니다.')
                      }
                    }}
                  >
                    <Edit size={16} style={{ marginRight: '5px' }} />
                    저장
                  </button>
                </div>
                <small style={{ color: '#666', marginTop: '5px', display: 'block' }}>
                  현재 커미션 비율: {(selectedReferralCode.commission_rate || 0.1) * 100}% (기본값: 10%)
                </small>
              </div>
            </div>
            <div className="modal-footer">
              <button 
                className="admin-button secondary"
                onClick={() => {
                  setShowReferralDetailModal(false)
                  setSelectedReferralCode(null)
                }}
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 공지사항 모달 */}
      {showNoticeModal && (
        <div className="notice-modal">
          <div className="notice-modal-content">
            <div className="modal-header">
              <h3>{editingNotice ? '팝업 수정' : '새 팝업 작성'}</h3>
              <button 
                className="modal-close"
                onClick={() => setShowNoticeModal(false)}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>팝업 타입</label>
                <select
                  value={noticeForm.popup_type}
                  onChange={(e) => setNoticeForm({...noticeForm, popup_type: e.target.value})}
                  className="admin-input"
                >
                  <option value="notice">공지사항 팝업</option>
                  <option value="login">로그인 팝업</option>
                </select>
              </div>

              {noticeForm.popup_type !== 'login' && (
                <div className="form-group">
                  <label>제목 {noticeForm.popup_type === 'notice' && <span style={{color: '#999', fontSize: '12px'}}>(선택 사항)</span>}</label>
                  <input
                    type="text"
                    value={noticeForm.title}
                    onChange={(e) => setNoticeForm({...noticeForm, title: e.target.value})}
                    placeholder={noticeForm.popup_type === 'notice' ? "팝업 제목 (선택 사항)" : "팝업 제목"}
                    className="admin-input"
                  />
                </div>
              )}

              {noticeForm.popup_type !== 'notice' && noticeForm.popup_type !== 'login' && (
                <div className="form-group">
                  <label>내용</label>
                  <textarea
                    value={noticeForm.content}
                    onChange={(e) => setNoticeForm({...noticeForm, content: e.target.value})}
                    placeholder="팝업 내용"
                    className="admin-input"
                    rows="4"
                  />
                </div>
              )}

              {noticeForm.popup_type === 'notice' && (
                <div className="form-group">
                  <label>공지사항 이미지 업로드</label>
                <div className="image-upload-container">
                <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      const file = e.target.files[0]
                      if (file) {
                        handleImageUpload(file)
                      }
                    }}
                    className="file-input"
                    id="image-upload"
                    disabled={uploadingImage}
                  />
                  <label htmlFor="image-upload" className="file-input-label">
                    {uploadingImage ? '업로드 중...' : '이미지 선택'}
                  </label>
                  {noticeForm.image_url && (
                    <div className="uploaded-image-preview">
                      <img src={noticeForm.image_url} alt="업로드된 이미지" />
                      <button 
                        type="button"
                        onClick={() => setNoticeForm({...noticeForm, image_url: ''})}
                        className="remove-image-btn"
                      >
                        ×
                      </button>
              </div>
                  )}
              </div>
              </div>
              )}

              {noticeForm.popup_type === 'login' && (
                <div className="form-group">
                  <label>로그인 팝업 이미지 업로드</label>
                  <small style={{color: '#666', display: 'block', marginBottom: '8px'}}>
                    로그인 모달의 왼쪽 배경에 표시되는 이미지입니다. (예: "신규 회원 쿠폰" 등의 프로모션 이미지)
                  </small>
                  <div className="image-upload-container">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        const file = e.target.files[0]
                        if (file) {
                          handleImageUpload(file, 'login')
                        }
                      }}
                      className="file-input"
                      id="login-image-upload"
                      disabled={uploadingImage}
                    />
                    <label htmlFor="login-image-upload" className="file-input-label">
                      {uploadingImage ? '업로드 중...' : '이미지 선택'}
                    </label>
                    {noticeForm.login_popup_image_url && (
                      <div className="uploaded-image-preview">
                        <img src={noticeForm.login_popup_image_url} alt="로그인 팝업 이미지" />
                        <button
                          type="button"
                          onClick={() => setNoticeForm({...noticeForm, login_popup_image_url: ''})}
                          className="remove-image-btn"
                        >
                          ×
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={noticeForm.is_active}
                    onChange={(e) => setNoticeForm({...noticeForm, is_active: e.target.checked})}
                  />
                  활성화
                </label>
              </div>
            </div>
            <div className="modal-footer">
              <button 
                className="admin-button secondary"
                onClick={() => setShowNoticeModal(false)}
              >
                취소
              </button>
              <button 
                className="admin-button primary"
                onClick={handleNoticeSubmit}
                disabled={isLoading || uploadingImage || (noticeForm.popup_type === 'notice' && !noticeForm.image_url) || (noticeForm.popup_type === 'login' && !noticeForm.login_popup_image_url)}
              >
                {editingNotice ? '수정' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 블로그 관리 */}
      {activeTab === 'blog' && (
        <div className="admin-section">
          <div className="section-header">
            <h2>블로그 관리</h2>
            <p>블로그 글을 작성하고 관리할 수 있습니다.</p>
          </div>
          <div className="blog-redirect">
            <p>블로그 관리는 별도 페이지에서 진행됩니다.</p>
            <button 
              className="admin-button primary"
              onClick={() => navigate('/admin/blog')}
            >
              <File size={16} />
              블로그 관리 페이지로 이동
            </button>
          </div>
        </div>
      )}

      {/* 관리자 권한 체크 중 - 조건부 렌더링은 hooks 뒤에 */}
      {checkingAdmin && (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '100vh',
          flexDirection: 'column',
          gap: '20px',
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'white',
          zIndex: 9999
        }}>
          <div style={{ fontSize: '18px', color: '#333' }}>
            관리자 권한 확인 중...
          </div>
          <div style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>
            응답이 없으면 자동으로 일반 사용자로 처리됩니다.
          </div>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #667eea',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }}></div>
        </div>
      )}

      {/* 관리자가 아닌 경우 접근 거부 - 조건부 렌더링은 hooks 뒤에 */}
      {isAdmin === false && !checkingAdmin && (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '100vh',
          flexDirection: 'column',
          gap: '20px',
          padding: '20px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#dc2626' }}>
            접근 권한이 없습니다
          </div>
          <div style={{ fontSize: '16px', color: '#666' }}>
            관리자 권한이 필요합니다.
          </div>
          <button 
            onClick={() => navigate('/')}
            style={{
              padding: '10px 20px',
              fontSize: '16px',
              backgroundColor: '#667eea',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer'
            }}
          >
            홈으로 돌아가기
          </button>
        </div>
      )}
    </div>
  )
}

export default AdminPage
