import React from 'react'
import { Package, TrendingUp } from 'lucide-react'

function PackageList({ packages, selectedPackage, onSelectPackage }) {
  const calculateTotalPrice = (pkg) => {
    if (!pkg.items || pkg.items.length === 0) return 0
    return pkg.items.reduce((sum, item) => 
      sum + (parseFloat(item.variant_price) * item.quantity * item.repeat_count), 0
    )
  }

  return (
    <div className="service-type-selection">
      <div className="service-category">
        <h3 className="category-title">
          <Package size={24} style={{ display: 'inline', marginRight: '8px' }} />
          추천 패키지
        </h3>
        <p className="category-description">최적화된 패키지 상품을 선택해보세요</p>

        <div className="premium-banner">
          <div className="banner-content">
            <TrendingUp size={20} />
            <span>프리미엄 패키지로 더 빠른 성장을 경험하세요</span>
          </div>
        </div>

        <div className="service-list">
          {packages.map((pkg) => {
            const totalPrice = calculateTotalPrice(pkg)
            const hasItems = pkg.items && pkg.items.length > 0

            return (
              <div
                key={pkg.package_id}
                className={`service-item ${selectedPackage === pkg.package_id ? 'selected' : ''} ${hasItems ? 'featured' : ''}`}
                onClick={() => onSelectPackage(pkg.package_id)}
              >
                <div className="service-content">
                  <div className="service-title-row">
                    {/* {hasItems && <span className="service-badge auto">패키지</span>} */}
                    <span className="service-name">{pkg.name}</span>
                  </div>
                  {/* {pkg.description && (
                    <p style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                      {pkg.description}
                    </p>
                  )} */}
                  {/* {hasItems && (
                    <div style={{ marginTop: '8px', fontSize: '14px', fontWeight: 'bold', color: '#667eea' }}>
                      총 {pkg.items.length}개 서비스 • ₩{totalPrice.toLocaleString()}
                    </div>
                  )} */}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default PackageList

