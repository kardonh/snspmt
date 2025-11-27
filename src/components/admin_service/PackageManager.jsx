import React from 'react'
import { Package, Plus, Edit, Trash2 } from 'lucide-react'

const PackageManager = ({
  packages,
  categories,
  onAddPackage,
  onEditPackage,
  onDeletePackage
}) => {
  const getCategoryName = (categoryId) =>
    categories.find((cat) => cat.category_id === categoryId)?.name || '카테고리 미지정'

  return (
    <section className="manager-card">
      <div className="manager-card-header">
        <div>
          <p className="manager-step">STEP 4</p>
          <h3>패키지</h3>
          <p className="manager-desc">여러 세부서비스를 묶어 패키지 상품을 구성하세요.</p>
        </div>
        <button className="btn-primary" onClick={onAddPackage}>
          <Plus size={14} />
          패키지 추가
        </button>
      </div>

      <div className="manager-list">
        {packages.length === 0 && (
          <div className="empty-state">등록된 패키지가 없습니다.</div>
        )}

        {packages.map((pkg) => {
          const price = pkg?.meta_json?.price ?? pkg.price
          return (
            <div key={pkg.package_id} className="manager-item display-only">
              <div className="item-leading-icon">
                <Package size={16} />
              </div>
              <div className="item-content">
                <div className="item-title-row">
                  <span className="item-title">{pkg.name}</span>
                  <span className="badge">{getCategoryName(pkg.category_id)}</span>
                </div>
                {pkg.description && <p className="item-subtitle">{pkg.description}</p>}
                {price && (
                  <p className="item-subtitle">{parseFloat(price).toLocaleString()}원</p>
                )}
              </div>
              <div className="item-actions">
                <button
                  type="button"
                  className="btn-icon"
                  title="수정"
                  onClick={() => onEditPackage(pkg)}
                >
                  <Edit size={14} />
                </button>
                <button
                  type="button"
                  className="btn-icon danger"
                  title="삭제"
                  onClick={() => onDeletePackage(pkg.package_id)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default PackageManager

