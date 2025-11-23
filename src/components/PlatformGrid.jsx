import React from 'react'

function PlatformGrid({ categories, selectedPlatform, onSelectPlatform, categoryColors }) {
  return (
    <div className="service-selection">
      <div className="service-header">
        <div className="header-title">
          <h2>주문하기</h2>
          <p>원하는 서비스를 선택하고 주문해보세요!</p>
        </div>
      </div>

      <div className="platform-grid">
        <div 
          className={`platform-item ${selectedPlatform === 'recommended' ? 'selected' : ''}`}
          onClick={() => onSelectPlatform('recommended')}
        >
          <img src="https://assets.snsshop.kr/assets/img2/new-order/platform/recommend.svg" alt="추천 서비스" className="platform-icon" />
          <div className="platform-name">추천 서비스</div>
        </div>

        {categories.map(({ category_id, name, slug }) => {
          const color = categoryColors[slug] || '#667eea'
          return (
            <div
              key={category_id}
              className={`platform-item ${selectedPlatform === category_id ? 'selected' : ''}`}
              onClick={() => onSelectPlatform(category_id)}
              style={{ '--platform-color': color, '--platform-color-secondary': color }}
            >
              <img src={`https://assets.snsshop.kr/assets/img2/new-order/platform/recommend.svg`} alt={name} className="platform-icon" />
              <div className="platform-name">{name}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default PlatformGrid

