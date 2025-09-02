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
  Activity
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
    pendingPurchases: 0
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

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    loadAdminData()
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
          pendingPurchases: data.pendingPurchases || 0
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
    <div className="dashboard-grid">
      <div className="stat-card">
        <div className="stat-icon users">
          <Users size={24} />
        </div>
        <div className="stat-content">
          <h3>총 사용자</h3>
          <p className="stat-number">{dashboardData.totalUsers.toLocaleString()}</p>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon orders">
          <ShoppingCart size={24} />
        </div>
        <div className="stat-content">
          <h3>총 주문</h3>
          <p className="stat-number">{dashboardData.totalOrders.toLocaleString()}</p>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon revenue">
          <DollarSign size={24} />
        </div>
        <div className="stat-content">
          <h3>총 매출</h3>
          <p className="stat-number">₩{dashboardData.totalRevenue.toLocaleString()}</p>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon pending">
          <Activity size={24} />
        </div>
        <div className="stat-content">
          <h3>대기 중인 구매</h3>
          <p className="stat-number">{dashboardData.pendingPurchases}</p>
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
          </>
        )}
      </div>
    </div>
  )
}

export default AdminPage
