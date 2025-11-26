import React, { useState } from 'react'

function OrderForm({ variant, packageDetail, category, onSubmit }) {
  const [quantity, setQuantity] = useState(0)
  const [link, setLink] = useState('')
  const [comments, setComments] = useState('')

  const isPackage = !!packageDetail
  const minQuantity = isPackage ? 1 : (variant?.min_quantity || 0)
  const maxQuantity = isPackage ? 1 : (variant?.max_quantity || 0)

  console.log(variant)

  const calculatePrice = () => {
    if (isPackage) {
      // 패키지는 variant_price가 이미 원 단위로 저장되어 있음
      // const calculateStepPrice = (item) => {
      //   return parseFloat(item.variant_price) * item.quantity * item.repeat_count
      // }
      // return packageDetail.items?.reduce((sum, item) => 
      //   sum + calculateStepPrice(item), 0) || 0
    }
    // 일반 variant는 price가 1000원 단위로 저장되어 있음
    return (parseFloat(variant?.price || 0) * quantity)
  }

  const totalPrice = calculatePrice()
  const formattedPrice = totalPrice % 1 === 0 ? totalPrice.toString() : totalPrice.toFixed(2)

  const isQuantityValid = isPackage || (quantity >= minQuantity && quantity <= maxQuantity)
  const isFormValid = link && (isPackage || isQuantityValid)

  const handleSubmit = () => {
    if (!isFormValid) return
    onSubmit({ quantity: isPackage ? 1 : quantity, link, comments, price: totalPrice })
  }

  return (
    <div className="order-form">
      <div className="order-info-header">
        <h3>주문 정보 입력</h3>


      </div>

      {/* Quantity Selection - 패키지가 아닐 때만 표시 */}
      {!isPackage && (
        <div className="form-group">

          <label className="quantity-label">수량 선택</label>
          <input
            type="number"
            value={quantity === 0 ? '' : quantity}
            onChange={(e) => {
              const inputValue = e.target.value
              if (inputValue === '') {
                setQuantity(0)
              } else {
                const newQuantity = parseInt(inputValue)
                if (!isNaN(newQuantity)) {
                  setQuantity(newQuantity)
                }
              }
            }}
            min="0"
            max={maxQuantity}
            className={`quantity-input-field ${quantity > 0 && quantity < minQuantity ? 'quantity-input-invalid' : ''}`}
            placeholder="수량을 입력하세요 (0부터 시작)"
          />
          <div className="quantity-hint-left">
            최소 {minQuantity.toLocaleString()} : 최대 {maxQuantity.toLocaleString()}
          </div>
        </div>
      )}

      {/* Link Input */}
      <div className="form-group">

        <label>링크 입력</label>
        <input
          type="url"
          value={link}
          onChange={(e) => setLink(e.target.value)}
          placeholder={`${category?.name || ''} 게시물 URL 또는 사용자명을 입력하세요`}
          className="form-control link-input-field"
        />

        <div className="url-info">
          <h5>📝 주문 URL 입력 방법</h5>
          <div className="url-examples">
            <p><strong>방법 1:</strong> https://www.instagram.com/인스타아이디</p>
            <p><strong>방법 2:</strong> 인스타아이디만 입력</p>
            <p><em>※ http → https, www 반드시 추가, I → i 소문자, co.kr → com</em></p>
          </div>
        </div>
      </div>

      {/* Package Steps Display */}
      {isPackage && packageDetail.steps && (
        <div className="package-steps">
          <h3>📦 패키지 구성</h3>
          <div className="steps-container">
            {packageDetail.steps.map((step, index) => (
              <div key={index} className="package-step">
                <div className="step-header">
                  <span className="step-number">{index + 1}</span>
                  <span className="step-name">{step.name}</span>
                </div>
                <div className="step-details">
                  <p className="step-quantity">
                    수량: {step.quantity.toLocaleString()}개 × {step.repeat}회
                  </p>
                  {step.term_value > 0 && (
                    <p className="step-term">
                      간격: {step.term_value}{step.term_unit === 'minute' ? '분' : '시간'}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Comments Input - for specific services */}
      {variant?.name?.includes('댓글') && (
        <div className="form-group">
          <label>댓글 내용</label>
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="댓글 내용을 입력하세요 (최대 200자)"
            maxLength="200"
            className="form-control"
            rows="4"
          />
          <div className="char-count">{(comments || '').length}/200</div>
        </div>
      )}

      {/* Total Price */}
      <div className="price-display">
        <div className="total-price">₩{Number(formattedPrice).toLocaleString()}</div>
        <div className="price-label">총 금액</div>
      </div>

      {/* Submit Button */}
      <div className="action-buttons">
        <button
          className="submit-btn"
          onClick={handleSubmit}
          disabled={!isFormValid}
          style={{
            opacity: isFormValid ? 1 : 0.5,
            cursor: isFormValid ? 'pointer' : 'not-allowed'
          }}
        >
          구매하기
        </button>
      </div>
    </div>
  )
}

export default OrderForm

