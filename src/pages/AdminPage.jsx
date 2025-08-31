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
  Download,
  Search,
  User,
  Clock,
  Package
} from 'lucide-react'
import './AdminPage.css'

// Force rebuild - Admin page with cash receipt download functionality
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
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [searchLoading, setSearchLoading] = useState(false)

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
      
      // Rate limiting 방지를 위한 지연
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // 백엔드 서버 URL 확인
      const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000' : ''
      
      // 실제 API 호출
      const [statsResponse, transactionsResponse, purchasesResponse, usersResponse] = await Promise.all([
        fetch(`${baseUrl}/api/admin/stats`),
        fetch(`${baseUrl}/api/admin/transactions`),
        fetch(`${baseUrl}/api/admin/purchases/pending`),
        fetch(`${baseUrl}/api/admin/users`)
      ])
      
      // 응답 상태 확인
      if (!statsResponse.ok || !transactionsResponse.ok || !purchasesResponse.ok || !usersResponse.ok) {
        throw new Error(`API 요청 실패: Stats ${statsResponse.status}, Transactions ${transactionsResponse.status}, Purchases ${purchasesResponse.status}, Users ${usersResponse.status}`)
      }
      
      // JSON 파싱
      const statsData = await statsResponse.json()
      const transactionsData = await transactionsResponse.json()
      const purchasesData = await purchasesResponse.json()
      const usersData = await usersResponse.json()
      
      // 데이터 설정
      if (statsData.success) {
        setStats(statsData.data)
      }
      
      if (transactionsData.success) {
        setTransactions(transactionsData.data)
      }
      
      if (purchasesData.success && purchasesData.purchases) {
        setPendingPurchases(purchasesData.purchases)
        
        // 승인된 구매와 거절된 구매 분리
        const approved = purchasesData.purchases.filter(p => p.status === 'approved')
        const rejected = purchasesData.purchases.filter(p => p.status === 'rejected')
        
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
      // API 실패 시 기본 데이터 사용
      setStats({
        totalUsers: 0,
        monthlyUsers: 0,
        totalRevenue: 0,
        monthlyRevenue: 0,
        totalSMMKingsCharge: 0,
        monthlySMMKingsCharge: 0
      })
      setTransactions({
        charges: [],
        refunds: []
      })
      setUsersInfo({
        totalUsers: 0,
        activeUsers: 0,
        newUsersToday: 0,
        newUsersWeek: 0,
        recentUsers: []
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
      const baseUrl = ''
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

  const handleExportCashReceipts = async () => {
    try {
      const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000' : ''
      const response = await fetch(`${baseUrl}/api/admin/export/cash-receipts`)
      
      if (!response.ok) {
        throw new Error('현금영수증 다운로드에 실패했습니다.')
      }
      
      // 파일 다운로드
      const blob = await response.blob()
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      
      // 파일명 추출
      const contentDisposition = response.headers.get('content-disposition')
      let filename = '현금영수증.csv'
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '')
        }
      }
      
      link.setAttribute('download', filename)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      alert('현금영수증 데이터가 다운로드되었습니다.')
    } catch (error) {
      console.error('현금영수증 다운로드 실패:', error)
      alert('현금영수증 다운로드 중 오류가 발생했습니다.')
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
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString('ko-KR')
  }

  const handleSearchAccount = async () => {
    if (!searchQuery.trim()) {
      alert('검색어를 입력해주세요.')
      return
    }

    try {
      setSearchLoading(true)
      const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000' : ''
      const response = await fetch(`${baseUrl}/api/admin/search-account?query=${encodeURIComponent(searchQuery.trim())}`)
      
      if (!response.ok) {
        throw new Error('검색에 실패했습니다.')
      }
      
      const result = await response.json()
      
      if (result.success) {
        setSearchResults(result.data)
      } else {
        alert(result.error || '검색에 실패했습니다.')
      }
    } catch (error) {
      console.error('계좌 검색 실패:', error)
      alert('계좌 검색에 실패했습니다.')
    } finally {
      setSearchLoading(false)
    }
  }

  const clearSearch = () => {
    setSearchQuery('')
    setSearchResults(null)
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
          <div className="export-buttons">
            <button onClick={handleExportPurchases} className="export-btn">
              <Download size={16} />
              구매내역 다운로드
            </button>
            <button onClick={handleExportCashReceipts} className="export-btn">
              <Download size={16} />
              현금영수증 다운로드
            </button>
          </div>
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

      {/* 계좌 정보 검색 섹션 */}
      <div className="search-section">
        <div className="search-header">
          <h2>계좌 정보 검색</h2>
          <div className="search-controls">
            <div className="search-input-wrapper">
              <Search size={20} className="search-icon" />
              <input
                type="text"
                placeholder="사용자 ID 또는 이메일을 입력하세요"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearchAccount()}
                className="search-input"
              />
            </div>
            <button 
              onClick={handleSearchAccount} 
              disabled={searchLoading}
              className="search-btn"
            >
              {searchLoading ? (
                <RefreshCw size={16} className="loading-spinner" />
              ) : (
                <Search size={16} />
              )}
              검색
            </button>
            {searchResults && (
              <button onClick={clearSearch} className="clear-btn">
                초기화
              </button>
            )}
          </div>
        </div>

        {searchResults && (
          <div className="search-results">
            <div className="search-summary">
              <h3>검색 결과</h3>
              <span className="result-count">{searchResults.totalFound}개의 계좌를 찾았습니다</span>
            </div>

            {/* 계좌 정보 */}
            <div className="accounts-grid">
              {searchResults.accounts.map((account, index) => (
                <div key={index} className="account-card">
                  <div className="account-header">
                    <User size={20} />
                    <h4>{account.userId}</h4>
                  </div>
                  <div className="account-stats">
                    <div className="stat-item">
                      <span className="stat-label">총 주문:</span>
                      <span className="stat-value">{account.orderCount}건</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">총 결제:</span>
                      <span className="stat-value">{formatCurrency(account.totalSpent)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">완료:</span>
                      <span className="stat-value positive">{formatCurrency(account.completedAmount)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">대기:</span>
                      <span className="stat-value pending">{formatCurrency(account.pendingAmount)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">취소:</span>
                      <span className="stat-value negative">{formatCurrency(account.canceledAmount)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">첫 주문:</span>
                      <span className="stat-value">{formatDate(account.firstOrder)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">마지막 주문:</span>
                      <span className="stat-value">{formatDate(account.lastOrder)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 최근 주문 내역 */}
            {searchResults.recentOrders.length > 0 && (
              <div className="recent-orders">
                <h3>최근 주문 내역</h3>
                <div className="orders-table">
                  <div className="table-header">
                    <div className="header-cell">주문번호</div>
                    <div className="header-cell">사용자</div>
                    <div className="header-cell">플랫폼</div>
                    <div className="header-cell">서비스</div>
                    <div className="header-cell">수량</div>
                    <div className="header-cell">금액</div>
                    <div className="header-cell">상태</div>
                    <div className="header-cell">주문일</div>
                  </div>
                  {searchResults.recentOrders.map((order) => (
                    <div key={order.id} className="table-row">
                      <div className="table-cell">{order.id}</div>
                      <div className="table-cell">{order.userId}</div>
                      <div className="table-cell">{order.platform}</div>
                      <div className="table-cell">{order.serviceName}</div>
                      <div className="table-cell">{order.quantity?.toLocaleString()}</div>
                      <div className="table-cell">{formatCurrency(order.totalAmount)}</div>
                      <div className={`table-cell status-${order.status}`}>
                        {order.status === 'completed' ? '완료' : 
                         order.status === 'pending' ? '대기중' : 
                         order.status === 'canceled' ? '취소' : order.status}
                      </div>
                      <div className="table-cell">{formatDate(order.createdAt)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
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
