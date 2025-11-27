import React from 'react'
import { Plus, Edit, Trash2, Sparkles } from 'lucide-react'

const VariantManager = ({
  variants,
  products,
  selectedProductId,
  onAddVariant,
  onEditVariant,
  onDeleteVariant
}) => {
  const selectedProduct = products.find(
    (product) => product.product_id === selectedProductId
  )

  const productVariants = variants.filter(
    (variant) => variant.product_id === selectedProductId
  )

  return (
    <section className="manager-card">
      <div className="manager-card-header">
        <div>
          <p className="manager-step">STEP 3</p>
          <h3>세부서비스</h3>
          <p className="manager-desc">
            선택한 상품 아래 실제 구매 가능한 세부서비스를 등록하세요.
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() =>
            selectedProductId
              ? onAddVariant(selectedProductId, selectedProduct?.category_id)
              : null
          }
          disabled={!selectedProductId}
          title={selectedProductId ? '세부서비스 추가' : '먼저 상품을 선택하세요'}
        >
          <Plus size={14} />
          세부서비스 추가
        </button>
      </div>

      {!selectedProductId && (
        <div className="empty-state">먼저 상품을 선택해주세요.</div>
      )}

      {selectedProductId && (
        <div className="manager-list">
          {productVariants.length === 0 ? (
            <div className="empty-state">
              등록된 세부서비스가 없습니다. 추가 버튼을 눌러 생성하세요.
            </div>
          ) : (
            productVariants.map((variant) => (
              <div key={variant.variant_id} className="manager-item display-only">
                <div className="item-leading-icon">
                  <Sparkles size={16} />
                </div>
                <div className="item-content">
                  <div className="item-title-row">
                    <span className="item-title">{variant.name}</span>
                    <span className="badge">
                      {parseFloat(variant.price).toLocaleString()}원
                    </span>
                    {!variant.is_active && <span className="badge muted">비활성</span>}
                  </div>
                  <p className="item-subtitle">
                    최소 {variant.min_quantity || '-'} / 최대 {variant.max_quantity || '-'}
                    {variant.delivery_time_days && ` • ${variant.delivery_time_days}일`}
                  </p>
                </div>
                <div className="item-actions">
                  <button
                    type="button"
                    className="btn-icon"
                    title="수정"
                    onClick={() => onEditVariant(variant)}
                  >
                    <Edit size={14} />
                  </button>
                  <button
                    type="button"
                    className="btn-icon danger"
                    title="삭제"
                    onClick={() => onDeleteVariant(variant.variant_id)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  )
}

export default VariantManager

