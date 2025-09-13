import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { CreditCard, CheckCircle, AlertCircle, ArrowLeft } from 'lucide-react'
import './PointPaymentPage.css'

const PointPaymentPage = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { orderData, userPoints } = location.state || {}
  
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  // 주문 데이터가 없으면 홈으로 리다이렉트
  useEffect(() => {
    if (!orderData) {
      navigate('/')
    }
  }, [orderData, navigate])

  const handlePayment = async () => {
    if (!orderData) return
    
    setIsProcessing(true)
    setError('')
    
    try {
      // 1. 포인트 차감
      const deductResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/points/deduct`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: orderData.user_id,
          amount: orderData.total_price
        })
      })

      if (!deductResponse.ok) {
        const errorData = await deductResponse.json()
        throw new Error(errorData.error || '포인트 차감 실패')
      }

      const deductResult = await deductResponse.json()
      console.log('포인트 차감 성공:', deductResult)

      // 2. 주문 생성
      const orderResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(orderData)
      })

      if (!orderResponse.ok) {
        const errorData = await orderResponse.json()
        throw new Error(errorData.error || '주문 생성 실패')
      }

      const orderResult = await orderResponse.json()
      console.log('주문 생성 성공:', orderResult)

      // 3. SMM Panel API 호출 (백엔드 프록시 사용)
      try {
        const smmResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/smm-panel`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            action: 'add',
            service: orderData.service_id,
            link: orderData.link,
            quantity: orderData.quantity,
            key: '5efae48d287931cf9bd80a1bc6fdfa6d'
          })
        })

        if (smmResponse.ok) {
          const smmResult = await smmResponse.json()
          console.log('SMM Panel API 성공:', smmResult)
        } else {
          console.warn('SMM Panel API 실패, 하지만 주문은 완료됨')
        }
      } catch (smmError) {
        console.warn('SMM Panel API 오류:', smmError)
        // SMM Panel API 실패해도 주문은 완료된 것으로 처리
      }

      setSuccess(true)
      
      // 2초 후 주문 완료 페이지로 이동
      setTimeout(() => {
        navigate('/order-complete', { 
          state: { 
            orderId: orderResult.order_id,
            orderData: orderData
          }
        })
      }, 2000)

    } catch (error) {
      console.error('결제 오류:', error)
      setError(error.message)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleBack = () => {
    navigate(-1)
  }

  if (!orderData) {
    return null
  }

  return (
    <div className="point-payment-page">
      <div className="payment-container">
        <div className="payment-header">
          <button className="back-button" onClick={handleBack}>
            <ArrowLeft size={20} />
            뒤로가기
          </button>
          <h1>포인트 결제</h1>
        </div>

        {success ? (
          <div className="success-card">
            <CheckCircle className="success-icon" size={48} />
            <h2>결제 처리 중...</h2>
            <p>주문이 완료되었습니다. 잠시만 기다려주세요.</p>
          </div>
        ) : (
          <>
            <div className="order-summary">
              <h2>주문 요약</h2>
              <div className="summary-item">
                <span>서비스:</span>
                <span>{orderData.service_name}</span>
              </div>
              <div className="summary-item">
                <span>수량:</span>
                <span>{orderData.quantity.toLocaleString()}개</span>
              </div>
              <div className="summary-item">
                <span>단가:</span>
                <span>{orderData.unit_price.toLocaleString()}원</span>
              </div>
              <div className="summary-item total">
                <span>총 금액:</span>
                <span>{orderData.total_price.toLocaleString()}원</span>
              </div>
            </div>

            <div className="payment-method">
              <h2>결제 방법</h2>
              <div className="payment-option selected">
                <CreditCard className="payment-icon" size={24} />
                <div className="payment-info">
                  <h3>포인트 결제</h3>
                  <p>보유 포인트: {userPoints?.points?.toLocaleString() || 0}원</p>
                </div>
              </div>
            </div>

            {error && (
              <div className="error-message">
                <AlertCircle size={20} />
                <span>{error}</span>
              </div>
            )}

            <div className="payment-actions">
              <button 
                className="payment-button"
                onClick={handlePayment}
                disabled={isProcessing || (userPoints?.points || 0) < orderData.total_price}
              >
                {isProcessing ? '결제 처리 중...' : '포인트로 결제하기'}
              </button>
              
              {(userPoints?.points || 0) < orderData.total_price && (
                <p className="insufficient-points">
                  포인트가 부족합니다. 포인트를 충전해주세요.
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default PointPaymentPage
