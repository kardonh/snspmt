import React from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { CheckCircle, Home, FileText, Clock, Users, TrendingUp, Package } from 'lucide-react'
import './OrderCompletePage.css'

const OrderCompletePage = () => {
  const { orderId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const orderData = location.state?.orderData

  const handleGoHome = () => {
    navigate('/')
  }

  const handleViewOrders = () => {
    navigate('/orders')
  }

  return (
    <div className="order-complete-page">
      <div className="complete-container">
        {/* 성공 메시지 */}
        <div className="success-section">
          <CheckCircle className="success-icon" />
          <h1>주문이 완료되었습니다!</h1>
          <p className="order-id">주문번호: {orderId || location.state?.orderId}</p>
          <p className="success-message">
            결제가 성공적으로 완료되었습니다. 서비스가 곧 시작됩니다.
          </p>
        </div>

        {/* 주문 정보 요약 */}
        {orderData && (
          <div className="order-summary">
            <h2>주문 정보</h2>
            <div className="summary-grid">
              <div className="summary-item">
                <div className="item-icon">
                  <Users />
                </div>
                <div className="item-content">
                  <h3>카테고리</h3>
                  <p>{orderData.category?.name || '알 수 없음'}</p>
                </div>
              </div>
              
              <div className="summary-item">
                <div className="item-icon">
                  {orderData.type === 'package' ? <Package /> : <TrendingUp />}
                </div>
                <div className="item-content">
                  <h3>{orderData.type === 'package' ? '패키지' : '서비스'}</h3>
                  <p>{orderData.type === 'package' ? orderData.package?.name : orderData.product?.name}</p>
                </div>
              </div>

              {orderData.type === 'product' && (
                <div className="summary-item">
                  <div className="item-icon">
                    <FileText />
                  </div>
                  <div className="item-content">
                    <h3>상세 서비스</h3>
                    <p>{orderData.variant?.name}</p>
                  </div>
                </div>
              )}

              {orderData.type === 'product' && (
                <div className="summary-item">
                  <div className="item-icon">
                    <TrendingUp />
                  </div>
                  <div className="item-content">
                    <h3>수량</h3>
                    <p>{orderData.orderDetails?.quantity?.toLocaleString()}개</p>
                  </div>
                </div>
              )}

              <div className="summary-item">
                <div className="item-icon">
                  <Clock />
                </div>
                <div className="item-content">
                  <h3>처리 시간</h3>
                  <p>24-48시간 내</p>
                </div>
              </div>
            </div>

            {/* 추가 정보 */}
            <div className="additional-info">
              <div className="info-row">
                <span className="info-label">링크:</span>
                <span className="info-value">{orderData.orderDetails?.link}</span>
              </div>
              {orderData.orderDetails?.comments && (
                <div className="info-row">
                  <span className="info-label">댓글:</span>
                  <span className="info-value">{orderData.orderDetails.comments}</span>
                </div>
              )}
              <div className="info-row">
                <span className="info-label">결제 금액:</span>
                <span className="info-value total-price">{orderData.pricing?.formatted || `₩${orderData.pricing?.total?.toLocaleString()}`}</span>
              </div>
            </div>

            {/* 패키지 구성 표시 */}
            {orderData.type === 'package' && orderData.package?.steps?.length > 0 && (
              <div className="package-steps-info">
                <h3>📦 패키지 구성</h3>
                <ul>
                  {orderData.package.steps.map((step, index) => (
                    <li key={index}>
                      Step {step.step}: {step.variant_name} (x{step.quantity})
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* 다음 단계 안내 */}
        <div className="next-steps">
          <h2>다음 단계</h2>
          <div className="steps-list">
            <div className="step-item">
              <div className="step-number">1</div>
              <div className="step-content">
                <h3>주문 확인</h3>
                <p>주문이 성공적으로 접수되었습니다.</p>
              </div>
            </div>
            <div className="step-item">
              <div className="step-number">2</div>
              <div className="step-content">
                <h3>서비스 시작</h3>
                <p>24-48시간 내에 서비스가 시작됩니다.</p>
              </div>
            </div>
            <div className="step-item">
              <div className="step-number">3</div>
              <div className="step-content">
                <h3>진행 상황 확인</h3>
                <p>이메일로 진행 상황을 안내드립니다.</p>
              </div>
            </div>
            <div className="step-item">
              <div className="step-number">4</div>
              <div className="step-content">
                <h3>서비스 완료</h3>
                <p>요청하신 수량만큼 서비스가 완료됩니다.</p>
              </div>
            </div>
          </div>
        </div>

        {/* 중요 안내사항 */}
        <div className="important-notice">
          <h2>중요 안내사항</h2>
          <ul>
            <li>주문 확인 이메일을 확인해주세요.</li>
            <li>서비스 진행 중 문의사항이 있으시면 고객센터로 연락해주세요.</li>
            <li>서비스 완료까지 24-48시간이 소요될 수 있습니다.</li>
            <li>주문 취소는 결제 후 1시간 이내에만 가능합니다.</li>
          </ul>
        </div>

        {/* 액션 버튼 */}
        <div className="action-buttons">
          <button className="btn-primary" onClick={handleGoHome}>
            <Home />
            홈으로 돌아가기
          </button>
          <button className="btn-secondary" onClick={handleViewOrders}>
            <FileText />
            주문 내역 보기
          </button>
        </div>

        {/* 고객센터 정보 */}
        <div className="customer-service">
          <h3>고객센터</h3>
          <p>문의사항이 있으시면 하단의 카카오채널로 문의 부탁드립니다!</p>
          <div className="contact-info">
            <p>⏰ 운영시간: 평일 운영시간: 10:00 ~ 18:00</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OrderCompletePage
