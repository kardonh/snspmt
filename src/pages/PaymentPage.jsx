import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { ChevronLeft, CheckCircle, Coins, Star } from 'lucide-react'
import './PaymentPage.css'

const PaymentPage = () => {
  const { platform } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const orderData = location.state?.orderData

  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [paymentSuccess, setPaymentSuccess] = useState(false)
  const [availableCoupons, setAvailableCoupons] = useState([])
  const [selectedCoupon, setSelectedCoupon] = useState(null)
  const [showCouponModal, setShowCouponModal] = useState(false)
  const [finalPrice, setFinalPrice] = useState(orderData?.totalPrice || 0)

  // 주문 데이터가 없으면 홈으로 리다이렉트
  useEffect(() => {
    if (!orderData) {
      navigate('/')
      return
    }
  }, [orderData, navigate])

  // 쿠폰 데이터 로드
  useEffect(() => {
    const loadCoupons = async () => {
      try {
        const response = await fetch('/api/coupons')
        if (response.ok) {
          const coupons = await response.json()
          setAvailableCoupons(coupons)
        }
      } catch (error) {
        console.error('쿠폰 로드 실패:', error)
      }
    }
    loadCoupons()
  }, [])

  // 최종 가격 계산
  useEffect(() => {
    if (orderData) {
      let price = orderData.totalPrice || 0
      if (selectedCoupon) {
        if (selectedCoupon.type === 'percentage') {
          price = price * (1 - selectedCoupon.discount / 100)
        } else {
          price = Math.max(0, price - selectedCoupon.discount)
        }
      }
      setFinalPrice(Math.round(price))
    }
  }, [orderData, selectedCoupon])

  // 쿠폰 선택
  const handleCouponSelect = (coupon) => {
    setSelectedCoupon(coupon)
    setShowCouponModal(false)
  }

  // 쿠폰 선택 해제
  const handleCouponRemove = () => {
    setSelectedCoupon(null)
  }

  const paymentMethods = [
    {
      id: 'points',
      name: '포인트 결제',
      icon: Coins,
      description: '보유 포인트로 간편 결제',
      color: '#FF6B35',
      features: ['즉시 결제', '수수료 없음', '안전 보장']
    }
  ]

  const handlePaymentMethodSelect = (methodId) => {
    setSelectedPaymentMethod(methodId)
  }

  const getPaymentMethodName = (methodId) => {
    const method = paymentMethods.find(m => m.id === methodId)
    return method ? method.name : ''
  }

  const handlePayment = async () => {
    if (!selectedPaymentMethod) {
      alert('결제 방법을 선택해주세요.')
      return
    }

    setIsProcessing(true)

    // 포인트 결제 처리
    let paymentMessage = '포인트 결제를 진행합니다...'

    try {
      // 1. 포인트 차감
      const deductResponse = await fetch('/api/points/deduct', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: orderData.userId || orderData.user_id,
          amount: finalPrice
        })
      })

      if (!deductResponse.ok) {
        const errorData = await deductResponse.json()
        throw new Error(errorData.error || '포인트 차감 실패')
      }

      const deductResult = await deductResponse.json()

      // 2. SMM Panel API 호출 (백엔드 프록시 사용)
      try {
        // SMM Panel API용 데이터 변환 (새로운 API 형식)
        const smmOrderData = {
          action: 'add',
          service: orderData.service_id || orderData.detailedService?.id,
          link: orderData.link,
          quantity: orderData.quantity,
          runs: 1,
          interval: 0,
          key: '35246b890345d819e1110d5cea9d5565'
        }
        
        
        const smmResponse = await fetch('/api/smm-panel', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(smmOrderData)
        })

        if (smmResponse.ok) {
          const smmResult = await smmResponse.json()
          
          if (smmResult.success && smmResult.data) {
            // 새로운 API 형식: {"order": 23501}
            if (smmResult.data.order) {
            }
          } else {
          }
        } else {
          const errorData = await smmResponse.json().catch(() => ({ error: 'Unknown error' }))
        }
      } catch (smmError) {
        // SMM Panel API 실패해도 주문은 완료된 것으로 처리
      }

      // 3. 주문 생성 (결제 완료 후)
      const orderResponse = await fetch('/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': orderData.userId || orderData.user_id
        },
        body: JSON.stringify({
          user_id: orderData.userId || orderData.user_id,
          platform: orderData.platform,
          service: orderData.service,
          detailed_service: orderData.detailedService?.name || orderData.service_name,
          service_id: orderData.detailedService?.id || orderData.detailedService?.smmkings_id,
          link: orderData.link,
          quantity: orderData.quantity,
          comments: orderData.comments || '',
          explanation: orderData.explanation || '',
          total_price: finalPrice,
          discount: selectedCoupon ? (selectedCoupon.type === 'percentage' ? selectedCoupon.discount : (orderData.totalPrice - finalPrice)) : (orderData.discount || 0),
          is_scheduled: orderData.isScheduledOrder || false,
          scheduled_datetime: orderData.isScheduledOrder ? `${orderData.scheduledDate} ${orderData.scheduledTime}` : null,
          is_split_delivery: orderData.isSplitDelivery || false,
          split_days: orderData.splitDays || null,
          split_quantity: orderData.dailyQuantity || null,
          package_steps: orderData.detailedService?.package && orderData.detailedService?.steps ? orderData.detailedService.steps : [],
          use_coupon: orderData.discount > 0,
          coupon_id: orderData.discount > 0 ? 'manual_discount' : null,
          coupon_discount: orderData.discount || 0
        })
      })

      if (!orderResponse.ok) {
        const orderError = await orderResponse.json()
        throw new Error(orderError.error || '주문 생성 실패')
      }

      const orderResult = await orderResponse.json()

      // 4. 결제 성공 처리
      setIsProcessing(false)
      setPaymentSuccess(true)
      
      // 2초 후 주문 완료 페이지로 이동
      setTimeout(() => {
        navigate('/order-complete', { 
          state: { 
            orderId: orderResult.order_id || orderResult.order,
            orderData: orderData,
            paymentMethod: getPaymentMethodName(selectedPaymentMethod)
          }
        })
      }, 2000)

    } catch (error) {
      alert(`결제 실패: ${error.message}`)
      setIsProcessing(false)
    }
  }

  const handleBack = () => {
    navigate(-1)
  }

  if (!orderData) {
    return null
  }

  if (paymentSuccess) {
    return (
      <div className="payment-success">
        <div className="success-content">
          <CheckCircle className="success-icon" />
          <h2>결제가 완료되었습니다!</h2>
          <p>주문 완료 페이지로 이동합니다...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="payment-page">
      <div className="payment-header">
        <button className="back-button" onClick={handleBack}>
          <ChevronLeft />
          뒤로가기
        </button>
        <h1>포인트 결제</h1>
      </div>

      <div className="payment-container">
        {/* 주문 요약 */}
        <div className="order-summary">
          <h2>주문 요약</h2>
          <div className="summary-content">
            <div className="summary-row">
              <span>플랫폼:</span>
              <span className="platform-name">
                {platform === 'instagram' ? '인스타그램' : 
                 platform === 'tiktok' ? '틱톡' : 
                 platform === 'youtube' ? '유튜브' : platform}
              </span>
            </div>
            <div className="summary-row">
              <span>서비스:</span>
              <span>{orderData.serviceName}</span>
            </div>
            <div className="summary-row">
              <span>수량:</span>
              <span>{orderData.quantity.toLocaleString()}개</span>
            </div>
            <div className="summary-row">
              <span>링크:</span>
              <span className="order-link">{orderData.link}</span>
            </div>
            {orderData.comments && (
              <div className="summary-row">
                <span>댓글:</span>
                <span className="order-comments">{orderData.comments}</span>
              </div>
            )}
            {orderData.explanation && (
              <div className="summary-row">
                <span>추가 요청사항:</span>
                <span className="order-explanation">{orderData.explanation}</span>
              </div>
            )}
          </div>
        </div>

        {/* 가격 정보 */}
        <div className="price-summary">
          <h2>가격 정보</h2>
          <div className="price-content">
            <div className="price-row">
              <span>1000개 단가:</span>
              <span>{orderData.unitPrice}원</span>
            </div>
            <div className="price-row">
              <span>수량:</span>
              <span>{orderData.quantity.toLocaleString()}개</span>
            </div>
            {/* 쿠폰 선택 */}
            <div className="coupon-section">
              <div className="coupon-header">
                <span>할인 쿠폰:</span>
                <button 
                  className="coupon-select-btn"
                  onClick={() => setShowCouponModal(true)}
                >
                  {selectedCoupon ? selectedCoupon.name : '쿠폰 선택'}
                </button>
              </div>
              {selectedCoupon && (
                <div className="selected-coupon">
                  <span className="coupon-name">{selectedCoupon.name}</span>
                  <button 
                    className="coupon-remove-btn"
                    onClick={handleCouponRemove}
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>
            
            {selectedCoupon && (
              <div className="price-row discount">
                <span>할인 ({selectedCoupon.type === 'percentage' ? selectedCoupon.discount + '%' : selectedCoupon.discount + '원'}):</span>
                <span>-{(orderData.totalPrice - finalPrice).toLocaleString()}원</span>
              </div>
            )}
            <div className="price-row total">
              <span>총 결제금액:</span>
              <span>{finalPrice.toLocaleString()}원</span>
            </div>
          </div>
        </div>

        {/* 포인트 결제 방법 */}
        <div className="payment-methods">
          <h2>포인트 결제</h2>
          
          {/* 포인트 결제 섹션 */}
          <div className="points-payment-section">
            <h3>💰 포인트 결제 <span className="recommended-badge">추천</span></h3>
            <p className="points-payment-info">보유 포인트로 간편하고 안전하게 결제하세요. 수수료 없이 즉시 처리됩니다.</p>
            <div className="methods-grid points-methods">
              {paymentMethods.map((method) => (
                <div
                  key={method.id}
                  className={`payment-method points-method ${selectedPaymentMethod === method.id ? 'selected' : ''}`}
                  onClick={() => handlePaymentMethodSelect(method.id)}
                  style={{ '--method-color': method.color }}
                >
                  <div className="method-icon" style={{ backgroundColor: method.color + '20', color: method.color }}>
                    <method.icon />
                  </div>
                  <div className="method-info">
                    <h3>{method.name}</h3>
                    <p>{method.description}</p>
                    <div className="method-features">
                      {method.features.map((feature, index) => (
                        <span key={index} className="feature">{feature}</span>
                      ))}
                    </div>
                  </div>
                  <div className="method-check">
                    {selectedPaymentMethod === method.id && <CheckCircle />}
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* 결제 버튼 */}
        <div className="payment-actions">
          <button
            className={`payment-button ${!selectedPaymentMethod || isProcessing ? 'disabled' : ''}`}
            onClick={handlePayment}
            disabled={!selectedPaymentMethod || isProcessing}
          >
            {isProcessing ? '포인트 결제 처리 중...' : 
             selectedPaymentMethod ? 
             `${finalPrice.toLocaleString()}포인트로 결제하기` :
             `${finalPrice.toLocaleString()}포인트 결제하기`}
          </button>
        </div>

        {/* 안내사항 */}
        <div className="payment-notice">
          <h3>포인트 결제 안내사항</h3>
          <ul>
            <li>포인트 결제는 즉시 처리되며 수수료가 없습니다.</li>
            <li>결제 완료 후 즉시 서비스가 시작됩니다.</li>
            <li>주문 취소는 결제 후 1시간 이내에만 가능합니다.</li>
            <li>포인트가 부족한 경우 포인트 충전 후 다시 시도해주세요.</li>
            <li>서비스 이용 중 문제가 발생하면 고객센터로 문의해주세요.</li>
            <li>개인정보는 안전하게 보호되며, 결제 정보는 암호화되어 전송됩니다.</li>
          </ul>
        </div>
      </div>

      {/* 쿠폰 선택 모달 */}
      {showCouponModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>할인 쿠폰 선택</h2>
              <button 
                className="close-btn"
                onClick={() => setShowCouponModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              {availableCoupons.length === 0 ? (
                <p>사용 가능한 쿠폰이 없습니다.</p>
              ) : (
                <div className="coupon-list">
                  {availableCoupons.map((coupon) => (
                    <div 
                      key={coupon.id}
                      className={`coupon-item ${selectedCoupon?.id === coupon.id ? 'selected' : ''}`}
                      onClick={() => handleCouponSelect(coupon)}
                    >
                      <div className="coupon-info">
                        <h3>{coupon.name}</h3>
                        <p>{coupon.description}</p>
                        <div className="coupon-discount">
                          {coupon.type === 'percentage' 
                            ? `${coupon.discount}% 할인`
                            : `${coupon.discount.toLocaleString()}원 할인`
                          }
                        </div>
                      </div>
                      <div className="coupon-select">
                        {selectedCoupon?.id === coupon.id ? '✓' : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button 
                className="cancel-btn"
                onClick={() => setShowCouponModal(false)}
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PaymentPage
