import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getUserCoupons } from '../services/snspopApi';
import { Gift, Clock, CheckCircle, XCircle } from 'lucide-react';
import './CouponPage.css';

const CouponPage = () => {
  const { currentUser } = useAuth();
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // all, active, used, expired

  useEffect(() => {
    if (currentUser) {
      fetchCoupons();
    }
  }, [currentUser]);

  const fetchCoupons = async () => {
    try {
      setLoading(true);
      const userCoupons = await getUserCoupons(currentUser.email);
      setCoupons(userCoupons);
      setError(null);
    } catch (err) {
      setError('쿠폰 정보를 불러오는 중 오류가 발생했습니다.');
      console.error('Error fetching coupons:', err);
    } finally {
      setLoading(false);
    }
  };

  const getFilteredCoupons = () => {
    const now = new Date();
    return coupons.filter(coupon => {
      const isExpired = new Date(coupon.expires_at) < now;
      
      switch (filter) {
        case 'active':
          return !coupon.is_used && !isExpired;
        case 'used':
          return coupon.is_used;
        case 'expired':
          return !coupon.is_used && isExpired;
        default:
          return true;
      }
    });
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getStatusIcon = (coupon) => {
    const now = new Date();
    const isExpired = new Date(coupon.expires_at) < now;
    
    if (coupon.is_used) {
      return <CheckCircle className="status-icon used" />;
    } else if (isExpired) {
      return <XCircle className="status-icon expired" />;
    } else {
      return <Clock className="status-icon active" />;
    }
  };

  const getStatusText = (coupon) => {
    const now = new Date();
    const isExpired = new Date(coupon.expires_at) < now;
    
    if (coupon.is_used) {
      return '사용됨';
    } else if (isExpired) {
      return '만료됨';
    } else {
      return '사용 가능';
    }
  };

  const getDaysUntilExpiry = (expiryDate) => {
    const now = new Date();
    const expiry = new Date(expiryDate);
    const diffTime = expiry - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return 0;
    if (diffDays === 0) return '오늘';
    if (diffDays === 1) return '내일';
    return `${diffDays}일 후`;
  };

  if (!currentUser) {
    return (
      <div className="coupon-page">
        <div className="container">
          <div className="auth-required">
            <Gift size={48} />
            <h2>로그인이 필요합니다</h2>
            <p>쿠폰을 확인하려면 로그인해주세요.</p>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="coupon-page">
        <div className="container">
          <div className="loading">
            <div className="spinner"></div>
            <p>쿠폰 정보를 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="coupon-page">
        <div className="container">
          <div className="error">
            <XCircle size={48} />
            <h2>오류가 발생했습니다</h2>
            <p>{error}</p>
            <button onClick={fetchCoupons} className="retry-btn">
              다시 시도
            </button>
          </div>
        </div>
      </div>
    );
  }

  const filteredCoupons = getFilteredCoupons();

  return (
    <div className="coupon-page">
      <div className="container">
        <div className="page-header">
          <div className="header-content">
            <Gift size={32} />
            <h1>내 쿠폰</h1>
          </div>
          <p className="header-description">
            보유한 쿠폰을 확인하고 결제 시 사용하세요
          </p>
        </div>

        <div className="filter-section">
          <div className="filter-tabs">
            <button
              className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              전체 ({coupons.length})
            </button>
            <button
              className={`filter-tab ${filter === 'active' ? 'active' : ''}`}
              onClick={() => setFilter('active')}
            >
              사용 가능 ({coupons.filter(c => !c.is_used && new Date(c.expires_at) > new Date()).length})
            </button>
            <button
              className={`filter-tab ${filter === 'used' ? 'active' : ''}`}
              onClick={() => setFilter('used')}
            >
              사용됨 ({coupons.filter(c => c.is_used).length})
            </button>
            <button
              className={`filter-tab ${filter === 'expired' ? 'active' : ''}`}
              onClick={() => setFilter('expired')}
            >
              만료됨 ({coupons.filter(c => !c.is_used && new Date(c.expires_at) < new Date()).length})
            </button>
          </div>
        </div>

        <div className="coupons-section">
          {filteredCoupons.length === 0 ? (
            <div className="no-coupons">
              <Gift size={48} />
              <h3>쿠폰이 없습니다</h3>
              <p>
                {filter === 'all' && '아직 쿠폰을 받지 못했습니다.'}
                {filter === 'active' && '사용 가능한 쿠폰이 없습니다.'}
                {filter === 'used' && '사용한 쿠폰이 없습니다.'}
                {filter === 'expired' && '만료된 쿠폰이 없습니다.'}
              </p>
            </div>
          ) : (
            <div className="coupons-grid">
              {filteredCoupons.map((coupon) => (
                <div key={coupon.id} className={`coupon-card ${coupon.is_used ? 'used' : ''}`}>
                  <div className="coupon-header">
                    <div className="coupon-status">
                      {getStatusIcon(coupon)}
                      <span className="status-text">{getStatusText(coupon)}</span>
                    </div>
                    <div className="coupon-code">{coupon.code}</div>
                  </div>
                  
                  <div className="coupon-body">
                    <div className="discount-info">
                      <span className="discount-value">
                        {coupon.discount_type === 'percentage' ? `${coupon.discount_value}%` : `${coupon.discount_value}원`}
                      </span>
                      <span className="discount-label">할인</span>
                    </div>
                    
                    <div className="coupon-details">
                      <div className="detail-item">
                        <span className="label">발급일:</span>
                        <span className="value">{formatDate(coupon.created_at)}</span>
                      </div>
                      <div className="detail-item">
                        <span className="label">만료일:</span>
                        <span className="value">{formatDate(coupon.expires_at)}</span>
                      </div>
                      {!coupon.is_used && new Date(coupon.expires_at) > new Date() && (
                        <div className="detail-item expiry-warning">
                          <span className="label">남은 기간:</span>
                          <span className="value">{getDaysUntilExpiry(coupon.expires_at)}</span>
                        </div>
                      )}
                      {coupon.is_used && (
                        <div className="detail-item">
                          <span className="label">사용일:</span>
                          <span className="value">{formatDate(coupon.used_at)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {coupon.is_used && (
                    <div className="coupon-footer used">
                      <CheckCircle size={16} />
                      <span>주문에서 사용됨</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="coupon-info">
          <h3>쿠폰 사용 안내</h3>
          <ul>
            <li>쿠폰은 결제 페이지에서 사용할 수 있습니다</li>
            <li>한 번 사용된 쿠폰은 재사용할 수 없습니다</li>
            <li>쿠폰은 발급일로부터 30일간 유효합니다</li>
            <li>만료된 쿠폰은 자동으로 사용 불가 처리됩니다</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default CouponPage;
