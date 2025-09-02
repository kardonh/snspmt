import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { ChevronLeft, CreditCard, Wallet, Shield, CheckCircle, Smartphone, Zap, Heart } from 'lucide-react'
import './PaymentPage.css'

const PaymentPage = () => {
  const { platform } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const orderData = location.state?.orderData

  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [paymentSuccess, setPaymentSuccess] = useState(false)

  // 주문 데이터가 없으면 홈으로 리다이렉트
  useEffect(() => {
    if (!orderData) {
      navigate('/')
      return
    }
  }, [orderData, navigate])

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

    // 1단계: 결제 처리 (시뮬레이션)
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

    // 2초 후 실제 처리 시작
    setTimeout(async () => {
      try {
        // 2단계: 주문 결제 완료 및 외부 API 전송
        console.log('결제 완료, 주문 결제 완료 API 호출 시작...')
        
        // 주문 결제 완료 API 호출 (포인트 차감 + 외부 API 전송)
        const completePaymentResponse = await fetch(`/api/orders/${orderData.orderId}/complete-payment`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-User-ID': orderData.userId || 'anonymous'
          },
          body: JSON.stringify({
            // 추가 주문 옵션들 (필요한 경우)
            comments: orderData.comments || '',
            explanation: orderData.explanation || ''
          })
        })
        
        if (!completePaymentResponse.ok) {
          const errorData = await completePaymentResponse.json()
          throw new Error(errorData.error || '주문 결제 완료 실패')
        }
        
        const completeResult = await completePaymentResponse.json()
        console.log('주문 결제 완료 성공:', completeResult)
        
        // 주문 성공 시 처리
        setIsProcessing(false)
        setPaymentSuccess(true)
        
        // 3초 후 주문 완료 페이지로 이동
        setTimeout(() => {
          navigate(`/order-complete/${orderData.orderId || 'temp'}`, { 
            state: { 
              orderData: orderData,
              externalOrderId: completeResult.externalOrderId,
              pointsUsed: completeResult.points_used,
              remainingPoints: completeResult.remaining_points
            } 
          })
        }, 3000)
        
      } catch (error) {
        console.error('주문 결제 완료 실패:', error)
        alert(`주문 처리 중 오류가 발생했습니다: ${error.message}`)
        setIsProcessing(false)
      }
    }, 2000)
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
            <div className="price-row total">
              <span>총 결제금액:</span>
              <span>{orderData.totalPrice.toLocaleString()}원</span>
            </div>
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
             `${orderData.totalPrice.toLocaleString()}원 ${getPaymentMethodName(selectedPaymentMethod)}로 결제하기` :
             `${orderData.totalPrice.toLocaleString()}원 결제하기`}
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
    </div>
  )
}

export default PaymentPage
