import React from 'react'
import { Globe, ChevronRight } from 'lucide-react'

function ServiceTypeSelector({ 
  categories, 
  selectedPlatform, 
  selectedTab, 
  onTabChange, 
  products, 
  selectedService, 
  onServiceSelect,
  shouldShowTabs,
  getServiceBadge 
}) {
  const filterProducts = (product) => {
    if (!shouldShowTabs()) return true
    if (selectedTab === 'korean') return product.name.includes('한국인') || !product.name.includes('외국인')
    return product.name.includes('외국인')
  }

  return (
    <div className="service-type-selection">
      <div className="service-category">
        <h3 className="category-title">
          {categories.find(c => c.category_id === selectedPlatform)?.name} 서비스
        </h3>
        <p className="category-description">상세 서비스를 선택해주세요</p>

        {shouldShowTabs() && (
          <div className="service-tabs">
            <button 
              className={`tab-button ${selectedTab === 'korean' ? 'active' : ''}`} 
              onClick={() => onTabChange('korean')}
            >
              <img src="https://upload.wikimedia.org/wikipedia/commons/0/09/Flag_of_South_Korea.svg" alt="태극기" style={{ width: 20, height: 20 }} />
              한국인
            </button>
            <button 
              className={`tab-button ${selectedTab === 'foreign' ? 'active' : ''}`} 
              onClick={() => onTabChange('foreign')}
            >
              <Globe size={20} />
              외국인
            </button>
          </div>
        )}

        <div className="premium-banner">
          <div className="banner-content">
            <span>선택서비스 소셜리티 퀄리티 확인</span>
            <ChevronRight size={20} />
          </div>
        </div>

        <div className="service-list">
          {products.filter(filterProducts).map((product) => (
            <div
              key={product.product_id}
              className={`service-item ${selectedService === product.product_id ? 'selected' : ''}`}
              onClick={() => onServiceSelect(product.product_id)}
            >
              <div className="service-content">
                <div className="service-title-row">
                  {getServiceBadge(product)}
                  <span className="service-name">{product.name}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ServiceTypeSelector

