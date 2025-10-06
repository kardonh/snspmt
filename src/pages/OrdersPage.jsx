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
      
      // 30초마다 주문 상태 업데이트
      const interval = setInterval(() => {
        loadOrders()
      }, 30000)
      
      return () => clearInterval(interval)
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
      
      // 올바른 API 호출
      const response = await fetch(`/api/orders?user_id=${userId}`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.orders) {
          setOrders(data.orders)
          
          // 첫 번째 주문의 데이터 구조 확인
          if (data.orders.length > 0) {
            console.log('🔍 첫 번째 주문 데이터 구조:', data.orders[0])
            console.log('🔍 주문번호 필드들:', {
              id: data.orders[0].id,
              order_id: data.orders[0].order_id,
              order_number: data.orders[0].order_number,
              orderId: data.orders[0].orderId
            })
          }
        } else {
          setOrders([])
        }
      } else {
        setOrders([])
        setError('주문 목록을 불러오는데 실패했습니다.')
      }
    } catch (err) {
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
      case 'cancelled':
        return <XCircle size={20} className="status-icon canceled" />
      case 'pending':
        return <Clock size={20} className="status-icon pending" />
      case 'processing':
      case 'package_processing':
        return <RefreshCw size={20} className="status-icon processing" />
      case 'pending_payment':
        return <AlertCircle size={20} className="status-icon pending" />
      case 'scheduled':
        return <Clock size={20} className="status-icon scheduled" />
      case 'received':
        return <AlertCircle size={20} className="status-icon received" />
      case 'in_progress':
        return <RefreshCw size={20} className="status-icon in-progress" />
      case 'split_scheduled':
        return <Clock size={20} className="status-icon scheduled" />
      case 'failed':
        return <XCircle size={20} className="status-icon canceled" />
      case 'partial_completed':
        return <CheckCircle size={20} className="status-icon completed" />
      default:
        return <AlertCircle size={20} className="status-icon unknown" />
    }
  }

  const getStatusText = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return '완료'
      case 'canceled':
      case 'cancelled':
        return '주문 취소 및 전액 환불'
      case 'pending':
        return '주문 대기 중'
      case 'processing':
      case 'package_processing':
        return '주문 준비 및 가동 중'
      case 'pending_payment':
        return '주문 접수'
      case 'scheduled':
        return '예약됨'
      case 'received':
        return '접수됨'
      case 'in_progress':
        return '실행중'
      case 'split_scheduled':
        return '분할 발송 예약됨'
      case 'failed':
        return '실패'
      case 'partial_completed':
        return '부분 완료 (작업 안된 만큼 환불)'
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
        (order.id || order.order_id)?.toString().toLowerCase().includes(searchLower) ||
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
      case 'cancelled':
        return 'status-canceled'
      case 'pending':
        return 'status-pending'
      case 'processing':
      case 'package_processing':
        return 'status-processing'
      case 'pending_payment':
        return 'status-pending'
      case 'scheduled':
        return 'status-scheduled'
      case 'received':
        return 'status-received'
      case 'in_progress':
        return 'status-in-progress'
      case 'split_scheduled':
        return 'status-scheduled'
      case 'failed':
        return 'status-canceled'
      case 'partial_completed':
        return 'status-completed'
      default:
        return 'status-unknown'
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString('ko-KR')
  }

  const formatScheduledTime = (scheduledDatetime) => {
    if (!scheduledDatetime) return 'N/A'
    
    // scheduled_datetime이 "YYYY-MM-DD HH:MM" 형식인 경우
    if (typeof scheduledDatetime === 'string' && scheduledDatetime.includes(' ')) {
      const [date, time] = scheduledDatetime.split(' ')
      const [year, month, day] = date.split('-')
      const [hour, minute] = time.split(':')
      
      const scheduledDate = new Date(year, month - 1, day, hour, minute)
      return scheduledDate.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      })
    }
    
    // 일반 Date 객체인 경우
    const date = new Date(scheduledDatetime)
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  const getPackageProgress = (order) => {
    if (!order.package_steps || order.package_steps.length === 0) {
      return '패키지 정보 없음'
    }

    // 패키지 진행 상황 계산
    const totalSteps = order.package_steps.length
    const completedSteps = order.package_progress ? order.package_progress.filter(p => p.status === 'completed').length : 0
    
    if (completedSteps === totalSteps) {
      return `✅ 모든 단계 완료 (${completedSteps}/${totalSteps})`
    } else if (completedSteps === 0) {
      return `⏳ 대기 중 (0/${totalSteps})`
    } else {
      return `🔄 진행 중 (${completedSteps}/${totalSteps} 단계 완료)`
    }
  }

  const getSplitDeliveryProgress = (order) => {
    if (!order.is_split_delivery || !order.split_days || !order.split_quantity) {
      return '분할 발송 정보 없음'
    }

    const orderDate = new Date(order.created_at)
    const today = new Date()
    const daysPassed = Math.floor((today - orderDate) / (1000 * 60 * 60 * 24))
    
    const totalDays = order.split_days
    const dailyQuantity = order.split_quantity
    const totalQuantity = order.quantity || 0
    
    // 진행률 계산
    const progressDays = Math.min(daysPassed, totalDays)
    const completedQuantity = Math.min(progressDays * dailyQuantity, totalQuantity)
    const remainingQuantity = Math.max(0, totalQuantity - completedQuantity)
    
    // 상태 결정
    let status = ''
    if (daysPassed >= totalDays) {
      status = '완료'
    } else if (daysPassed > 0) {
      status = '진행중'
    } else {
      status = '대기중'
    }

    return `${status} (${completedQuantity}/${totalQuantity}개 완료, ${remainingQuantity}개 남음)`
  }

  const handleViewDetail = async (order) => {
    try {
      // 디버깅: 주문 데이터 구조 확인
      
      // 주문 상세 정보는 이미 orders 배열에 있으므로 직접 사용
      setSelectedOrder(order)
      setShowOrderDetail(true)
    } catch (err) {
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
    '주문 대기 중',
    '주문 접수',
    '주문 준비 및 가동 중',
    '실행중',
    '완료',
    '부분 완료 (작업 안된 만큼 환불)',
    '예약됨',
    '접수됨',
    '주문 취소 및 전액 환불'
  ]

  return (
    <div className="orders-page">
      <div className="orders-container">
        <div className="orders-header">
          <h1>주문내역 관리</h1>
          <button 
            className="refresh-btn"
            onClick={loadOrders}
            disabled={loading}
            title="주문 상태 새로고침"
          >
            <RefreshCw size={20} className={loading ? 'loading-icon' : ''} />
            새로고침
          </button>
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
                <div key={order.order_id || order.id} className="order-card">
                  <div className="order-header">
                    <div className="order-id">
                      <span className="label">주문번호:</span>
                      <span className="value">
                        {order.order_id || order.id || order.order_number || 'N/A'}
                      </span>
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
                      {/* 패키지 주문인 경우 패키지 배지 표시 */}
                      {order.package_steps && order.package_steps.length > 0 && (
                        <OrderStatusBadge status={ORDER_STATUS.IN_PROGRESS} />
                      )}
                      {/* 분할 발송 주문인 경우 분할 발송 배지 표시 */}
                      {order.is_split_delivery && (
                        <OrderStatusBadge status={ORDER_STATUS.IN_PROGRESS} />
                      )}
                    </div>
                  </div>
                  
                  <div className="order-content">
                    <div className="order-info">
                      <div className="info-row">
                        <span className="label">서비스:</span>
                        <span className="value">
                          {order.detailed_service || order.service_name || order.service || order.platform || 'N/A'}
                        </span>
                      </div>
                      <div className="info-row">
                        <span className="label">서비스 ID:</span>
                        <span className="value">{order.service_id || 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">수량:</span>
                        <span className="value">{order.quantity ? order.quantity.toLocaleString() : 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">가격:</span>
                        <span className="value">{order.price ? `${order.price.toLocaleString()}원` : 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">주문일:</span>
                        <span className="value">{formatDate(order.created_at)}</span>
                      </div>
                      {/* 예약 발송 주문인 경우 예약 시간 표시 */}
                      {order.scheduled && order.scheduled_datetime && (
                        <div className="info-row scheduled-time-row">
                          <span className="label">예약 시간:</span>
                          <span className="value scheduled-time">{formatScheduledTime(order.scheduled_datetime)}</span>
                        </div>
                      )}
                      
                      {/* 패키지 주문인 경우 진행 상황 표시 */}
                      {order.package_steps && order.package_steps.length > 0 && (
                        <div className="package-progress-section">
                          <div className="info-row package-delivery-row">
                            <span className="label">패키지 진행:</span>
                            <span className="value package-delivery-info">
                              {getPackageProgress(order)}
                            </span>
                          </div>
                          {/* 패키지 단계별 상세 정보 */}
                          <div className="package-steps-detail">
                            {order.package_steps.map((step, index) => (
                              <div key={step.id || index} className="package-step-item">
                                <div className="step-header">
                                  <span className="step-number">{index + 1}</span>
                                  <span className="step-name">{step.name}</span>
                                  <span className="step-quantity">({step.quantity ? step.quantity.toLocaleString() : 0}개)</span>
                                </div>
                                {step.description && (
                                  <div className="step-description">{step.description}</div>
                                )}
                                {step.delay && step.delay > 0 && (
                                  <div className="step-delay">⏰ {step.delay}분 후 실행</div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* 분할 발송 주문인 경우 진행 상황 표시 */}
                      {order.is_split_delivery && (
                        <div className="info-row split-delivery-row">
                          <span className="label">분할 발송:</span>
                          <span className="value split-delivery-info">
                            {getSplitDeliveryProgress(order)}
                          </span>
                        </div>
                      )}
                    </div>
                    
                    {/* 링크 섹션을 별도로 분리하여 아래에 배치 */}
                    {order.link && (
                      <div className="order-link-section">
                        <div className="link-container">
                          <span className="link-label">링크:</span>
                          <span className="link-value">{order.link}</span>
                        </div>
                      </div>
                    )}
                    
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
                    <span className="value">{selectedOrder.quantity ? selectedOrder.quantity.toLocaleString() : 'N/A'}</span>
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
                      <span className="value">{selectedOrder.start_count ? selectedOrder.start_count.toLocaleString() : '0'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">남은 수량:</span>
                      <span className="value">{selectedOrder.remains ? selectedOrder.remains.toLocaleString() : '0'}</span>
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
