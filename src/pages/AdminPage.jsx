import React, { useState, useEffect } from 'react'
import { 
  Users, 
  ShoppingCart, 
  BarChart3,
  Settings, 
  Search, 
  CheckCircle,
  XCircle,
  Eye,
  Download,
  RefreshCw,
  TrendingUp,
  DollarSign,
  Activity,
  Info,
  UserPlus
} from 'lucide-react'
import ReferralRegistration from '../components/ReferralRegistration'
import { 
  saveReferralCode, 
  getReferralCodes, 
  saveReferral, 
  getReferrals, 
  getCommissions 
} from '../utils/referralStorage'
import './AdminPage.css'

const AdminPage = () => {
  // 관리자 API 호출 헬퍼 함수
  const adminFetch = async (url, options = {}) => {
    const defaultHeaders = {
      'X-Admin-Token': 'admin_sociality_2024' // 관리자 토큰
    }
    
    return fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers
      }
    })
  }

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
    purchases: { searchTerm: '', lastUpdate: null },
    referrals: { lastUpdate: null }
  })

  // 대시보드 데이터
  const [dashboardData, setDashboardData] = useState({
    totalUsers: 0,
    totalOrders: 0,
    totalRevenue: 0,
    pendingPurchases: 0,
    todayOrders: 0,
    todayRevenue: 0
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
  const [filteredPurchases, setFilteredPurchases] = useState([])
  const [referralCodes, setReferralCodes] = useState([])
  const [referralCommissions, setReferralCommissions] = useState([])
  const [newReferralUser, setNewReferralUser] = useState('')
  
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

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    loadAdminData()
    loadReferralData()
    loadCommissionData()
  }, [])

  // 구매 신청 검색 필터링
  useEffect(() => {
    const searchTerm = tabStates.purchases.searchTerm
    const filtered = (pendingPurchases || []).filter(purchase => {
      try {
        const userId = String(purchase?.userId || '')
        const email = String(purchase?.email || '')
        const buyerName = String(purchase?.buyerName || '')
        const searchLower = String(searchTerm || '').toLowerCase()
        
        return userId.toLowerCase().includes(searchLower) ||
               email.toLowerCase().includes(searchLower) ||
               buyerName.toLowerCase().includes(searchLower)
      } catch (error) {
        return false
      }
    })
    setFilteredPurchases(filtered)
  }, [pendingPurchases, tabStates.purchases.searchTerm])

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

  // 관리자 데이터 로드
  const loadAdminData = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // 대시보드 통계 로드
      await loadDashboardStats()
      
      // 사용자 데이터 로드
      await loadUsers()
      
      // 주문 데이터 로드
      await loadOrders()
      
      // 포인트 구매 신청 로드
      await loadPendingPurchases()
      
      setLastUpdate(new Date().toLocaleString())
    } catch (error) {
      setError('데이터를 불러오는 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 대시보드 통계 로드
  const loadDashboardStats = async () => {
    try {
      const response = await adminFetch('/api/admin/stats')
      
      if (response.ok) {
        const data = await response.json()
        setDashboardData({
          totalUsers: data.total_users || 0,
          totalOrders: data.total_orders || 0,
          totalRevenue: data.total_revenue || 0,
          pendingPurchases: data.pending_purchases || 0,
          todayOrders: data.today_orders || 0,
          todayRevenue: data.today_revenue || 0
        })
      } else {
        console.error('대시보드 통계 로드 실패:', response.status)
      }
    } catch (error) {
      // 대시보드 통계 로드 실패
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
      const response = await adminFetch('/api/admin/transactions')
      
      if (response.ok) {
        const data = await response.json()
        // API 응답을 프론트엔드 형식으로 변환
        const transformedOrders = Array.isArray(data.transactions || data.orders) ? 
          (data.transactions || data.orders).map(order => ({
            orderId: order.order_id || order.orderId || order.id,
            userId: order.user_id || order.userId,
            platform: order.platform || order.service_platform || 'N/A',
            service: order.service_name || order.service || order.service_type || 'N/A',
            quantity: order.quantity || order.service_quantity || 0,
            amount: order.price || order.amount || order.total_price || 0,
            status: order.status || 'pending',
            createdAt: order.created_at || order.createdAt || order.order_date,
            link: order.link || order.service_link || 'N/A',
            comments: order.comments || order.remarks || 'N/A'
          })) : []
        
        setOrders(transformedOrders)
      }
    } catch (error) {
      setOrders([])
    }
  }

  // 포인트 구매 신청 로드
  const loadPendingPurchases = async () => {
    try {
      const response = await adminFetch('/api/admin/purchases')
      
      if (response.ok) {
        const data = await response.json()
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
        
        setPendingPurchases(transformedPurchases)
        setFilteredPurchases(transformedPurchases)
      }
    } catch (error) {
      setPendingPurchases([])
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
  // 추천인 데이터 로드
  const loadReferralData = async () => {
    try {
      console.log('🔄 추천인 데이터 로드 시작...')
      
      // 서버에서 데이터 로드
      const [codesResponse, referralsResponse, commissionsResponse] = await Promise.all([
        adminFetch('/api/admin/referral/codes'),
        adminFetch('/api/admin/referral/list'),
        adminFetch('/api/admin/referral/commissions')
      ])
      
      console.log('📡 API 응답 상태:', {
        codes: codesResponse.status,
        referrals: referralsResponse.status,
        commissions: commissionsResponse.status
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
      
      if (commissionsResponse.ok) {
        const commissionsData = await commissionsResponse.json()
        console.log('📋 커미션 내역 API 응답:', commissionsData)
        setReferralCommissions(commissionsData.commissions || [])
        console.log('✅ 커미션 내역 데이터 로드 완료:', commissionsData.commissions?.length || 0, '개')
      } else {
        console.error('❌ 커미션 내역 로드 실패:', commissionsResponse.status)
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

  // 커미션 데이터 로드
  const loadCommissionData = async () => {
    try {
      const [overviewResponse, historyResponse] = await Promise.all([
        adminFetch('/api/admin/referral/commission-overview'),
        adminFetch('/api/admin/referral/payment-history')
      ])
      
      if (overviewResponse.ok) {
        const overviewData = await overviewResponse.json()
        setCommissionOverview(overviewData.overview || [])
        setCommissionStats(overviewData.stats || {})
      }
      
      if (historyResponse.ok) {
        const historyData = await historyResponse.json()
        setPaymentHistory(historyData.payments || [])
      }
    } catch (error) {
      console.error('커미션 데이터 로드 실패:', error)
    }
  }

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

  // 추천인 코드 생성
  const handleGenerateReferralCode = async () => {
    if (!newReferralUser.trim()) {
      alert('사용자 ID를 입력해주세요.')
      return
    }

    try {
      const response = await adminFetch('/api/admin/referral/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: newReferralUser.trim() + '@example.com',
          name: newReferralUser.trim(),
          phone: ''
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        await loadReferralData()
        setNewReferralUser('')
        alert(`추천인 코드가 생성되었습니다: ${data.referralCode}`)
      } else {
        const errorData = await response.json()
        alert(`추천인 코드 생성 실패: ${errorData.error}`)
      }
    } catch (error) {
      console.error('추천인 코드 생성 실패:', error)
      alert('추천인 코드 생성에 실패했습니다.')
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
      const searchTerm = String(tabStates.orders.searchTerm || '').toLowerCase()
      
      return orderId.toLowerCase().includes(searchTerm) ||
             platform.toLowerCase().includes(searchTerm)
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
            <p className="stat-number">{dashboardData.totalUsers.toLocaleString()}</p>
            <p className="stat-label">전체 등록된 사용자</p>
            </div>
            </div>

        <div className="stat-card">
          <div className="stat-icon orders">
            <ShoppingCart size={24} />
            </div>
          <div className="stat-content">
            <h3>총 주문</h3>
            <p className="stat-number">{dashboardData.totalOrders.toLocaleString()}</p>
            <p className="stat-label">전체 주문 건수</p>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon revenue">
            <DollarSign size={24} />
          </div>
          <div className="stat-content">
            <h3>총 매출</h3>
            <p className="stat-number">₩{dashboardData.totalRevenue.toLocaleString()}</p>
            <p className="stat-label">전체 누적 매출</p>
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
            <p className="stat-number">₩{dashboardData.todayRevenue.toLocaleString()}</p>
            <p className="stat-label">오늘 신규 매출</p>
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

  const renderUsers = () => (
    <div className="tab-content">
      <div className="search-bar">
        <Search size={20} />
        <input
          type="text"
          placeholder="사용자 ID 또는 이메일로 검색..."
          value={tabStates.users.searchTerm}
          onChange={(e) => updateSearchTerm('users', e.target.value)}
        />
                    </div>

      <div className="data-table">
        <table>
          <thead>
            <tr>
              <th>사용자 ID</th>
              <th>이메일</th>
              <th>포인트</th>
              <th>가입일</th>
              <th>마지막 활동</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.length > 0 ? (
              filteredUsers.map((user, index) => (
                <tr key={index}>
                  <td>{user.userId || 'N/A'}</td>
                  <td>{user.email || 'N/A'}</td>
                  <td>{user.points?.toLocaleString() || 0}</td>
                  <td>{formatDate(user.createdAt)}</td>
                  <td>{formatDate(user.lastActivity)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="no-data">
                  {users.length === 0 ? '사용자 데이터를 불러오는 중...' : '검색 결과가 없습니다.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
                    </div>
                  </div>
  )

  const renderOrders = () => (
    <div className="tab-content">
      <div className="search-bar">
        <Search size={20} />
        <input
          type="text"
          placeholder="주문 ID 또는 플랫폼으로 검색..."
          value={tabStates.orders.searchTerm}
          onChange={(e) => updateSearchTerm('orders', e.target.value)}
        />
          </div>

      <div className="data-table">
        <table>
          <thead>
            <tr>
              <th>주문 ID</th>
              <th>플랫폼</th>
              <th>서비스</th>
              <th>수량</th>
              <th>금액</th>
              <th>링크</th>
              <th>상태</th>
              <th>주문일</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.length > 0 ? (
              filteredOrders.map((order, index) => (
                <tr key={index}>
                  <td>{order.orderId || 'N/A'}</td>
                  <td>{order.platform || 'N/A'}</td>
                  <td>{order.service || 'N/A'}</td>
                  <td>{order.quantity?.toLocaleString() || 0}</td>
                  <td>₩{order.amount?.toLocaleString() || 0}</td>
                  <td>
                    {order.link && order.link !== 'N/A' ? (
                      <a href={order.link} target="_blank" rel="noopener noreferrer" className="order-link">
                        {order.link.length > 30 ? order.link.substring(0, 30) + '...' : order.link}
                      </a>
                    ) : 'N/A'}
                  </td>
                  <td>
                    <span className={`status ${order.status || 'pending'}`}>
                      {order.status || '대기중'}
                    </span>
                  </td>
                  <td>{formatDate(order.createdAt)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="8" className="no-data">
                  {orders.length === 0 ? '주문 데이터를 불러오는 중...' : '검색 결과가 없습니다.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
            </div>
                    </div>
  )

  const renderPurchases = () => (
    <div className="tab-content">
      <div className="search-bar">
        <Search size={20} />
        <input
          type="text"
          placeholder="구매자 이름, 이메일 또는 사용자 ID로 검색..."
          value={tabStates.purchases.searchTerm}
          onChange={(e) => updateSearchTerm('purchases', e.target.value)}
        />
                    </div>

      <div className="data-table">
        <table>
          <thead>
            <tr>
              <th>신청 ID</th>
              <th>사용자 ID</th>
              <th>이메일</th>
              <th>구매자 이름</th>
              <th>은행 정보</th>
              <th>결제 금액</th>
              <th>신청일</th>
              <th>상태</th>
              <th>작업</th>
            </tr>
          </thead>
          <tbody>
            {filteredPurchases.map((purchase, index) => (
              <tr key={index}>
                <td>{purchase.id || 'N/A'}</td>
                <td>{purchase.userId || 'N/A'}</td>
                <td>{purchase.email || 'N/A'}</td>
                <td>{purchase.buyerName || 'N/A'}</td>
                <td>{purchase.bankInfo || 'N/A'}</td>
                <td>₩{purchase.amount?.toLocaleString() || 0}</td>
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
            ))}
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
            <div className="input-group">
              <input
                type="text"
                placeholder="사용자 ID 입력"
                value={newReferralUser}
                onChange={(e) => setNewReferralUser(e.target.value)}
                className="admin-input"
              />
              <button 
                onClick={handleGenerateReferralCode}
                className="admin-button primary"
              >
                <UserPlus size={16} />
                추천인 코드 생성
              </button>
            </div>
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
                  <th>상태</th>
                  <th>사용 횟수</th>
                  <th>총 커미션</th>
                  <th>생성일</th>
                </tr>
              </thead>
              <tbody>
                {referralCodes.map((code, index) => (
                  <tr key={index}>
                    <td className="code-cell">
                      <span className="referral-code">{code.code}</span>
                    </td>
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
                      {code.total_commission.toLocaleString()}원
                    </td>
                    <td>{code.created_at ? new Date(code.created_at).toLocaleDateString() : '날짜 없음'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
                  </div>
                    </div>

        <div className="referral-commissions-section">
          <h3>커미션 내역</h3>
          <div className="commissions-table">
            <table>
              <thead>
                <tr>
                  <th>피추천인</th>
                  <th>구매 금액</th>
                  <th>커미션 금액</th>
                  <th>커미션율</th>
                  <th>지급일</th>
                </tr>
              </thead>
              <tbody>
                {referralCommissions.map((commission, index) => (
                  <tr key={index}>
                    <td>{commission.referred_user_id}</td>
                    <td>{commission.purchase_amount?.toLocaleString()}원</td>
                    <td className="commission-amount">
                      {commission.commission_amount.toLocaleString()}원
                    </td>
                    <td>{(commission.commission_rate * 100).toFixed(1)}%</td>
                    <td>{new Date(commission.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
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
            {referralCommissions.reduce((sum, c) => sum + c.commission_amount, 0).toLocaleString()}원
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

  // 커미션 관리 탭 렌더링
  const renderCommissions = () => (
    <div className="commission-management">
      <div className="commission-header">
        <h2>커미션 관리</h2>
        <div className="commission-stats">
          <div className="stat-card">
            <h4>총 추천인 수</h4>
            <span className="stat-number">{commissionStats.total_referrers || 0}</span>
          </div>
          <div className="stat-card">
            <h4>총 피추천인 수</h4>
            <span className="stat-number">{commissionStats.total_referrals || 0}</span>
          </div>
          <div className="stat-card">
            <h4>총 커미션</h4>
            <span className="stat-number">{(commissionStats.total_commissions || 0).toLocaleString()}원</span>
          </div>
          <div className="stat-card">
            <h4>이번 달 커미션</h4>
            <span className="stat-number">{(commissionStats.this_month_commissions || 0).toLocaleString()}원</span>
          </div>
        </div>
      </div>

      <div className="commission-overview">
        <h3>추천인별 커미션 현황</h3>
        <div className="commission-table-container">
          <table className="commission-table">
            <thead>
              <tr>
                <th>추천인</th>
                <th>추천인 코드</th>
                <th>피추천인 수</th>
                <th>총 커미션</th>
                <th>이번 달 커미션</th>
                <th>미지급 커미션</th>
                <th>액션</th>
              </tr>
            </thead>
            <tbody>
              {commissionOverview.map((referrer, index) => (
                <tr key={index}>
                  <td>
                    <div className="referrer-info">
                      <div className="referrer-avatar">👤</div>
                      <div>
                        <div className="referrer-name">{referrer.referrer_name || '이름 없음'}</div>
                        <div className="referrer-email">{referrer.referrer_email}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="referral-code">{referrer.referral_code}</span>
                  </td>
                  <td>
                    <span className="referral-count">{referrer.referral_count}명</span>
                  </td>
                  <td>
                    <span className="total-commission">{referrer.total_commission.toLocaleString()}원</span>
                  </td>
                  <td>
                    <span className="month-commission">{referrer.this_month_commission.toLocaleString()}원</span>
                  </td>
                  <td>
                    <span className={`unpaid-commission ${referrer.unpaid_commission > 0 ? 'has-unpaid' : ''}`}>
                      {referrer.unpaid_commission.toLocaleString()}원
                    </span>
                  </td>
                  <td>
                    {referrer.unpaid_commission > 0 ? (
                      <button 
                        className="admin-button primary"
                        onClick={() => openPaymentModal(referrer)}
                      >
                        환급하기
                      </button>
                    ) : (
                      <span className="no-payment">환급 완료</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="payment-history">
        <h3>환급 내역</h3>
        <div className="payment-table-container">
          <table className="payment-table">
            <thead>
              <tr>
                <th>추천인</th>
                <th>환급 금액</th>
                <th>환급 방법</th>
                <th>메모</th>
                <th>환급일</th>
              </tr>
            </thead>
            <tbody>
              {paymentHistory.map((payment, index) => (
                <tr key={index}>
                  <td>{payment.referrer_email}</td>
                  <td className="payment-amount">{payment.amount.toLocaleString()}원</td>
                  <td>
                    <span className={`payment-method ${payment.payment_method}`}>
                      {payment.payment_method === 'bank_transfer' ? '계좌이체' : 
                       payment.payment_method === 'kakao_pay' ? '카카오페이' : 
                       payment.payment_method === 'toss' ? '토스' : payment.payment_method}
                    </span>
                  </td>
                  <td>{payment.notes || '-'}</td>
                  <td>{new Date(payment.paid_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )

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
              } else if (activeTab === 'users') {
                loadUsers()
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
          className={`tab-button ${activeTab === 'commissions' ? 'active' : ''}`}
          onClick={() => setActiveTab('commissions')}
                  >
          <DollarSign size={20} />
          커미션 관리
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
            {activeTab === 'users' && renderUsers()}
            {activeTab === 'orders' && renderOrders()}
            {activeTab === 'purchases' && renderPurchases()}
            {activeTab === 'referrals' && renderReferrals()}
            {activeTab === 'commissions' && renderCommissions()}
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
    </div>
  )
}

export default AdminPage
