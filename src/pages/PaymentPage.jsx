import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { ChevronLeft, CreditCard, Wallet, Shield, CheckCircle, Smartphone, Zap, Heart, Gift, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { getUserCoupons, useCoupon } from '../services/snspopApi'
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
  const [coupons, setCoupons] = useState([])
  const [selectedCoupon, setSelectedCoupon] = useState(null)
  const [couponsLoading, setCouponsLoading] = useState(false)
  const [couponsError, setCouponsError] = useState(null)
  const [showCouponModal, setShowCouponModal] = useState(false)

  // 주문 데이터가 없으면 홈으로 리다이렉트
  useEffect(() => {
    if (!orderData) {
      navigate('/')
      return
    }
  }, [orderData, navigate])

  // 사용 가능한 쿠폰 불러오기
  useEffect(() => {
    if (currentUser && orderData) {
      fetchUserCoupons()
    }
  }, [currentUser, orderData])

  const fetchUserCoupons = async () => {
    try {
      setCouponsLoading(true)
      setCouponsError(null)
      const userCoupons = await getUserCoupons(currentUser.email)
      // 사용 가능한 쿠폰만 필터링 (사용되지 않았고 만료되지 않은 쿠폰)
      const availableCoupons = userCoupons.filter(coupon => 
        !coupon.is_used && new Date(coupon.expires_at) > new Date()
      )
      setCoupons(availableCoupons)
    } catch (err) {
      setCouponsError('쿠폰 정보를 불러오는 중 오류가 발생했습니다.')
      console.error('Error fetching coupons:', err)
    } finally {
      setCouponsLoading(false)
    }
  }

  const handleCouponSelect = (coupon) => {
    setSelectedCoupon(coupon)
    setShowCouponModal(false)
  }

  const handleCouponRemove = () => {
    setSelectedCoupon(null)
  }

  const calculateDiscountedPrice = () => {
    if (!selectedCoupon) return orderData.totalPrice
    
    let discountAmount = 0
    if (selectedCoupon.discount_type === 'percentage') {
      discountAmount = Math.round(orderData.totalPrice * selectedCoupon.discount_value / 100)
    } else {
      discountAmount = Math.min(selectedCoupon.discount_value, orderData.totalPrice)
    }
    
    return Math.max(0, orderData.totalPrice - discountAmount)
  }

  const getDiscountAmount = () => {
    if (!selectedCoupon) return 0
    return orderData.totalPrice - calculateDiscountedPrice()
  }

  const paymentMethods = [
    {
      id: 'toss',
      name: '토스페이',
      icon: Zap,
      description: '간편하고 빠른 토스페이 결제',
      color: '#0064FF'
    },
    {
      id: 'kakao',
      name: '카카오페이',
      icon: Heart,
      description: '카카오페이로 간편 결제',
      color: '#FEE500'
    },
    {
      id: 'naver',
      name: '네이버페이',
      icon: Smartphone,
      description: '네이버페이로 안전한 결제',
      color: '#03C75A'
    },
    {
      id: 'card',
      name: '신용카드',
      icon: CreditCard,
      description: 'VISA, MasterCard, 국내 모든 카드사',
      color: '#6c757d'
    },
    {
      id: 'bank',
      name: '계좌이체',
      icon: Wallet,
      description: '실시간 계좌이체',
      color: '#6c757d'
    },
    {
      id: 'virtual',
      name: '가상계좌',
      icon: Shield,
      description: '안전한 가상계좌 결제',
      color: '#6c757d'
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

    try {
      // 쿠폰이 선택된 경우 쿠폰 사용 처리
      if (selectedCoupon) {
        try {
          await useCoupon(selectedCoupon.id, orderData.orderId || 'temp')
          console.log('쿠폰이 성공적으로 사용되었습니다.')
        } catch (couponError) {
          console.error('쿠폰 사용 중 오류:', couponError)
          // 쿠폰 사용 실패해도 결제는 계속 진행
        }
      }

      // 선택된 결제 방법에 따른 처리
      let paymentMessage = ''
      switch (selectedPaymentMethod) {
        case 'toss':
          paymentMessage = '토스페이 결제를 진행합니다...'
          break
        case 'kakao':
          paymentMessage = '카카오페이 결제를 진행합니다...'
          break
        case 'naver':
          paymentMessage = '네이버페이 결제를 진행합니다...'
          break
        case 'card':
          paymentMessage = '신용카드 결제를 진행합니다...'
          break
        case 'bank':
          paymentMessage = '계좌이체를 진행합니다...'
          break
        case 'virtual':
          paymentMessage = '가상계좌 결제를 진행합니다...'
          break
        default:
          paymentMessage = '결제를 진행합니다...'
      }

      // 실제 결제 처리 로직을 여기에 구현
      // 현재는 시뮬레이션
      setTimeout(() => {
        setIsProcessing(false)
        setPaymentSuccess(true)
        
        // 3초 후 주문 완료 페이지로 이동
        setTimeout(() => {
          navigate(`/order-complete/${orderData.orderId || 'temp'}`, { 
            state: { orderData: orderData } 
          })
        }, 3000)
      }, 2000)
    } catch (error) {
      console.error('결제 처리 중 오류:', error)
      setIsProcessing(false)
      alert('결제 처리 중 오류가 발생했습니다. 다시 시도해주세요.')
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
        <h1>결제하기</h1>
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
              <span>단가:</span>
              <span>{orderData.unitPrice}원</span>
            </div>
            <div className="price-row">
              <span>수량:</span>
              <span>{orderData.quantity.toLocaleString()}개</span>
            </div>
            {orderData.discount > 0 && (
              <div className="price-row discount">
                <span>할인 ({orderData.discount}%):</span>
                <span>-{Math.round(orderData.quantity * orderData.unitPrice * orderData.discount / 100).toLocaleString()}원</span>
              </div>
            )}
            {selectedCoupon && (
              <div className="price-row coupon-discount">
                <span>쿠폰 할인 ({selectedCoupon.discount_type === 'percentage' ? `${selectedCoupon.discount_value}%` : `${selectedCoupon.discount_value}원`}):</span>
                <span>-{getDiscountAmount().toLocaleString()}원</span>
              </div>
            )}
            <div className="price-row total">
              <span>총 결제금액:</span>
              <span>{calculateDiscountedPrice().toLocaleString()}원</span>
            </div>
          </div>
        </div>

        {/* 쿠폰 선택 */}
        <div className="coupon-section">
          <h2>쿠폰 사용</h2>
          <div className="coupon-content">
            {couponsLoading ? (
              <div className="coupon-loading">
                <div className="spinner"></div>
                <span>쿠폰 정보를 불러오는 중...</span>
              </div>
            ) : couponsError ? (
              <div className="coupon-error">
                <span>{couponsError}</span>
                <button onClick={fetchUserCoupons} className="retry-btn">다시 시도</button>
              </div>
            ) : selectedCoupon ? (
              <div className="selected-coupon">
                <div className="coupon-info">
                  <Gift size={20} />
                  <div className="coupon-details">
                    <span className="coupon-code">{selectedCoupon.code}</span>
                    <span className="coupon-discount">
                      {selectedCoupon.discount_type === 'percentage' ? `${selectedCoupon.discount_value}%` : `${selectedCoupon.discount_value}원`} 할인
                    </span>
                  </div>
                </div>
                <button onClick={handleCouponRemove} className="remove-coupon-btn">
                  <X size={16} />
                </button>
              </div>
            ) : coupons.length > 0 ? (
              <div className="coupon-actions">
                <button onClick={() => setShowCouponModal(true)} className="select-coupon-btn">
                  <Gift size={16} />
                  쿠폰 선택하기
                </button>
                <span className="coupon-count">사용 가능한 쿠폰 {coupons.length}개</span>
              </div>
            ) : (
              <div className="no-coupons">
                <span>사용 가능한 쿠폰이 없습니다</span>
              </div>
            )}
          </div>
        </div>

        {/* 결제 방법 선택 */}
        <div className="payment-methods">
          <h2>결제 방법 선택</h2>
          
          {/* 한국 간편결제 */}
          <div className="korean-payment-section">
            <h3>🇰🇷 간편결제 <span className="recommended-badge">추천</span></h3>
            <p className="korean-payment-info">한국에서 가장 인기 있는 간편결제 서비스입니다. 빠르고 안전한 결제를 경험해보세요.</p>
            <div className="methods-grid korean-methods">
              {paymentMethods.slice(0, 3).map((method) => (
                <div
                  key={method.id}
                  className={`payment-method korean-method ${selectedPaymentMethod === method.id ? 'selected' : ''}`}
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
                      <span className="feature">빠른 결제</span>
                      <span className="feature">안전 보장</span>
                      <span className="feature">즉시 처리</span>
                    </div>
                  </div>
                  <div className="method-check">
                    {selectedPaymentMethod === method.id && <CheckCircle />}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 일반 결제 */}
          <div className="general-payment-section">
            <h3>💳 일반 결제</h3>
            <div className="methods-grid">
              {paymentMethods.slice(3).map((method) => (
                <div
                  key={method.id}
                  className={`payment-method ${selectedPaymentMethod === method.id ? 'selected' : ''}`}
                  onClick={() => handlePaymentMethodSelect(method.id)}
                >
                  <div className="method-icon">
                    <method.icon />
                  </div>
                  <div className="method-info">
                    <h3>{method.name}</h3>
                    <p>{method.description}</p>
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
            {isProcessing ? '결제 처리 중...' : 
             selectedPaymentMethod ? 
             `${calculateDiscountedPrice().toLocaleString()}원 ${getPaymentMethodName(selectedPaymentMethod)}로 결제하기` :
             `${calculateDiscountedPrice().toLocaleString()}원 결제하기`}
          </button>
        </div>

        {/* 안내사항 */}
        <div className="payment-notice">
          <h3>결제 안내사항</h3>
          <ul>
            <li>결제 완료 후 즉시 서비스가 시작됩니다.</li>
            <li>주문 취소는 결제 후 1시간 이내에만 가능합니다.</li>
            <li>서비스 이용 중 문제가 발생하면 고객센터로 문의해주세요.</li>
            <li>개인정보는 안전하게 보호되며, 결제 정보는 암호화되어 전송됩니다.</li>
            <li><strong>간편결제:</strong> 토스페이, 카카오페이, 네이버페이는 즉시 처리되며 수수료가 없습니다.</li>
            <li><strong>신용카드:</strong> 결제 후 1-2일 내에 카드사에서 승인됩니다.</li>
            <li><strong>계좌이체:</strong> 실시간으로 처리되며 은행 수수료가 발생할 수 있습니다.</li>
          </ul>
        </div>
      </div>

      {/* 쿠폰 선택 모달 */}
      {showCouponModal && (
        <div className="coupon-modal-overlay" onClick={() => setShowCouponModal(false)}>
          <div className="coupon-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>쿠폰 선택</h3>
              <button onClick={() => setShowCouponModal(false)} className="close-btn">
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              {coupons.length === 0 ? (
                <div className="no-coupons-modal">
                  <Gift size={48} />
                  <h4>사용 가능한 쿠폰이 없습니다</h4>
                  <p>추천인 코드를 사용하여 쿠폰을 받아보세요!</p>
                </div>
              ) : (
                <div className="coupons-list">
                  {coupons.map((coupon) => (
                    <div
                      key={coupon.id}
                      className="coupon-item"
                      onClick={() => handleCouponSelect(coupon)}
                    >
                      <div className="coupon-item-header">
                        <span className="coupon-code">{coupon.code}</span>
                        <span className="coupon-expiry">
                          {new Date(coupon.expires_at).toLocaleDateString('ko-KR')}까지
                        </span>
                      </div>
                      <div className="coupon-item-body">
                        <span className="discount-value">
                          {coupon.discount_type === 'percentage' ? `${coupon.discount_value}%` : `${coupon.discount_value}원`}
                        </span>
                        <span className="discount-label">할인</span>
                      </div>
                      <div className="coupon-item-footer">
                        <span className="estimated-savings">
                          예상 절약: {coupon.discount_type === 'percentage' ? 
                            `${Math.round(orderData.totalPrice * coupon.discount_value / 100).toLocaleString()}원` : 
                            `${Math.min(coupon.discount_value, orderData.totalPrice).toLocaleString()}원`}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PaymentPage
