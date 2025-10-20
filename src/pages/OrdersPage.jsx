import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import smmpanelApi from '../services/snspopApi'
import { Copy, ExternalLink, Plus, ChevronLeft, ChevronRight } from 'lucide-react'
import './OrdersPage.css'

// 주문 현황 상태 상수 (4개로 단순화)
const ORDER_STATUS = {
  ALL: 'all',                    // 전체
  SENT: '주문발송',              // 주문발송
  IN_PROGRESS: '주문 실행중',    // 주문 실행중
  COMPLETED: '주문 실행완료',    // 주문 실행완료
  UNPROCESSED: '주문 미처리'     // 주문 미처리
}

// 주문 현황 상태 한글 매핑
const ORDER_STATUS_LABELS = {
  [ORDER_STATUS.ALL]: '전체',
  [ORDER_STATUS.SENT]: '주문발송',
  [ORDER_STATUS.IN_PROGRESS]: '주문 실행중',
  [ORDER_STATUS.COMPLETED]: '주문 실행완료',
  [ORDER_STATUS.UNPROCESSED]: '주문 미처리'
}

// 주문 카드 컴포넌트
const OrderCard = ({ order, onCopyOrderId, onCopyLink, onRefill }) => {
  const formatDate = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }).replace(/\./g, '-').replace(/,/g, '')
  }

  const getStatusColor = (status) => {
    switch (status) {
      case '주문 실행완료': return '#10b981'
      case '주문 실행중': return '#8b5cf6'
      case '주문발송': return '#3b82f6'
      case '주문 미처리': return '#ef4444'
      default: return '#6b7280'
    }
  }

  return (
    <div className="order-card">
      <div className="order-header">
        <div className="order-title">
          <span className="service-type">[일반]</span>
          <span className="service-name">{order.service_name || '서비스명'}</span>
          <Plus size={16} className="expand-icon" />
        </div>
        <button className="copy-link-btn" onClick={() => onCopyLink(order.link)}>
          링크복사
        </button>
      </div>
      
      <div className="order-link">
        <a href={order.link} target="_blank" rel="noopener noreferrer">
          {order.link}
        </a>
      </div>
      
      <div className="order-details">
        <div className="order-details-left">
          <div className="detail-item">
            <span className="detail-label">사용금액 :</span>
            <span className="detail-value amount">{order.charge || 0}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">남은수량:</span>
            <span className="detail-value">{order.remains || 0}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">주문번호 :</span>
            <span className="detail-value">{order.order_id}</span>
            <button className="copy-btn" onClick={() => onCopyOrderId(order.order_id)}>
              복사
            </button>
          </div>
          <div className="detail-item">
            <span className="detail-label">주문상태 :</span>
            <span 
              className="detail-value status"
              style={{ color: getStatusColor(order.status) }}
            >
              {ORDER_STATUS_LABELS[order.status] || '알 수 없음'}
            </span>
          </div>
        </div>
        
        <div className="order-details-right">
          <div className="detail-item">
            <span className="detail-label">주문수량 :</span>
            <span className="detail-value">{order.quantity || 0}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">주문전수량:</span>
            <span className="detail-value">{order.start_count || 0}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">주문일시:</span>
            <span className="detail-value">{formatDate(order.created_at)}</span>
          </div>
        </div>
      </div>
      
      {order.status === '주문 실행완료' && (
        <div className="order-actions">
          <button className="refill-btn" onClick={() => onRefill(order.order_id)}>
            리필(확인중)
          </button>
        </div>
      )}
    </div>
  )
}

const OrdersPage = () => {
  const { currentUser } = useAuth()
  const [orders, setOrders] = useState([])
  const [filteredOrders, setFilteredOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedFilter, setSelectedFilter] = useState(ORDER_STATUS.ALL)
  const [currentPage, setCurrentPage] = useState(1)
  const [ordersPerPage] = useState(10)
  const [copiedItems, setCopiedItems] = useState({})

  useEffect(() => {
    if (currentUser) {
      loadOrders()
      
      // 60초마다 주문 상태 업데이트 (성능 최적화)
      const interval = setInterval(() => {
        loadOrders()
      }, 60000)
      
      return () => clearInterval(interval)
    }
  }, [currentUser])

  useEffect(() => {
    filterOrders()
  }, [orders, selectedFilter])

  const loadOrders = async () => {
    if (!currentUser) return
    
    try {
      setLoading(true)
      const response = await smmpanelApi.getUserOrders(currentUser.uid)
      console.log('주문 내역 로드:', response)
      
      if (response && response.orders) {
        setOrders(response.orders)
      } else {
        setOrders([])
      }
    } catch (error) {
      console.error('주문 내역 로드 실패:', error)
      setError('주문 내역을 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const filterOrders = () => {
    let filtered = orders
    
    if (selectedFilter !== ORDER_STATUS.ALL) {
      filtered = orders.filter(order => order.status === selectedFilter)
    }

    setFilteredOrders(filtered)
    setCurrentPage(1) // 필터 변경 시 첫 페이지로 이동
  }

  const handleFilterChange = (filter) => {
    setSelectedFilter(filter)
  }

  const handleCopyOrderId = async (orderId) => {
    try {
      await navigator.clipboard.writeText(orderId)
      setCopiedItems(prev => ({ ...prev, [orderId]: true }))
      setTimeout(() => {
        setCopiedItems(prev => ({ ...prev, [orderId]: false }))
      }, 2000)
    } catch (error) {
      console.error('복사 실패:', error)
    }
  }

  const handleCopyLink = async (link) => {
    try {
      await navigator.clipboard.writeText(link)
      alert('링크가 복사되었습니다.')
    } catch (error) {
      console.error('링크 복사 실패:', error)
    }
  }

  const handleRefill = async (orderId) => {
    try {
      const response = await smmpanelApi.refillOrder(orderId)
      console.log('리필 요청:', response)
      alert('리필 요청이 완료되었습니다.')
      loadOrders() // 주문 목록 새로고침
    } catch (error) {
      console.error('리필 요청 실패:', error)
      alert('리필 요청에 실패했습니다.')
    }
  }

  // 페이지네이션 계산
  const indexOfLastOrder = currentPage * ordersPerPage
  const indexOfFirstOrder = indexOfLastOrder - ordersPerPage
  const currentOrders = filteredOrders.slice(indexOfFirstOrder, indexOfLastOrder)
  const totalPages = Math.ceil(filteredOrders.length / ordersPerPage)

  const handlePageChange = (page) => {
    setCurrentPage(page)
  }

  if (loading) {
    return (
      <div className="orders-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>주문 내역을 불러오는 중...</p>
          </div>
          </div>
    )
  }

  if (error) {
    return (
      <div className="orders-page">
        <div className="error-container">
          <p>{error}</p>
          <button onClick={loadOrders} className="retry-btn">
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="orders-page">
      <div className="orders-container">
        {/* 헤더 */}
        <div className="orders-header">
          <h1>주문내역 관리</h1>
        </div>

        {/* 필터 버튼들 (4개로 단순화) */}
        <div className="filter-section">
          <div className="filter-row">
            <button 
              className={`filter-btn ${selectedFilter === ORDER_STATUS.ALL ? 'active' : ''}`}
              onClick={() => handleFilterChange(ORDER_STATUS.ALL)}
            >
              {ORDER_STATUS_LABELS[ORDER_STATUS.ALL]}
            </button>
            <button 
              className={`filter-btn ${selectedFilter === ORDER_STATUS.SENT ? 'active' : ''}`}
              onClick={() => handleFilterChange(ORDER_STATUS.SENT)}
            >
              {ORDER_STATUS_LABELS[ORDER_STATUS.SENT]}
            </button>
            <button 
              className={`filter-btn ${selectedFilter === ORDER_STATUS.IN_PROGRESS ? 'active' : ''}`}
              onClick={() => handleFilterChange(ORDER_STATUS.IN_PROGRESS)}
            >
              {ORDER_STATUS_LABELS[ORDER_STATUS.IN_PROGRESS]}
            </button>
            <button
              className={`filter-btn ${selectedFilter === ORDER_STATUS.COMPLETED ? 'active' : ''}`}
              onClick={() => handleFilterChange(ORDER_STATUS.COMPLETED)}
            >
              {ORDER_STATUS_LABELS[ORDER_STATUS.COMPLETED]}
            </button>
          </div>
          <div className="filter-row">
            <button 
              className={`filter-btn ${selectedFilter === ORDER_STATUS.UNPROCESSED ? 'active' : ''}`}
              onClick={() => handleFilterChange(ORDER_STATUS.UNPROCESSED)}
            >
              {ORDER_STATUS_LABELS[ORDER_STATUS.UNPROCESSED]}
            </button>
          </div>
        </div>

        {/* 주문 목록 */}
        <div className="orders-list">
          {currentOrders.length === 0 ? (
          <div className="no-orders">
              <p>주문 내역이 없습니다.</p>
          </div>
        ) : (
            currentOrders.map((order) => (
              <OrderCard
                key={order.order_id}
                order={order}
                onCopyOrderId={handleCopyOrderId}
                onCopyLink={handleCopyLink}
                onRefill={handleRefill}
              />
            ))
                      )}
                    </div>
                    
        {/* 페이지네이션 */}
            {totalPages > 1 && (
              <div className="pagination">
                <button 
                  className="pagination-btn"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft size={16} />
                </button>
            <span className="pagination-info">
                  {currentPage} / {totalPages}
            </span>
                <button 
                  className="pagination-btn"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight size={16} />
                </button>
              </div>
        )}
      </div>
    </div>
  )
}

export default OrdersPage