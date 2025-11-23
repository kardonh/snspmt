import React from 'react'
import { Package, Clock } from 'lucide-react'

function PackageDetailView({ packageDetail, onClose }) {
  const formatPrice = (price) => {
    const priceValue = parseFloat(price) / 1000
    return priceValue % 1 === 0 ? priceValue.toString() : priceValue.toFixed(2)
  }

  const calculateStepPrice = (item) => {
    return parseFloat(item.variant_price) * item.quantity * item.repeat_count
  }

  const totalPrice = packageDetail.items?.reduce((sum, item) => sum + calculateStepPrice(item), 0) || 0

  return (
    <div className="detailed-service-selection">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3>패키지 상세 정보</h3>
        <button onClick={onClose} style={{ padding: '8px 16px', cursor: 'pointer' }}>닫기</button>
      </div>

      <div style={{ marginBottom: '24px', padding: '16px', background: '#f8f9fa', borderRadius: '8px' }}>
        <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '8px' }}>{packageDetail.name}</div>
        {packageDetail.description && <div style={{ color: '#666', marginBottom: '12px' }}>{packageDetail.description}</div>}
        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#667eea' }}>
          총 가격: ₩{formatPrice(totalPrice.toString())}
        </div>
      </div>

      <div className="detailed-service-list">
        {packageDetail.steps?.map((step, index) => (
          <div key={step.package_item_id} className="detailed-service-item">
            <div className="detailed-service-content">
              <div className="detailed-service-info">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ background: '#667eea', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px' }}>
                    Step {step.step}
                  </span>
                  <div className="detailed-service-name">{step.variant_name}</div>
                </div>
                <div className="detailed-service-range">
                  수량: {step.quantity.toLocaleString()} | 반복: {step.repeat_count}회
                  {step.term_value > 0 && ` | 간격: ${step.term_value}${step.term_unit === 'minute' ? '분' : '시간'}`}
                </div>
              </div>
              <div className="detailed-service-price">
                ₩{formatPrice(calculateStepPrice(step).toString())}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default PackageDetailView

