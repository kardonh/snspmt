import React from 'react'

function VariantList({ variants, selectedVariant, onSelectVariant }) {
  console.log(variants)
  const formatPrice = (price) => {
    const priceValue = parseFloat(price)
    return priceValue % 1 === 0 ? priceValue.toString() : priceValue.toFixed(2)
  }

  return (
    <div className="detailed-service-selection">
      <h3>세부 서비스를 선택해주세요</h3>
      <div className="detailed-service-list">
        {variants.map((variant, index) => (
          <div
            key={index}
            className={`detailed-service-item ${selectedVariant?.id === variant.id ? 'selected' : ''}`}
            onClick={() => onSelectVariant(variant)}
          >
            <div className="detailed-service-content">
              <div className="detailed-service-info">
                <div className="detailed-service-name">{variant.name}</div>
                <div className="detailed-service-range">
                  최소: {(variant.min_quantity || 0).toLocaleString()} ~ 최대: {(variant.max_quantity || 0).toLocaleString()}
                </div>
              </div>
              <div className="detailed-service-price">
                ₩{formatPrice(variant.price)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default VariantList

