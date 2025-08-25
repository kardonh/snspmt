import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { 
  Users, 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  CreditCard, 
  RefreshCw,
  BarChart3,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle,
  XCircle,
  Download
} from 'lucide-react'
import './AdminPage.css'

const AdminPage = () => {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState({
    totalUsers: 0,
    monthlyUsers: 0,
    totalRevenue: 0,
    monthlyRevenue: 0,
    totalSMMKingsCharge: 0,
    monthlySMMKingsCharge: 0
  })
  const [transactions, setTransactions] = useState({
    charges: [],
    refunds: []
  })
  const [approvedPurchases, setApprovedPurchases] = useState([])
  const [rejectedPurchases, setRejectedPurchases] = useState([])
  const [monthlyStats, setMonthlyStats] = useState({
    monthlyRevenue: 0,
    monthlyCharge: 0,
    monthlyProfit: 0
  })
  const [pendingPurchases, setPendingPurchases] = useState([])
  const [loading, setLoading] = useState(true)
  const [usersInfo, setUsersInfo] = useState({
    totalUsers: 0,
    activeUsers: 0,
    newUsersToday: 0,
    newUsersWeek: 0,
    recentUsers: [],
    activeUsersList: []
  })

  // 관리자 이메일 체크
  useEffect(() => {
    if (!currentUser) {
      navigate('/')
      return
    }

    // 관리자 이메일 체크
    if (currentUser.email !== 'tambleofficial@gmail.com') {
      alert('관리자만 접근할 수 있습니다.')
      navigate('/')
      return
    }
    // 관리자 데이터 로드
    loadAdminData()
  }, [currentUser, navigate])

  const loadAdminData = async () => {
    try {
      setLoading(true)
  
      
      // 백엔드 서버 URL 확인
      const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000' : ''
      
      // 실제 API 호출
      const [statsResponse, transactionsResponse, purchasesResponse, usersResponse] = await Promise.all([
        fetch(`${baseUrl}/api/admin/stats`),
        fetch(`${baseUrl}/api/admin/transactions`),
        fetch(`${baseUrl}/api/admin/purchases/pending`),
        fetch(`${baseUrl}/api/admin/users`)
      ])
      
      
      
      // 응답 내용 확인
      const statsText = await statsResponse.text()
      const transactionsText = await transactionsResponse.text()
      const purchasesText = await purchasesResponse.text()
      const usersText = await usersResponse.text()
      
      
      
      if (!statsResponse.ok || !transactionsResponse.ok || !purchasesResponse.ok || !usersResponse.ok) {
        throw new Error(`API 요청 실패: Stats ${statsResponse.status}, Transactions ${transactionsResponse.status}, Purchases ${purchasesResponse.status}, Users ${usersResponse.status}`)
      }
      
      // JSON 파싱 시도
      let statsData, transactionsData, purchasesData, usersData
      try {
        statsData = JSON.parse(statsText)
        transactionsData = JSON.parse(transactionsText)
        purchasesData = JSON.parse(purchasesText)
        usersData = JSON.parse(usersText)
      } catch (parseError) {
        console.error('JSON 파싱 실패:', parseError)
        throw new Error('API 응답이 유효한 JSON이 아닙니다')
      }
      
      
      
      if (statsData.success) {
        setStats(statsData.data)
      }
      
      if (transactionsData.success) {
        setTransactions(transactionsData.data)
      }
      
      if (purchasesData.purchases) {
        setPendingPurchases(purchasesData.purchases)
        
        // 승인된 구매와 거절된 구매 분리
        const approved = []
        const rejected = []
        
        // 모든 구매 내역을 가져오기 위해 추가 API 호출
        try {
          const allPurchasesResponse = await fetch(`${baseUrl}/api/purchases`)
          if (allPurchasesResponse.ok) {
            const allPurchasesData = await allPurchasesResponse.json()
            if (allPurchasesData.history) {
              // 모든 사용자의 구매 내역을 하나로 합치기
              const allPurchases = []
              for (const userPurchases of Object.values(allPurchasesData.history)) {
                if (Array.isArray(userPurchases)) {
                  allPurchases.push(...userPurchases)
                }
              }
              
              // 승인/거절된 구매 분리
              allPurchases.forEach(purchase => {
                if (purchase.status === 'approved') {
                  approved.push(purchase)
                } else if (purchase.status === 'rejected') {
                  rejected.push(purchase)
                }
              })
            }
          }
        } catch (error) {
          console.error('전체 구매 내역 조회 실패:', error)
        }
        
        setApprovedPurchases(approved)
        setRejectedPurchases(rejected)
        
        // 월별 통계 계산
        const allPurchases = [...approved, ...rejected]
        calculateMonthlyStats(allPurchases)
      }
      
      if (usersData) {
        setUsersInfo(usersData)
      }

    } catch (error) {
      console.error('관리자 데이터 로드 실패:', error)
      // API 실패 시 임시 데이터 사용
      const mockData = {
        totalUsers: 1250,
        monthlyUsers: 89,
        totalRevenue: 2500000,
        monthlyRevenue: 180000,
        totalSMMKingsCharge: 1800000,
        monthlySMMKingsCharge: 120000,
        monthlyCost: 96000
      }
      
      setStats(mockData)
      setTransactions({
        charges: [
          { id: 1, user: 'user1@example.com', amount: 50000, date: '2024-01-15', status: 'completed' },
          { id: 2, user: 'user2@example.com', amount: 30000, date: '2024-01-14', status: 'completed' }
        ],
        refunds: [
          { id: 1, user: 'user4@example.com', amount: 25000, date: '2024-01-12', reason: '서비스 미제공' }
        ]
      })
    } finally {
      setLoading(false)
    }
  }

  const calculateMonthlyStats = (purchases) => {
    const now = new Date()
    const currentMonth = now.getMonth()
    const currentYear = now.getFullYear()
    
    let monthlyRevenue = 0
    
    purchases.forEach(purchase => {
      const purchaseDate = new Date(purchase.createdAt)
      if (purchaseDate.getMonth() === currentMonth && purchaseDate.getFullYear() === currentYear) {
        if (purchase.status === 'approved') {
          monthlyRevenue += purchase.price || 0
        }
      }
    })
    
    // 백엔드에서 받은 월 원가 사용
    const monthlyCost = stats.monthlyCost || 0
    const monthlyProfit = monthlyRevenue - monthlyCost
    
    setMonthlyStats({
      monthlyRevenue,
      monthlyCost,
      monthlyProfit
    })
  }

  const handleExportPurchases = async () => {
    try {
      const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000' : ''
      const response = await fetch(`${baseUrl}/api/admin/export/purchases`)
      
      if (!response.ok) {
        throw new Error('엑셀 다운로드에 실패했습니다.')
      }
      
      const data = await response.json()
      
      if (data.success) {
        // CSV 파일 다운로드
        const blob = new Blob([data.data], { type: 'text/csv;charset=utf-8;' })
        const link = document.createElement('a')
        const url = URL.createObjectURL(blob)
        link.setAttribute('href', url)
        link.setAttribute('download', data.filename)
        link.style.visibility = 'hidden'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        
        alert('포인트 구매 내역이 다운로드되었습니다.')
      } else {
        alert('엑셀 다운로드에 실패했습니다.')
      }
    } catch (error) {
      console.error('엑셀 다운로드 실패:', error)
      alert('엑셀 다운로드 중 오류가 발생했습니다.')
    }
  }

  const handlePurchaseAction = async (purchaseId, action) => {
    try {
      const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000' : ''
      
      const response = await fetch(`${baseUrl}/api/admin/purchases/${purchaseId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: action })
      })
      
      if (!response.ok) {
        throw new Error('구매 신청 처리에 실패했습니다.')
      }
      
      const result = await response.json()
      
      if (result.success) {
        alert(`구매 신청이 ${action === 'approved' ? '승인' : '거절'}되었습니다.`)
        // 데이터 새로고침
        loadAdminData()
      } else {
        alert('처리 중 오류가 발생했습니다.')
      }
    } catch (error) {
      console.error('구매 신청 처리 실패:', error)
      alert('구매 신청 처리에 실패했습니다.')
    }
  }

  const formatNumber = (num) => {
    return new Intl.NumberFormat('ko-KR').format(num)
  }

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'KRW'
    }).format(amount)
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ko-KR')
  }

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>관리자 데이터를 불러오는 중...</p>
        <p>현재 사용자: {currentUser ? currentUser.email : '로그인되지 않음'}</p>
      </div>
    )
  }

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>관리자 대시보드</h1>
        <p>안녕하세요, 관리자님! 오늘의 통계를 확인하세요.</p>
        <p style={{fontSize: '0.9rem', opacity: 0.8}}>현재 사용자: {currentUser ? currentUser.email : '로그인되지 않음'}</p>
      </div>



      {/* 실시간 사용자 정보 섹션 */}
      <div className="users-info-section">
        <div className="users-stats">
          <h2>실시간 사용자 정보</h2>
          <div className="users-grid">
            <div className="user-stat-item">
              <Users size={20} />
              <span>총 가입자</span>
              <strong>{formatNumber(usersInfo.totalUsers)}명</strong>
            </div>
            <div className="user-stat-item">
              <TrendingUp size={20} />
              <span>실시간 접속자</span>
              <strong>{formatNumber(usersInfo.activeUsers)}명</strong>
            </div>
            <div className="user-stat-item">
              <Calendar size={20} />
              <span>오늘 신규 가입</span>
              <strong>{formatNumber(usersInfo.newUsersToday)}명</strong>
            </div>
            <div className="user-stat-item">
              <BarChart3 size={20} />
              <span>이번 주 신규 가입</span>
              <strong>{formatNumber(usersInfo.newUsersWeek)}명</strong>
            </div>
          </div>
        </div>
        
        <div className="recent-users">
          <h3>최근 접속 사용자 (최대 20명)</h3>
          <div className="users-list">
            {usersInfo.recentUsers.slice(0, 20).map((user, index) => (
              <div key={user.id} className="user-item">
                <div className="user-info">
                  <div className="user-email">{user.email}</div>
                  <div className="user-details">
                    <span className="user-name">{user.displayName || '이름 없음'}</span>
                    <span className="user-points">{formatNumber(user.currentPoints)}P</span>
                  </div>
                </div>
                <div className="user-activity">
                  <span className="last-login">
                    마지막 접속: {formatDate(user.lastLoginAt)}
                  </span>
                  {usersInfo.activeUsersList.includes(user.id) && (
                    <span className="online-indicator">🟢 온라인</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 상세 통계 섹션 */}
      <div className="detailed-stats">
        <div className="monthly-stats">
          <h2>이번 달 통계</h2>
          <div className="monthly-grid">
            <div className="monthly-item">
              <TrendingUp size={20} />
              <span>월 매출액</span>
              <strong>{formatCurrency(monthlyStats.monthlyRevenue)}</strong>
            </div>
            <div className="monthly-item">
              <RefreshCw size={20} />
              <span>월 원가</span>
              <strong>{formatCurrency(monthlyStats.monthlyCost)}</strong>
            </div>
            <div className="monthly-item">
              <TrendingDown size={20} />
              <span>월 순이익</span>
              <strong>{formatCurrency(monthlyStats.monthlyProfit)}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* 거래 내역 섹션 */}
      <div className="transactions-section">
        <div className="transactions-header">
          <h2>포인트 구매 내역</h2>
          <button onClick={handleExportPurchases} className="export-btn">
            <Download size={16} />
            엑셀 다운로드
          </button>
        </div>
        <div className="transactions-grid">
          {/* 승인된 구매 내역 */}
          <div className="transaction-card">
            <div className="transaction-header">
              <h3>승인된 구매 내역</h3>
              <span className="transaction-count">{approvedPurchases.length}건</span>
            </div>
            <div className="transaction-list">
              {approvedPurchases.length === 0 ? (
                <div className="no-transactions">승인된 구매 내역이 없습니다.</div>
              ) : (
                approvedPurchases.map(purchase => (
                  <div key={purchase.id} className="transaction-item">
                    <div className="transaction-info">
                      <span className="transaction-user">{purchase.depositorName}</span>
                      <span className="transaction-date">{formatDate(purchase.createdAt)}</span>
                    </div>
                    <div className="transaction-amount positive">
                      +{purchase.amount.toLocaleString()}P
                    </div>
                    <div className="transaction-bank">
                      {purchase.bankName}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 거절된 구매 내역 */}
          <div className="transaction-card">
            <div className="transaction-header">
              <h3>거절된 구매 내역</h3>
              <span className="transaction-count">{rejectedPurchases.length}건</span>
            </div>
            <div className="transaction-list">
              {rejectedPurchases.length === 0 ? (
                <div className="no-transactions">거절된 구매 내역이 없습니다.</div>
              ) : (
                rejectedPurchases.map(purchase => (
                  <div key={purchase.id} className="transaction-item">
                    <div className="transaction-info">
                      <span className="transaction-user">{purchase.depositorName}</span>
                      <span className="transaction-date">{formatDate(purchase.createdAt)}</span>
                    </div>
                    <div className="transaction-amount negative">
                      -{purchase.amount.toLocaleString()}P
                    </div>
                    <div className="transaction-bank">
                      {purchase.bankName}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 포인트 구매 승인 섹션 */}
      <div className="purchases-section">
        <div className="purchases-header">
          <h2>포인트 구매 승인</h2>
          <span className="purchases-count">{pendingPurchases.length}건 대기중</span>
        </div>
        
        {pendingPurchases.length === 0 ? (
          <div className="no-purchases">
            <p>대기중인 포인트 구매 신청이 없습니다.</p>
          </div>
        ) : (
          <div className="purchases-list">
            {pendingPurchases.map(purchase => (
              <div key={purchase.id} className="purchase-item">
                <div className="purchase-info">
                  <div className="purchase-user">
                    <strong>{purchase.depositorName}</strong>
                    <span className="purchase-email">({purchase.userId})</span>
                  </div>
                  <div className="purchase-details">
                    <span className="purchase-amount">{purchase.amount.toLocaleString()}P</span>
                    <span className="purchase-price">{purchase.price.toLocaleString()}원</span>
                    <span className="purchase-date">{formatDate(purchase.createdAt)}</span>
                  </div>
                  <div className="purchase-bank">
                    <strong>은행:</strong> {purchase.bankName}
                  </div>
                  {purchase.receiptType && purchase.receiptType !== 'none' && (
                    <div className="purchase-receipt">
                      <strong>영수증:</strong> {purchase.receiptType === 'tax' ? '세금계산서' : '현금영수증'}
                      {purchase.receiptType === 'tax' && purchase.businessName && (
                        <span> ({purchase.businessName})</span>
                      )}
                      {purchase.receiptType === 'cash' && purchase.cashReceiptPhone && (
                        <span> ({purchase.cashReceiptPhone})</span>
                      )}
                    </div>
                  )}
                </div>
                <div className="purchase-actions">
                  <button
                    onClick={() => handlePurchaseAction(purchase.id, 'approved')}
                    className="approve-btn"
                  >
                    <CheckCircle size={16} />
                    승인
                  </button>
                  <button
                    onClick={() => handlePurchaseAction(purchase.id, 'rejected')}
                    className="reject-btn"
                  >
                    <XCircle size={16} />
                    거절
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminPage
