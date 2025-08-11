import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { getUserCoupons } from '../services/snspopApi'
import { Gift, Clock, CheckCircle, XCircle } from 'lucide-react'
import './CouponsPage.css'

const CouponsPage = () => {
  const { currentUser } = useAuth()
  const [coupons, setCoupons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (currentUser) {
      fetchCoupons()
    }
  }, [currentUser])

  const fetchCoupons = async () => {
    try {
      setLoading(true)
      const userCoupons = await getUserCoupons(currentUser.email)
      setCoupons(userCoupons)
      setError(null)
    } catch (err) {
      setError('쿠폰 정보를 불러오는데 실패했습니다.')
      console.error('쿠폰 조회 오류:', err)
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (coupon) => {
    if (coupon.is_used) {
      return <CheckCircle size={20} className="status-icon used" />
    }
    
    const now = new Date()
    const expiresAt = new Date(coupon.expires_at)
    
    if (now > expiresAt) {
      return <XCircle size={20} className="status-icon expired" />
    }
    
    return <Clock size={20} className="status-icon active" />
  }

  const getStatusText = (coupon) => {
    if (coupon.is_used) {
      return '사용됨'
    }
    
    const now = new Date()
    const expiresAt = new Date(coupon.expires_at)
    
    if (now > expiresAt) {
      return '만료됨'
    }
    
    return '사용 가능'
  }

  const getStatusClass = (coupon) => {
    if (coupon.is_used) {
      return 'used'
    }
    
    const now = new Date()
    const expiresAt = new Date(coupon.expires_at)
    
    if (now > expiresAt) {
      return 'expired'
    }
    
    return 'active'
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  }

  const formatExpiryDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = date - now
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays < 0) {
      return '만료됨'
    } else if (diffDays === 0) {
      return '오늘 만료'
    } else if (diffDays === 1) {
      return '내일 만료'
    } else {
      return `${diffDays}일 후 만료`
    }
  }

  const getDiscountText = (coupon) => {
    if (coupon.discount_type === 'percentage') {
      return `${coupon.discount_value}% 할인`
    } else if (coupon.discount_type === 'fixed') {
      return `₩${coupon.discount_value.toLocaleString()} 할인`
    }
    return '할인'
  }

  if (!currentUser) {
    return (
      <div className="coupons-page">
        <div className="coupons-container">
          <h1>내 쿠폰</h1>
          <p>로그인이 필요합니다.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="coupons-page">
        <div className="coupons-container">
          <h1>내 쿠폰</h1>
          <div className="loading">쿠폰 정보를 불러오는 중...</div>
        </div>
      </div>
    )
  }

  const activeCoupons = coupons.filter(coupon => 
    !coupon.is_used && new Date(coupon.expires_at) > new Date()
  )
  
  const usedCoupons = coupons.filter(coupon => coupon.is_used)
  
  const expiredCoupons = coupons.filter(coupon => 
    !coupon.is_used && new Date(coupon.expires_at) <= new Date()
  )

  return (
    <div className="coupons-page">
      <div className="coupons-container">
        <div className="coupons-header">
          <h1>내 쿠폰</h1>
          <div className="coupons-summary">
            <div className="summary-item">
              <span className="label">사용 가능</span>
              <span className="value active">{activeCoupons.length}개</span>
            </div>
            <div className="summary-item">
              <span className="label">사용됨</span>
              <span className="value used">{usedCoupons.length}개</span>
            </div>
            <div className="summary-item">
              <span className="label">만료됨</span>
              <span className="value expired">{expiredCoupons.length}개</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {coupons.length === 0 ? (
          <div className="no-coupons">
            <div className="no-coupons-icon">
              <Gift size={48} />
            </div>
            <h3>아직 쿠폰이 없습니다</h3>
            <p>추천인 코드를 사용하거나 친구를 초대하여 쿠폰을 받아보세요!</p>
          </div>
        ) : (
          <div className="coupons-content">
            {/* 사용 가능한 쿠폰 */}
            {activeCoupons.length > 0 && (
              <div className="coupon-section">
                <h2>사용 가능한 쿠폰</h2>
                <div className="coupons-grid">
                  {activeCoupons.map((coupon) => (
                    <div key={coupon.id} className={`coupon-card ${getStatusClass(coupon)}`}>
                      <div className="coupon-header">
                        <div className="coupon-status">
                          {getStatusIcon(coupon)}
                          <span className="status-text">{getStatusText(coupon)}</span>
                        </div>
                        <div className="coupon-expiry">
                          {formatExpiryDate(coupon.expires_at)}
                        </div>
                      </div>
                      
                      <div className="coupon-content">
                        <div className="coupon-discount">
                          {getDiscountText(coupon)}
                        </div>
                        <div className="coupon-code">
                          {coupon.code}
                        </div>
                        <div className="coupon-date">
                          발급일: {formatDate(coupon.created_at)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 사용된 쿠폰 */}
            {usedCoupons.length > 0 && (
              <div className="coupon-section">
                <h2>사용된 쿠폰</h2>
                <div className="coupons-grid">
                  {usedCoupons.map((coupon) => (
                    <div key={coupon.id} className={`coupon-card ${getStatusClass(coupon)}`}>
                      <div className="coupon-header">
                        <div className="coupon-status">
                          {getStatusIcon(coupon)}
                          <span className="status-text">{getStatusText(coupon)}</span>
                        </div>
                        <div className="coupon-used-date">
                          {coupon.used_at ? formatDate(coupon.used_at) : '사용됨'}
                        </div>
                      </div>
                      
                      <div className="coupon-content">
                        <div className="coupon-discount">
                          {getDiscountText(coupon)}
                        </div>
                        <div className="coupon-code">
                          {coupon.code}
                        </div>
                        <div className="coupon-date">
                          발급일: {formatDate(coupon.created_at)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 만료된 쿠폰 */}
            {expiredCoupons.length > 0 && (
              <div className="coupon-section">
                <h2>만료된 쿠폰</h2>
                <div className="coupons-grid">
                  {expiredCoupons.map((coupon) => (
                    <div key={coupon.id} className={`coupon-card ${getStatusClass(coupon)}`}>
                      <div className="coupon-header">
                        <div className="coupon-status">
                          {getStatusIcon(coupon)}
                          <span className="status-text">{getStatusText(coupon)}</span>
                        </div>
                        <div className="coupon-expiry">
                          만료일: {formatDate(coupon.expires_at)}
                        </div>
                      </div>
                      
                      <div className="coupon-content">
                        <div className="coupon-discount">
                          {getDiscountText(coupon)}
                        </div>
                        <div className="coupon-code">
                          {coupon.code}
                        </div>
                        <div className="coupon-date">
                          발급일: {formatDate(coupon.created_at)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default CouponsPage
