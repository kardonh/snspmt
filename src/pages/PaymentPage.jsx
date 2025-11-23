import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { ChevronLeft, CheckCircle, Coins, Star } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './PaymentPage.css'

const PaymentPage = () => {
  const { platform } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const orderData = location.state?.orderData
  const { currentUser } = useAuth()

  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [paymentSuccess, setPaymentSuccess] = useState(false)
  const [availableCoupons, setAvailableCoupons] = useState([])
  const [selectedCoupon, setSelectedCoupon] = useState(null)
  const [showCouponModal, setShowCouponModal] = useState(false)
  const [finalPrice, setFinalPrice] = useState(orderData?.totalPrice || 0)
  const [couponCode, setCouponCode] = useState('')
  const [addingCoupon, setAddingCoupon] = useState(false)

  // 주문 데이터가 없으면 홈으로 리다이렉트
  useEffect(() => {
    if (!orderData) {
      navigate('/')
      return
    }
  }, [orderData, navigate])

  // 사용자의 쿠폰 데이터 로드 (사용하지 않은 쿠폰만)
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
          // 사용하지 않은 쿠폰만 필터링
          const usableCoupons = (data.coupons || []).filter(coupon => {
            // is_used가 false이고, 만료되지 않은 쿠폰만
            const isNotUsed = !coupon.is_used
            const isNotExpired = !coupon.expires_at || new Date(coupon.expires_at) > new Date()
            return isNotUsed && isNotExpired
          }).map(coupon => ({
            id: coupon.id,
            name: coupon.coupon_name || coupon.referral_code || '할인 쿠폰',
            description: '',
            discount: coupon.discount_value || 0,
            type: coupon.discount_type === 'percentage' ? 'percentage' : 'fixed',
            coupon_code: coupon.coupon_code || coupon.referral_code
          }))
          setAvailableCoupons(usableCoupons)
        }
      } catch (error) {
        console.error('쿠폰 로드 실패:', error)
        setAvailableCoupons([])
      }
    }
    loadUserCoupons()
  }, [currentUser])

  // 최종 가격 계산
  useEffect(() => {
    if (orderData) {
      let price = orderData.totalPrice || 0
      if (selectedCoupon) {
        if (selectedCoupon.type === 'percentage' || selectedCoupon.discount_type === 'percentage') {
          price = price * (1 - (selectedCoupon.discount || 0) / 100)
        } else {
          price = Math.max(0, price - (selectedCoupon.discount || 0))
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

  // 쿠폰 번호로 쿠폰 추가
  const handleAddCouponByCode = async () => {
    if (!couponCode.trim()) {
      alert('쿠폰 번호를 입력해주세요.')
      return
    }

    if (!currentUser?.uid) {
      alert('로그인이 필요합니다.')
      return
    }

    setAddingCoupon(true)
    try {
      const response = await fetch('/api/user/coupons/add-by-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: currentUser.uid,
          coupon_code: couponCode.trim()
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        // 새로 추가된 쿠폰을 목록에 추가
        const newCoupon = {
          id: data.coupon.id,
          name: data.coupon.coupon_name || data.coupon.coupon_code || '할인 쿠폰',
          description: '',
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
      console.error('쿠폰 추가 실패:', error)
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

      // 2. SMM Panel API 호출 - 백엔드에서 처리하므로 프론트엔드에서는 호출하지 않음
      if (orderData.isScheduledOrder) {
        console.log('📅 예약 발송 주문 - 백엔드에서 처리 예정')
      } else if (orderData.detailedService?.package && orderData.detailedService?.steps && orderData.detailedService.steps.length > 0) {
        console.log('📦 패키지 상품 - 백엔드에서 순차 처리 예정')
      } else {
        console.log('🚀 일반 주문 - 백엔드에서 즉시 처리 예정')
      }

      // 3. 주문 생성 (결제 완료 후)
      // 예약 발송인 경우 별도 API 호출
      if (orderData.isScheduledOrder) {
        console.log('📅 예약 발송 주문 - 예약 주문 API 호출')
        console.log('📅 예약 시간:', `${orderData.scheduledDate} ${orderData.scheduledTime}`)
        
        // Drip-feed 상품인 경우 체크
        const isDripFeedScheduled = orderData.detailedService?.drip_feed === true
        
        const scheduledOrderResponse = await fetch('/api/scheduled-orders', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-User-ID': orderData.userId || orderData.user_id
          },
          body: JSON.stringify({
            user_id: orderData.userId || orderData.user_id,
            service_id: isDripFeedScheduled ? (orderData.detailedService?.smmkings_id || orderData.detailedService?.id) : (orderData.detailedService?.id || orderData.detailedService?.smmkings_id),
            link: orderData.link,
            quantity: isDripFeedScheduled ? (orderData.detailedService?.drip_quantity || orderData.quantity) : orderData.quantity,
            total_price: finalPrice,
            scheduled_datetime: `${orderData.scheduledDate} ${orderData.scheduledTime}`,
            runs: isDripFeedScheduled ? (orderData.detailedService?.runs || 1) : 1,
            interval: isDripFeedScheduled ? (orderData.detailedService?.interval || 0) : 0,
            package_steps: !isDripFeedScheduled && orderData.detailedService?.package && orderData.detailedService?.steps ? orderData.detailedService.steps.map(step => ({
              ...step,
              quantity: step.quantity || 0
            })) : []
          })
        })
        
        if (!scheduledOrderResponse.ok) {
          const scheduledError = await scheduledOrderResponse.json()
          throw new Error(scheduledError.error || '예약 발송 주문 생성 실패')
        }
        
        const scheduledResult = await scheduledOrderResponse.json()
        alert(scheduledResult.message)
        navigate('/orders')
        return
      }

      // Drip-feed 상품인 경우 runs와 interval 설정
      const isDripFeed = orderData.detailedService?.drip_feed === true
      const dripFeedRuns = isDripFeed ? (orderData.detailedService?.runs || 1) : 1
      const dripFeedInterval = isDripFeed ? (orderData.detailedService?.interval || 0) : 0
      const dripFeedQuantity = isDripFeed ? (orderData.detailedService?.drip_quantity || orderData.quantity) : orderData.quantity
      const dripFeedServiceId = isDripFeed ? (orderData.detailedService?.smmkings_id || orderData.detailedService?.id) : (orderData.detailedService?.id || orderData.detailedService?.smmkings_id)

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
          service_id: dripFeedServiceId || orderData.detailedService?.id || orderData.detailedService?.smmkings_id,
          link: orderData.link,
          quantity: dripFeedQuantity,
          runs: dripFeedRuns,  // Drip-feed 상품: 30일간 하루에 1번씩 → runs: 30, interval: 1440
          interval: dripFeedInterval,  // interval 단위: 분 (1440 = 24시간)
          comments: orderData.comments || '',
          explanation: orderData.explanation || '',
          total_price: finalPrice,
          discount: selectedCoupon ? (selectedCoupon.type === 'percentage' ? selectedCoupon.discount : (orderData.totalPrice - finalPrice)) : (orderData.discount || 0),
          is_scheduled: orderData.isScheduledOrder || false,
          scheduled_datetime: orderData.isScheduledOrder ? `${orderData.scheduledDate} ${orderData.scheduledTime}` : null,
          is_split_delivery: orderData.isSplitDelivery || false,
          split_days: orderData.splitDays || null,
          split_quantity: orderData.dailyQuantity || null,
          package_steps: !isDripFeed && orderData.detailedService?.package && orderData.detailedService?.steps ? orderData.detailedService.steps.map(step => ({
            ...step,
            quantity: step.quantity || 0  // 각 단계별 수량 보장
          })) : [],
          use_coupon: selectedCoupon ? true : (orderData.discount > 0),
          coupon_id: selectedCoupon?.id || (orderData.discount > 0 ? 'manual_discount' : null),
          coupon_discount: selectedCoupon ? (selectedCoupon.type === 'percentage' ? selectedCoupon.discount : (orderData.totalPrice - finalPrice)) : (orderData.discount || 0)
        })
      })

      if (!orderResponse.ok) {
        const orderError = await orderResponse.json()
        
        // 주문 생성 실패 시 포인트 환불
        if (orderError.refund_required && orderError.refund_amount) {
          console.log('💰 주문 실패로 인한 포인트 환불 시작')
          try {
            const refundResponse = await fetch('/api/points/refund', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                user_id: orderData.userId || orderData.user_id,
                amount: orderError.refund_amount,
                order_id: orderError.order_id
              })
            })
            
            if (refundResponse.ok) {
              const refundResult = await refundResponse.json()
              console.log('✅ 포인트 환불 완료:', refundResult)
            } else {
              console.error('❌ 포인트 환불 실패:', await refundResponse.json())
            }
          } catch (refundError) {
            console.error('❌ 포인트 환불 중 오류:', refundError)
          }
        }
        
        throw new Error(orderError.error || '주문 생성 실패')
      }

      const orderResult = await orderResponse.json()

      // 4. 패키지 주문인 경우 결제 완료 후 처리 시작
      if (orderData.detailedService?.package && orderData.detailedService?.steps && orderData.detailedService.steps.length > 0) {
        console.log('📦 패키지 주문 - 결제 완료 후 처리 시작')
        
        try {
          const startPackageResponse = await fetch('/api/orders/start-package-processing', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-User-ID': orderData.userId || orderData.user_id
            },
            body: JSON.stringify({
              order_id: orderResult.order_id
            })
          })

          if (!startPackageResponse.ok) {
            const errorData = await startPackageResponse.json()
            // 패키지 주문 시작 실패 (주문은 정상 생성됨)
          } else {
            const responseData = await startPackageResponse.json()
            if (responseData.success) {
              // 패키지 주문 처리 상태 확인 완료
            }
          }
        } catch (error) {
          // 패키지 주문 시작 중 오류 (주문은 정상 생성됨)
        }
      }

      // 5. 결제 성공 처리
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
                <span>할인 ({(selectedCoupon.type === 'percentage' || selectedCoupon.discount_type === 'percentage') 
                  ? (selectedCoupon.discount || 0) + '%' 
                  : (selectedCoupon.discount || 0).toLocaleString() + '원'}):</span>
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
              {/* 쿠폰 번호 입력 섹션 */}
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
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleAddCouponByCode()
                      }
                    }}
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

export default PaymentPage
