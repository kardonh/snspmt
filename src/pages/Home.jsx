import React from 'react'
import { useState, useEffect } from 'react'
import { instagramDetailedServices, platforms } from '../data/instagramDetailed'
import axios from 'axios'

const VITE_API_BASE_URL = import.meta.env.VITE_API_BASE_URL


function Home() {
  const [selectedPlatform, setSelectedPlatform] = useState('recommended')
  const [categories, setCategories] = useState([])

  const categoryColors = {
    instagram: '#e4405f',
    youtube: '#ff0000',
    facebook: '#1877f2',
    tiktok: '#000000',
    naver: '#03c75a'
  }

  useEffect(() => {
    axios.get(`${VITE_API_BASE_URL}/categories`)
      .then(response => {
        const payload = Array.isArray(response.data)
          ? response.data
          : response.data?.categories || []
        setCategories(payload)
        console.log(payload)
      })
      .catch(error => {
        console.error('Error fetching categories:', error)
      })
  }, [])


  return (
    <div>
      <div className="service-selection">
        <div className="service-header">
          <div className="header-title">
            <h2>주문하기</h2>
            <p>원하는 서비스를 선택하고 주문해보세요!</p>
          </div>
          <button
            className="order-method-btn"
            onClick={() => setShowOrderMethodModal(true)}
          >
            📋 주문방법
          </button>
        </div>

        <div className="platform-grid">
          {categories.length > 0 && categories.map(({ category_id, name, slug }) => {
            const color = categoryColors[slug] || '#667eea'
            return (
              <div
                key={category_id}
                className={`platform-item ${selectedPlatform === category_id ? 'selected' : ''}`}
                onClick={() => handlePlatformSelect(category_id)}
                style={{
                  '--platform-color': color,
                  '--platform-color-secondary': color
                }}
              >
                <img
                  src={'https://assets.snsshop.kr/assets/img2/new-order/platform/recommend.svg'}
                  alt={name}
                  className="platform-icon"
                  style={{ width: 32, height: 32 }}
                />
                <div className="platform-name">{name}</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default Home