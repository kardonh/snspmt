import React from 'react'
import { Plus, Edit, Trash2, Tag } from 'lucide-react'

const CategoryManager = ({
  categories,
  selectedCategoryId,
  onSelectCategory,
  onAddCategory,
  onEditCategory,
  onDeleteCategory
}) => {
  return (
    <section className="manager-card">
      <div className="manager-card-header">
        <div>
          <p className="manager-step">STEP 1</p>
          <h3>카테고리</h3>
          <p className="manager-desc">서비스를 묶을 최상위 카테고리를 생성하고 선택하세요.</p>
        </div>
        <button className="btn-primary" onClick={onAddCategory}>
          <Plus size={14} />
          카테고리 추가
        </button>
      </div>

      <div className="manager-list">
        {categories.length === 0 && (
          <div className="empty-state">등록된 카테고리가 없습니다.</div>
        )}

        {categories.map((category) => (
          <button
            key={category.category_id}
            className={`manager-item ${selectedCategoryId === category.category_id ? 'active' : ''}`}
            onClick={() => onSelectCategory(category.category_id)}
            type="button"
          >
            <div className="item-leading-icon">
              <Tag size={16} />
            </div>
            <div className="item-content">
              <div className="item-title-row">
                <span className="item-title">{category.name}</span>
                {!category.is_active && <span className="badge muted">비활성</span>}
              </div>
              {category.slug && <p className="item-subtitle">/{category.slug}</p>}
            </div>
            <div className="item-actions">
              <button
                type="button"
                className="btn-icon"
                onClick={(e) => {
                  e.stopPropagation()
                  onEditCategory(category)
                }}
                title="수정"
              >
                <Edit size={14} />
              </button>
              <button
                type="button"
                className="btn-icon danger"
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteCategory(category.category_id)
                }}
                title="삭제"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </button>
        ))}
      </div>
    </section>
  )
}

export default CategoryManager

