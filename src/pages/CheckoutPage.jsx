import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, CheckCircle, Coins } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { getOrderForCheckout, clearOrderCheckout } from '../utils/orderManager'
import './PaymentPage.css'

const CheckoutPage = () => {
  const navigate = useNavigate()
  const { currentUser } = useAuth()
  const [orderData, setOrderData] = useState(null)
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('points')
  const [isProcessing, setIsProcessing] = useState(false)
  const [paymentSuccess, setPaymentSuccess] = useState(false)
  const [availableCoupons, setAvailableCoupons] = useState([])
  const [selectedCoupon, setSelectedCoupon] = useState(null)
  const [showCouponModal, setShowCouponModal] = useState(false)
  const [finalPrice, setFinalPrice] = useState(0)
  const [couponCode, setCouponCode] = useState('')
  const [addingCoupon, setAddingCoupon] = useState(false)

  useEffect(() => {
    const savedOrder = getOrderForCheckout()
    if (!savedOrder) {
      navigate('/')
      return
    }
    setOrderData(savedOrder)
    setFinalPrice(savedOrder.pricing.total)
  }, [navigate])

  // 사용자의 쿠폰 데이터 로드
  useEffect(() => {
    const loadUserCoupons = async () => {
      if (!currentUser?.uid) {
        setAvailableCoupons([])
        return
      }
      
      try {
        const response = await fetch(`/api/user/coupons?user_id=${currentUser.uid}`)
        if (response.ok) {
          const data = await response.json()
          const usableCoupons = (data.coupons || []).filter(coupon => {
            const isNotUsed = !coupon.is_used
            const isNotExpired = !coupon.expires_at || new Date(coupon.expires_at) > new Date()
            return isNotUsed && isNotExpired
          }).map(coupon => ({
            id: coupon.id,
            name: coupon.coupon_name || coupon.referral_code || '할인 쿠폰',
            discount: coupon.discount_value || 0,
            type: coupon.discount_type === 'percentage' ? 'percentage' : 'fixed',
            coupon_code: coupon.coupon_code || coupon.referral_code
          }))
          setAvailableCoupons(usableCoupons)
        }
      } catch (error) {
        console.error('쿠폰 로드 실패:', error)
      }
    }
    loadUserCoupons()
  }, [currentUser])

  // 최종 가격 계산
  useEffect(() => {
    if (orderData) {
      let price = orderData.pricing.total
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

  const handleCouponSelect = (coupon) => {
    setSelectedCoupon(coupon)
    setShowCouponModal(false)
  }

  const handleCouponRemove = () => {
    setSelectedCoupon(null)
  }

  const handleAddCouponByCode = async () => {
    if (!couponCode.trim()) {
      alert('쿠폰 번호를 입력해주세요.')
      return
    }

    setAddingCoupon(true)
    try {
      const response = await fetch('/api/user/coupons/add-by-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: currentUser.uid,
          coupon_code: couponCode.trim()
        })
      })

      const data = await response.json()
      if (response.ok && data.success) {
        const newCoupon = {
          id: data.coupon.id,
          name: data.coupon.coupon_name || data.coupon.coupon_code || '할인 쿠폰',
          discount: data.coupon.discount_value || 0,
          type: data.coupon.discount_type === 'percentage' ? 'percentage' : 'fixed',
          coupon_code: data.coupon.coupon_code
        }
        setAvailableCoupons([...availableCoupons, newCoupon])
        setCouponCode('')
        alert('쿠폰이 추가되었습니다!')
      } else {
        alert(data.error || '쿠폰 추가에 실패했습니다.')
      }
    } catch (error) {
      alert('쿠폰 추가 중 오류가 발생했습니다.')
    } finally {
      setAddingCoupon(false)
    }
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

  const handlePayment = async () => {
    if (!selectedPaymentMethod) {
      alert('결제 방법을 선택해주세요.')
      return
    }

    console.log(orderData)

    setIsProcessing(true)

    try {
      // 1. 포인트 차감
      const deductResponse = await fetch('/api/points/deduct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: currentUser.uid,
          amount: finalPrice
        })
      })

      if (!deductResponse.ok) {
        const errorData = await deductResponse.json()
        throw new Error(errorData.error || '포인트 차감 실패')
      }

      // 2. 주문 생성
      const orderPayload = {
        user_id: currentUser.uid,
        platform: orderData.category.slug,
        service: orderData.product?.name || orderData.package?.name,
        detailed_service: orderData.variant?.name || orderData.package?.name,
        service_id: orderData.variant?.id || orderData.package?.id,
        link: orderData.orderDetails.link,
        quantity: orderData.orderDetails.quantity || 1,
        comments: orderData.orderDetails.comments || '',
        total_price: finalPrice,
        discount: selectedCoupon ? (selectedCoupon.type === 'percentage' ? selectedCoupon.discount : (orderData.pricing.total - finalPrice)) : 0,
        package_steps: orderData.type === 'package' && orderData.package ? (orderData.package.items || orderData.package.steps || []).map(item => ({
          step: item.step,
          variant_id: item.variant_id,
          variant_name: item.variant_name,
          quantity: item.quantity || 0,
          repeat_count: item.repeat_count || 1,
          term_value: item.term_value || 0,
          term_unit: item.term_unit || 'minute'
        })) : [],
        use_coupon: selectedCoupon ? true : false,
        coupon_id: selectedCoupon?.id || null,
        coupon_discount: selectedCoupon ? (selectedCoupon.type === 'percentage' ? selectedCoupon.discount : (orderData.pricing.total - finalPrice)) : 0
      }

      console.log("orderPayload",orderPayload)

      const orderResponse = await fetch('/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': currentUser.uid
        },
        body: JSON.stringify(orderPayload)
      })

      if (!orderResponse.ok) {
        const orderError = await orderResponse.json()
        
        // 주문 생성 실패 시 포인트 환불
        if (orderError.refund_required && orderError.refund_amount) {
          try {
            await fetch('/api/points/refund', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                user_id: currentUser.uid,
                amount: orderError.refund_amount,
                order_id: orderError.order_id
              })
            })
          } catch (refundError) {
            console.error('포인트 환불 실패:', refundError)
          }
        }
        
        throw new Error(orderError.error || '주문 생성 실패')
      }

      const orderResult = await orderResponse.json()

      // 3. 패키지 주문인 경우 처리 시작
      const packageItems = orderData.package?.items || orderData.package?.steps || []
      if (orderData.type === 'package' && orderData.package && packageItems.length > 0) {
        try {
          await fetch('/api/orders/start-package-processing', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-User-ID': currentUser.uid
            },
            body: JSON.stringify({ order_id: orderResult.order_id })
          })
        } catch (error) {
          console.error('패키지 처리 시작 실패:', error)
        }
      }

      // 4. 결제 성공
      setIsProcessing(false)
      setPaymentSuccess(true)
      clearOrderCheckout()

      setTimeout(() => {
        navigate('/order-complete', {
          state: {
            orderId: orderResult.order_id,
            orderData: orderData,
            paymentMethod: '포인트 결제'
          }
        })
      }, 2000)

    } catch (error) {
      alert(`결제 실패: ${error.message}`)
      
      setIsProcessing(false)
    }
  }

  if (!orderData) return null

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
        <button className="back-button" onClick={() => navigate(-1)}>
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
              <span>카테고리:</span>
              <span className="platform-name">{orderData.category.name}</span>
            </div>
            <div className="summary-row">
              <span>서비스:</span>
              <span>{orderData.type === 'package' ? orderData.package?.name : orderData.product?.name}</span>
            </div>
            {orderData.type === 'product' && (
              <>
                <div className="summary-row">
                  <span>상세:</span>
                  <span>{orderData.variant.name}</span>
                </div>
                <div className="summary-row">
                  <span>수량:</span>
                  <span>{orderData.orderDetails.quantity.toLocaleString()}개</span>
                </div>
              </>
            )}
            <div className="summary-row">
              <span>링크:</span>
              <span className="order-link">{orderData.orderDetails.link}</span>
            </div>
            {orderData.orderDetails.comments && (
              <div className="summary-row">
                <span>댓글:</span>
                <span className="order-comments">{orderData.orderDetails.comments}</span>
              </div>
            )}
          </div>
        </div>

        {/* 패키지 구성 */}
        {orderData.type === 'package' && orderData.package && (
          <div className="order-summary">
            <h2>📦 패키지 구성</h2>
            <div className="summary-content">
              {(orderData.package.items || orderData.package.steps || []).map((item, index) => (
                <div key={index} className="summary-row">
                  <span>Step {item.step || index + 1}:</span>
                  <span>{item.variant_name || item.name}:</span>
                  <span>
                    수량: {item.quantity?.toLocaleString()}개
                    {item.repeat_count > 1 && ` × ${item.repeat_count}회`}
                    {item.term_value > 0 && ` (간격: ${item.term_value}${item.term_unit === 'minute' ? '분' : '시간'})`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 가격 정보 */}
        <div className="price-summary">
          <h2>가격 정보</h2>
          <div className="price-content">
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
                <span>할인 ({selectedCoupon.type === 'percentage' ? `${selectedCoupon.discount}%` : `${selectedCoupon.discount.toLocaleString()}원`}):</span>
                <span>-{(orderData.pricing.total - finalPrice).toLocaleString()}원</span>
              </div>
            )}
            <div className="price-row total">
              <span>총 결제금액:</span>
              <span>{finalPrice.toLocaleString()}원</span>
            </div>
          </div>
        </div>

        {/* 포인트 결제 */}
        <div className="payment-methods">
          <h2>포인트 결제</h2>
          <div className="points-payment-section">
            <h3>💰 포인트 결제 <span className="recommended-badge">추천</span></h3>
            <p className="points-payment-info">보유 포인트로 간편하고 안전하게 결제하세요.</p>
            <div className="methods-grid points-methods">
              {paymentMethods.map((method) => (
                <div
                  key={method.id}
                  className={`payment-method points-method ${selectedPaymentMethod === method.id ? 'selected' : ''}`}
                  onClick={() => setSelectedPaymentMethod(method.id)}
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
            {isProcessing ? '포인트 결제 처리 중...' : `${finalPrice.toLocaleString()}포인트로 결제하기`}
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
              {/* 쿠폰 번호 입력 */}
              <div className="coupon-code-input-section" style={{ marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid #eee' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '16px' }}>쿠폰 번호 입력</h3>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    type="text"
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value)}
                    placeholder="쿠폰 번호를 입력하세요"
                    style={{
                      flex: 1,
                      padding: '10px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '14px'
                    }}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddCouponByCode()}
                  />
                  <button
                    onClick={handleAddCouponByCode}
                    disabled={addingCoupon || !couponCode.trim()}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: addingCoupon ? '#ccc' : '#6366f1',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: addingCoupon || !couponCode.trim() ? 'not-allowed' : 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    {addingCoupon ? '추가 중...' : '추가'}
                  </button>
                </div>
              </div>

              {/* 쿠폰 목록 */}
              <h3 style={{ marginBottom: '15px', fontSize: '16px' }}>보유한 쿠폰</h3>
              {availableCoupons.length === 0 ? (
                <p style={{ color: '#666', textAlign: 'center', padding: '20px' }}>사용 가능한 쿠폰이 없습니다.</p>
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
                        {coupon.coupon_code && (
                          <p style={{ fontSize: '12px', color: '#666' }}>쿠폰 번호: {coupon.coupon_code}</p>
                        )}
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

export default CheckoutPage

