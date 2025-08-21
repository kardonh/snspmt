import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { smmkingsApi } from '../services/snspopApi'
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw, Eye } from 'lucide-react'
import './OrdersPage.css'

const OrdersPage = () => {
  const { currentUser } = useAuth()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [showOrderDetail, setShowOrderDetail] = useState(false)

  useEffect(() => {
    if (currentUser) {
      loadOrders()
    }
  }, [currentUser])

  const loadOrders = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const userId = currentUser.uid || currentUser.email
      const response = await smmkingsApi.getUserOrders(userId)
      
      if (response.orders) {
        setOrders(response.orders)
      } else {
        setOrders([])
      }
    } catch (err) {
      console.error('주문 목록 로드 실패:', err)
      setError('주문 목록을 불러오는데 실패했습니다.')
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
      default:
        return <AlertCircle size={20} className="status-icon unknown" />
    }
  }

  const getStatusText = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return '완료'
      case 'canceled':
        return '취소됨'
      case 'pending':
        return '대기중'
      case 'processing':
        return '처리중'
      default:
        return '알 수 없음'
    }
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
      const userId = currentUser.uid || currentUser.email
      const response = await smmkingsApi.getOrderDetail(order.id, userId)
      setSelectedOrder(response)
      setShowOrderDetail(true)
    } catch (err) {
      console.error('주문 상세 정보 로드 실패:', err)
      setError('주문 상세 정보를 불러오는데 실패했습니다.')
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
          <div className="loading">
            <RefreshCw size={32} className="loading-icon" />
            <p>주문 정보를 불러오는 중...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="orders-page">
      <div className="orders-container">
        <div className="orders-header">
          <h1>주문 내역</h1>
          <button onClick={loadOrders} className="refresh-btn">
            <RefreshCw size={16} />
            새로고침
          </button>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {orders.length === 0 ? (
          <div className="no-orders">
            <AlertCircle size={48} />
            <h3>주문 내역이 없습니다</h3>
            <p>첫 번째 주문을 시작해보세요!</p>
          </div>
        ) : (
          <div className="orders-list">
            {orders.map((order) => (
              <div key={order.id} className="order-card">
                <div className="order-header">
                  <div className="order-id">
                    <span className="label">주문번호:</span>
                    <span className="value">{order.id}</span>
                  </div>
                  <div className={`order-status ${getStatusClass(order.status)}`}>
                    {getStatusIcon(order.status)}
                    <span>{getStatusText(order.status)}</span>
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
