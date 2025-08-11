import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { getUserOrders, updateOrderStatus } from '../services/snspopApi'
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react'
import './OrdersPage.css'

const OrdersPage = () => {
  const { currentUser } = useAuth()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (currentUser) {
      fetchOrders()
    }
  }, [currentUser])

  const fetchOrders = async () => {
    try {
      setLoading(true)
      const userOrders = await getUserOrders(currentUser.email)
      setOrders(userOrders)
      setError(null)
    } catch (err) {
      setError('주문 정보를 불러오는데 실패했습니다.')
      console.error('주문 조회 오류:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchOrders()
    setRefreshing(false)
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return <Clock size={16} className="status-icon pending" />
      case 'completed':
        return <CheckCircle size={16} className="status-icon completed" />
      case 'cancelled':
        return <XCircle size={16} className="status-icon cancelled" />
      case 'processing':
        return <RefreshCw size={16} className="status-icon processing" />
      default:
        return <AlertCircle size={16} className="status-icon unknown" />
    }
  }

  const getStatusText = (status) => {
    switch (status) {
      case 'pending':
        return '대기중'
      case 'completed':
        return '완료'
      case 'cancelled':
        return '취소됨'
      case 'processing':
        return '처리중'
      default:
        return '알 수 없음'
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatPrice = (price) => {
    return new Intl.NumberFormat('ko-KR').format(price)
  }

  if (!currentUser) {
    return (
      <div className="orders-page">
        <div className="orders-container">
          <h1>주문 내역</h1>
          <p>로그인이 필요합니다.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="orders-page">
        <div className="orders-container">
          <h1>주문 내역</h1>
          <div className="loading">주문 정보를 불러오는 중...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="orders-page">
      <div className="orders-container">
        <div className="orders-header">
          <h1>주문 내역</h1>
          <button 
            onClick={handleRefresh} 
            className="refresh-btn"
            disabled={refreshing}
          >
            <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
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
            <p>아직 주문 내역이 없습니다.</p>
            <p>첫 번째 주문을 시작해보세요!</p>
          </div>
        ) : (
          <div className="orders-list">
            {orders.map((order) => (
              <div key={order.id} className="order-card">
                <div className="order-header">
                  <div className="order-status">
                    {getStatusIcon(order.status)}
                    <span className="status-text">{getStatusText(order.status)}</span>
                  </div>
                  <div className="order-date">
                    {formatDate(order.created_at)}
                  </div>
                </div>
                
                <div className="order-content">
                  <div className="order-info">
                    <div className="platform-service">
                      <span className="platform">{order.platform}</span>
                      <span className="service">{order.service}</span>
                    </div>
                    <div className="order-details">
                      <div className="detail-item">
                        <span className="label">수량:</span>
                        <span className="value">{formatPrice(order.quantity)}</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">가격:</span>
                        <span className="value">₩{formatPrice(order.price)}</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">링크:</span>
                        <span className="value link">{order.link}</span>
                      </div>
                    </div>
                  </div>
                  
                  {order.snspop_order_id && (
                    <div className="snspop-order-id">
                      <span className="label">주문 ID:</span>
                      <span className="value">{order.snspop_order_id}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default OrdersPage
