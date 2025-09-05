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
  Info
} from 'lucide-react'
import './AdminPage.css'

const AdminPage = () => {
  // 상태 관리
  const [activeTab, setActiveTab] = useState('dashboard')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

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
  const [userSearchTerm, setUserSearchTerm] = useState('')

  // 주문 데이터
  const [orders, setOrders] = useState([])
  const [orderSearchTerm, setOrderSearchTerm] = useState('')

  // 포인트 구매 신청 데이터
  const [pendingPurchases, setPendingPurchases] = useState([])
  const [purchaseSearchTerm, setPurchaseSearchTerm] = useState('')

  // 추천인 데이터
  const [referralCodes, setReferralCodes] = useState([])
  const [referralCommissions, setReferralCommissions] = useState([])
  const [newReferralUser, setNewReferralUser] = useState('')

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    loadAdminData()
    loadReferralData()
  }, [])

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
      console.error('관리자 데이터 로드 실패:', error)
      setError('데이터를 불러오는 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  // 대시보드 통계 로드
  const loadDashboardStats = async () => {
    try {
      const response = await fetch('/api/admin/stats')
      if (response.ok) {
        const data = await response.json()
        setDashboardData({
          totalUsers: data.totalUsers || 0,
          totalOrders: data.totalOrders || 0,
          totalRevenue: data.totalRevenue || 0,
          pendingPurchases: data.pendingPurchases || 0,
          todayOrders: data.todayOrders || 0,
          todayRevenue: data.todayRevenue || 0
        })
      }
    } catch (error) {
      console.error('대시보드 통계 로드 실패:', error)
    }
  }

  // 사용자 데이터 로드
  const loadUsers = async () => {
    try {
      const response = await fetch('/api/admin/users')
      if (response.ok) {
        const data = await response.json()
        setUsers(Array.isArray(data) ? data : [])
      }
    } catch (error) {
      console.error('사용자 데이터 로드 실패:', error)
      setUsers([])
    }
  }

  // 주문 데이터 로드
  const loadOrders = async () => {
    try {
      const response = await fetch('/api/admin/transactions')
      if (response.ok) {
        const data = await response.json()
        setOrders(Array.isArray(data) ? data : [])
      }
    } catch (error) {
      console.error('주문 데이터 로드 실패:', error)
      setOrders([])
    }
  }

  // 포인트 구매 신청 로드
  const loadPendingPurchases = async () => {
    try {
      const response = await fetch('/api/admin/purchases')
      if (response.ok) {
        const data = await response.json()
        setPendingPurchases(Array.isArray(data) ? data : [])
      }
    } catch (error) {
      console.error('포인트 구매 신청 로드 실패:', error)
      setPendingPurchases([])
    }
  }

  // 포인트 구매 신청 승인
  const handleApprovePurchase = async (purchaseId) => {
    try {
      const response = await fetch(`/api/admin/purchases/${purchaseId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: 'approved' })
      })

      if (response.ok) {
        alert('포인트 구매 신청이 승인되었습니다.')
        loadPendingPurchases() // 목록 새로고침
        loadDashboardStats() // 통계 업데이트
      } else {
        alert('승인 처리 중 오류가 발생했습니다.')
      }
    } catch (error) {
      console.error('승인 처리 실패:', error)
      alert('승인 처리 중 오류가 발생했습니다.')
    }
  }

  // 포인트 구매 신청 거절
  const handleRejectPurchase = async (purchaseId) => {
    try {
      const response = await fetch(`/api/admin/purchases/${purchaseId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: 'rejected' })
      })

      if (response.ok) {
        alert('포인트 구매 신청이 거절되었습니다.')
        loadPendingPurchases() // 목록 새로고침
        loadDashboardStats() // 통계 업데이트
      } else {
        alert('거절 처리 중 오류가 발생했습니다.')
      }
    } catch (error) {
      console.error('거절 처리 실패:', error)
      alert('거절 처리 중 오류가 발생했습니다.')
    }
  }

  // 데이터 내보내기 함수
  // 추천인 데이터 로드
  const loadReferralData = async () => {
    try {
      // 추천인 코드 목록 로드
      const codesResponse = await fetch('/api/referral/my-codes?user_id=admin')
      if (codesResponse.ok) {
        const codesData = await codesResponse.json()
        setReferralCodes(codesData.codes || [])
      }

      // 추천인 커미션 내역 로드
      const commissionsResponse = await fetch('/api/referral/commissions?user_id=admin')
      if (commissionsResponse.ok) {
        const commissionsData = await commissionsResponse.json()
        setReferralCommissions(commissionsData.commissions || [])
      }
    } catch (error) {
      console.error('추천인 데이터 로드 실패:', error)
    }
  }

  // 추천인 코드 생성
  const handleGenerateReferralCode = async () => {
    if (!newReferralUser.trim()) {
      alert('사용자 ID를 입력해주세요.')
      return
    }

    try {
      const response = await fetch('/api/referral/generate-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: newReferralUser.trim()
        })
      })

      if (response.ok) {
        const result = await response.json()
        alert(`추천인 코드가 생성되었습니다: ${result.code}`)
        setNewReferralUser('')
        loadReferralData() // 데이터 새로고침
      } else {
        const error = await response.json()
        alert(`오류: ${error.error}`)
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
        '상태': order.status,
        '주문일': order.createdAt
      }));
      filename = 'orders_data.csv';
    } else if (type === 'purchases') {
      dataToExport = pendingPurchases.map(purchase => ({
        '신청 ID': purchase.id,
        '사용자 ID': purchase.userId,
        '이메일': purchase.email,
        '구매 포인트': purchase.points,
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

  // 검색 필터링 함수들
  const filteredUsers = users.filter(user => 
    user.userId?.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
    user.email?.toLowerCase().includes(userSearchTerm.toLowerCase())
  )

  const filteredOrders = orders.filter(order => 
    order.orderId?.toLowerCase().includes(orderSearchTerm.toLowerCase()) ||
    order.platform?.toLowerCase().includes(orderSearchTerm.toLowerCase())
  )

  const filteredPurchases = pendingPurchases.filter(purchase => 
    purchase.userId?.toLowerCase().includes(purchaseSearchTerm.toLowerCase()) ||
    purchase.email?.toLowerCase().includes(purchaseSearchTerm.toLowerCase())
  )

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
          value={userSearchTerm}
          onChange={(e) => setUserSearchTerm(e.target.value)}
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
            {filteredUsers.map((user, index) => (
              <tr key={index}>
                <td>{user.userId || 'N/A'}</td>
                <td>{user.email || 'N/A'}</td>
                <td>{user.points?.toLocaleString() || 0}</td>
                <td>{user.createdAt || 'N/A'}</td>
                <td>{user.lastActivity || 'N/A'}</td>
              </tr>
            ))}
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
          value={orderSearchTerm}
          onChange={(e) => setOrderSearchTerm(e.target.value)}
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
              <th>상태</th>
              <th>주문일</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map((order, index) => (
              <tr key={index}>
                <td>{order.orderId || 'N/A'}</td>
                <td>{order.platform || 'N/A'}</td>
                <td>{order.service || 'N/A'}</td>
                <td>{order.quantity?.toLocaleString() || 0}</td>
                <td>₩{order.amount?.toLocaleString() || 0}</td>
                <td>
                  <span className={`status ${order.status || 'pending'}`}>
                    {order.status || '대기중'}
                  </span>
                </td>
                <td>{order.createdAt || 'N/A'}</td>
              </tr>
            ))}
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
          placeholder="사용자 ID 또는 이메일로 검색..."
          value={purchaseSearchTerm}
          onChange={(e) => setPurchaseSearchTerm(e.target.value)}
        />
      </div>

      <div className="data-table">
        <table>
          <thead>
            <tr>
              <th>신청 ID</th>
              <th>사용자 ID</th>
              <th>이메일</th>
              <th>구매 포인트</th>
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
                <td>{purchase.points?.toLocaleString() || 0}</td>
                <td>₩{purchase.amount?.toLocaleString() || 0}</td>
                <td>{purchase.createdAt || 'N/A'}</td>
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
    <div className="referral-content">
      <div className="section-header">
        <h2>추천인 코드 관리</h2>
        <div className="referral-actions">
          <div className="generate-code-section">
            <input
              type="text"
              placeholder="사용자 ID 입력"
              value={newReferralUser}
              onChange={(e) => setNewReferralUser(e.target.value)}
              className="referral-input"
            />
            <button 
              onClick={handleGenerateReferralCode}
              className="generate-button"
            >
              추천인 코드 생성
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
                        {code.is_active ? '활성' : '비활성'}
                      </span>
                    </td>
                    <td>{code.usage_count}</td>
                    <td className="commission-amount">
                      {code.total_commission.toLocaleString()}원
                    </td>
                    <td>{new Date(code.created_at).toLocaleDateString()}</td>
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

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>관리자 대시보드</h1>
        <div className="header-actions">
          <button 
            className="btn-refresh"
            onClick={loadAdminData}
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
          </>
        )}
      </div>
    </div>
  )
}

export default AdminPage
