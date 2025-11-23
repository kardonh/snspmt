import React from 'react'
import { Plus, Edit, Trash2, Layers } from 'lucide-react'

const ProductManager = ({
  products,
  categories,
  selectedCategoryId,
  selectedProductId,
  onSelectProduct,
  onAddProduct,
  onEditProduct,
  onDeleteProduct,
  onAddVariant
}) => {
  const categoryName =
    categories.find((cat) => cat.category_id === selectedCategoryId)?.name || null

  const categoryProducts = products.filter(
    (product) => product.category_id === selectedCategoryId
  )

  return (
    <section className="manager-card">
      <div className="manager-card-header">
        <div>
          <p className="manager-step">STEP 2</p>
          <h3>상품 (Sub Category)</h3>
          <p className="manager-desc">
            선택한 카테고리 안에서 세부 상품(세부 플랫폼)을 구성하세요.
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => onAddProduct(selectedCategoryId || null)}
          disabled={!selectedCategoryId}
          title={selectedCategoryId ? '상품 추가' : '먼저 카테고리를 선택하세요'}
        >
          <Plus size={14} />
          상품 추가
        </button>
      </div>

      {!selectedCategoryId && (
        <div className="empty-state">먼저 카테고리를 선택해주세요.</div>
      )}

      {selectedCategoryId && (
        <div className="manager-list">
          {categoryProducts.length === 0 ? (
            <div className="empty-state">
              {categoryName} 카테고리에 등록된 상품이 없습니다.
            </div>
          ) : (
            categoryProducts.map((product) => (
              <button
                key={product.product_id}
                type="button"
                className={`manager-item ${selectedProductId === product.product_id ? 'active' : ''}`}
                onClick={() => onSelectProduct(product.product_id)}
              >
                <div className="item-leading-icon">
                  <Layers size={16} />
                </div>
                <div className="item-content">
                  <div className="item-title-row">
                    <span className="item-title">{product.name}</span>
                    {!product.is_domestic && <span className="badge muted">해외</span>}
                    {product.is_auto && <span className="badge">자동</span>}
                  </div>
                  {product.description && (
                    <p className="item-subtitle">{product.description}</p>
                  )}
                </div>
                <div className="item-actions">
                  <button
                    type="button"
                    className="btn-icon"
                    title="세부서비스 추가"
                    onClick={(e) => {
                      e.stopPropagation()
                      onAddVariant(product.product_id, product.category_id)
                    }}
                  >
                    <Plus size={14} />
                  </button>
                  <button
                    type="button"
                    className="btn-icon"
                    title="수정"
                    onClick={(e) => {
                      e.stopPropagation()
                      onEditProduct(product)
                    }}
                  >
                    <Edit size={14} />
                  </button>
                  <button
                    type="button"
                    className="btn-icon danger"
                    title="삭제"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteProduct(product.product_id)
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </section>
  )
}

export default ProductManager

