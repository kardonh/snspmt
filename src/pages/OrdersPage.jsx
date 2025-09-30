import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import smmpanelApi from '../services/snspopApi'
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw, Eye, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import './OrdersPage.css'

// 주문 현황 상태 상수
const ORDER_STATUS = {
  SCHEDULED: 'scheduled',     // 예약됨
  RECEIVED: 'received',       // 접수됨
  IN_PROGRESS: 'in_progress', // 실행중
  COMPLETED: 'completed'      // 완료
}

// 주문 현황 상태 한글 매핑
const ORDER_STATUS_LABELS = {
  [ORDER_STATUS.SCHEDULED]: '예약됨',
  [ORDER_STATUS.RECEIVED]: '접수됨',
  [ORDER_STATUS.IN_PROGRESS]: '실행중',
  [ORDER_STATUS.COMPLETED]: '완료'
}

// 주문 현황 상태 색상 매핑
const ORDER_STATUS_COLORS = {
  [ORDER_STATUS.SCHEDULED]: '#f59e0b',    // 주황색
  [ORDER_STATUS.RECEIVED]: '#3b82f6',     // 파란색
  [ORDER_STATUS.IN_PROGRESS]: '#8b5cf6',  // 보라색
  [ORDER_STATUS.COMPLETED]: '#10b981'     // 초록색
}

// 주문 현황 배지 컴포넌트
const OrderStatusBadge = ({ status }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case ORDER_STATUS.SCHEDULED:
        return <Clock size={14} />
      case ORDER_STATUS.RECEIVED:
        return <AlertCircle size={14} />
      case ORDER_STATUS.IN_PROGRESS:
        return <RefreshCw size={14} />
      case ORDER_STATUS.COMPLETED:
        return <CheckCircle size={14} />
      default:
        return <Clock size={14} />
    }
  }

  return (
    <div 
      className="order-status-badge"
      style={{ 
        backgroundColor: ORDER_STATUS_COLORS[status] || '#6b7280',
        color: 'white'
      }}
    >
      {getStatusIcon(status)}
      <span>{ORDER_STATUS_LABELS[status] || '알 수 없음'}</span>
    </div>
  )
}

const OrdersPage = () => {
  const { currentUser } = useAuth()
  const [orders, setOrders] = useState([])
  const [filteredOrders, setFilteredOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [showOrderDetail, setShowOrderDetail] = useState(false)
  const [selectedFilter, setSelectedFilter] = useState('전체')
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [ordersPerPage] = useState(10)

  useEffect(() => {
    if (currentUser) {
      loadOrders()
    }
  }, [currentUser])

  useEffect(() => {
    filterAndSearchOrders()
  }, [orders, selectedFilter, searchTerm])

  const loadOrders = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const userId = currentUser?.uid || localStorage.getItem('userId') || 'demo_user'
      console.log('🔍 주문내역 조회 - 사용자 ID:', userId)
      
      // 올바른 API 호출
      const response = await fetch(`/api/orders?user_id=${userId}`)
      console.log('📦 주문내역 API 응답:', response.status, response.statusText)
      
      if (response.ok) {
        const data = await response.json()
        console.log('📦 주문내역 데이터:', data)
        if (data.orders) {
          setOrders(data.orders)
          console.log('✅ 주문내역 로드 성공:', data.orders.length, '개')
        } else {
          setOrders([])
          console.log('ℹ️ 주문내역 없음')
        }
      } else {
        console.error('❌ 주문내역 API 오류:', response.status)
        setOrders([])
        setError('주문 목록을 불러오는데 실패했습니다.')
      }
    } catch (err) {
      console.error('❌ 주문 목록 로드 실패:', err)
      setError('주문 목록을 불러오는데 실패했습니다.')
      setOrders([])
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return <CheckCircle size={20} className="status-icon completed" />
      case 'canceled':
        return <XCircle size={20} className="status-icon canceled" />
      case 'pending':
        return <Clock size={20} className="status-icon pending" />
      case 'processing':
        return <RefreshCw size={20} className="status-icon processing" />
      case 'pending_payment':
        return <AlertCircle size={20} className="status-icon pending" />
      case 'scheduled':
        return <Clock size={20} className="status-icon scheduled" />
      case 'received':
        return <AlertCircle size={20} className="status-icon received" />
      case 'in_progress':
        return <RefreshCw size={20} className="status-icon in-progress" />
      default:
        return <AlertCircle size={20} className="status-icon unknown" />
    }
  }

  const getStatusText = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return '완료'
      case 'canceled':
        return '주문 취소 및 전액 환불'
      case 'pending':
        return '주문 대기 중'
      case 'processing':
        return '주문 준비 및 가동 중'
      case 'pending_payment':
        return '주문 접수'
      case 'scheduled':
        return '예약됨'
      case 'received':
        return '접수됨'
      case 'in_progress':
        return '실행중'
      default:
        return '알 수 없음'
    }
  }

  const filterAndSearchOrders = () => {
    let filtered = [...orders]

    // 상태 필터링
    if (selectedFilter !== '전체') {
      filtered = filtered.filter(order => {
        const statusText = getStatusText(order.status)
        return statusText === selectedFilter
      })
    }

    // 검색어 필터링
    if (searchTerm.trim()) {
      const searchLower = searchTerm.toLowerCase()
      filtered = filtered.filter(order => 
        order.id?.toLowerCase().includes(searchLower) ||
        order.service?.toLowerCase().includes(searchLower) ||
        order.link?.toLowerCase().includes(searchLower)
      )
    }

    setFilteredOrders(filtered)
    setCurrentPage(1) // 필터 변경 시 첫 페이지로
  }

  const handleFilterChange = (filter) => {
    setSelectedFilter(filter)
  }

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value)
  }

  // 페이지네이션 계산
  const totalPages = Math.ceil(filteredOrders.length / ordersPerPage)
  const startIndex = (currentPage - 1) * ordersPerPage
  const endIndex = startIndex + ordersPerPage
  const currentOrders = filteredOrders.slice(startIndex, endIndex)

  const handlePageChange = (page) => {
    setCurrentPage(page)
  }

  const getStatusClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'status-completed'
      case 'canceled':
        return 'status-canceled'
      case 'pending':
        return 'status-pending'
      case 'processing':
        return 'status-processing'
      case 'pending_payment':
        return 'status-pending'
      default:
        return 'status-unknown'
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString('ko-KR')
  }

  const handleViewDetail = async (order) => {
    try {
      // 주문 상세 정보는 이미 orders 배열에 있으므로 직접 사용
      setSelectedOrder(order)
      setShowOrderDetail(true)
    } catch (err) {
      console.error('주문 상세 정보 로드 실패:', err)
      alert('주문 상세 정보를 불러오는데 실패했습니다.')
    }
  }

  const closeOrderDetail = () => {
    setShowOrderDetail(false)
    setSelectedOrder(null)
  }

  if (loading) {
    return (
      <div className="orders-page">
        <div className="orders-container">
          <div className="orders-header">
            <h1>주문 내역</h1>
          </div>
          <div className="loading-simple">
            <RefreshCw size={24} className="loading-icon" />
            <span>로딩 중...</span>
          </div>
        </div>
      </div>
    )
  }

  const filterOptions = [
    '전체',
    '예약됨',
    '접수됨', 
    '실행중',
    '완료',
    '주문 접수',
    '주문 준비 및 가동 중',
    '부분 완료 (작업 안된 만큼 환불)',
    '주문 대기 중',
    '주문 취소 및 전액 환불'
  ]

  return (
    <div className="orders-page">
      <div className="orders-container">
        <div className="orders-header">
          <h1>주문내역 관리</h1>
        </div>

        <div className="orders-controls">
          <div className="filter-buttons">
            {filterOptions.map((filter) => (
              <button
                key={filter}
                className={`filter-btn ${selectedFilter === filter ? 'active' : ''}`}
                onClick={() => handleFilterChange(filter)}
              >
                {filter}
              </button>
            ))}
          </div>
          
          <div className="search-container">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="주문조회"
              value={searchTerm}
              onChange={handleSearchChange}
              className="search-input"
            />
          </div>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {filteredOrders.length === 0 ? (
          <div className="no-orders">
            <AlertCircle size={48} />
            <h3>주문 내역이 없습니다</h3>
            <p>첫 번째 주문을 시작해보세요!</p>
          </div>
        ) : (
          <>
            <div className="orders-list">
              {currentOrders.map((order) => (
                <div key={order.id} className="order-card">
                  <div className="order-header">
                    <div className="order-id">
                      <span className="label">주문번호:</span>
                      <span className="value">{order.id}</span>
                    </div>
                    <div className="order-status-section">
                      <div className={`order-status ${getStatusClass(order.status)}`}>
                        {getStatusIcon(order.status)}
                        <span>{getStatusText(order.status)}</span>
                      </div>
                      {/* 예약 발송 주문인 경우 주문 현황 배지 표시 */}
                      {order.scheduled && (
                        <OrderStatusBadge status={ORDER_STATUS.SCHEDULED} />
                      )}
                    </div>
                  </div>
                  
                  <div className="order-content">
                    <div className="order-info">
                      <div className="info-row">
                        <span className="label">서비스:</span>
                        <span className="value">{order.service || 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">링크:</span>
                        <span className="value link">{order.link || 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">수량:</span>
                        <span className="value">{order.quantity?.toLocaleString() || 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">주문일:</span>
                        <span className="value">{formatDate(order.created_at)}</span>
                      </div>
                    </div>
                    
                    <div className="order-actions">
                      <button 
                        onClick={() => handleViewDetail(order)}
                        className="detail-btn"
                      >
                        <Eye size={16} />
                        상세보기
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {totalPages > 1 && (
              <div className="pagination">
                <button 
                  className="pagination-btn"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft size={16} />
                </button>
                <div className="pagination-info">
                  {currentPage} / {totalPages}
                </div>
                <button 
                  className="pagination-btn"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* 주문 상세 정보 모달 */}
      {showOrderDetail && selectedOrder && (
        <div className="modal-overlay" onClick={closeOrderDetail}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>주문 상세 정보</h2>
              <button onClick={closeOrderDetail} className="close-btn">×</button>
            </div>
            
            <div className="modal-body">
              <div className="detail-section">
                <h3>기본 정보</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="label">주문번호:</span>
                    <span className="value">{selectedOrder.id}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">상태:</span>
                    <span className={`value ${getStatusClass(selectedOrder.status)}`}>
                      {getStatusText(selectedOrder.status)}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="label">서비스:</span>
                    <span className="value">{selectedOrder.service || 'N/A'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">링크:</span>
                    <span className="value link">{selectedOrder.link || 'N/A'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">수량:</span>
                    <span className="value">{selectedOrder.quantity?.toLocaleString() || 'N/A'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">주문일:</span>
                    <span className="value">{formatDate(selectedOrder.created_at)}</span>
                  </div>
                </div>
              </div>
              
              {selectedOrder.start_count !== undefined && (
                <div className="detail-section">
                  <h3>진행 상황</h3>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="label">시작 수량:</span>
                      <span className="value">{selectedOrder.start_count?.toLocaleString() || '0'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">남은 수량:</span>
                      <span className="value">{selectedOrder.remains?.toLocaleString() || '0'}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default OrdersPage
