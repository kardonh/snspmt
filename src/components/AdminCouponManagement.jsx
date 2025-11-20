import React, { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, X, Save, Search } from 'lucide-react'
import './AdminCouponManagement.css'

const AdminCouponManagement = ({ adminFetch }) => {
  const [coupons, setCoupons] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  
  // 모달 상태
  const [showModal, setShowModal] = useState(false)
  const [editingCoupon, setEditingCoupon] = useState(null)
  
  // 폼 상태
  const [couponForm, setCouponForm] = useState({
    coupon_code: '',
    coupon_name: '',
    discount_type: 'percentage', // 'percentage' or 'fixed'
    discount_value: '',
    product_variant_id: null,
    min_order_amount: '',
    valid_from: '',
    valid_until: ''
  })

  // 쿠폰 목록 로드
  useEffect(() => {
    loadCoupons()
  }, [])

  const loadCoupons = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await adminFetch('/api/admin/coupons')
      if (!response.ok) {
        throw new Error('쿠폰 목록을 불러오는데 실패했습니다.')
      }
      const data = await response.json()
      setCoupons(data.coupons || [])
    } catch (e) {
      console.error('쿠폰 목록 로드 오류:', e)
      setError(e.message || '쿠폰 목록을 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const openAddModal = () => {
    setEditingCoupon(null)
    setCouponForm({
      coupon_code: '',
      coupon_name: '',
      discount_type: 'percentage',
      discount_value: '',
      product_variant_id: null,
      min_order_amount: '',
      valid_from: '',
      valid_until: ''
    })
    setShowModal(true)
  }

  const openEditModal = (coupon) => {
    setEditingCoupon(coupon)
    setCouponForm({
      coupon_code: coupon.coupon_code || '',
      coupon_name: coupon.coupon_name || '',
      discount_type: coupon.discount_type || 'percentage',
      discount_value: coupon.discount_value || '',
      product_variant_id: coupon.product_variant_id || null,
      min_order_amount: coupon.min_order_amount || '',
      valid_from: coupon.valid_from ? coupon.valid_from.split('T')[0] : '',
      valid_until: coupon.valid_until ? coupon.valid_until.split('T')[0] : ''
    })
    setShowModal(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)

      const url = editingCoupon 
        ? `/api/admin/coupons/${editingCoupon.coupon_id}`
        : '/api/admin/coupons'
      
      const method = editingCoupon ? 'PUT' : 'POST'

      const response = await adminFetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(couponForm)
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || '쿠폰 저장에 실패했습니다.')
      }

      await loadCoupons()
      setShowModal(false)
      alert(editingCoupon ? '쿠폰이 수정되었습니다.' : '쿠폰이 추가되었습니다.')
    } catch (e) {
      console.error('쿠폰 저장 오류:', e)
      setError(e.message || '쿠폰 저장에 실패했습니다.')
      alert(e.message || '쿠폰 저장에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (couponId) => {
    if (!confirm('정말 이 쿠폰을 삭제하시겠습니까?')) {
      return
    }

    try {
      setLoading(true)
      setError(null)
      const response = await adminFetch(`/api/admin/coupons/${couponId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error('쿠폰 삭제에 실패했습니다.')
      }

      await loadCoupons()
      alert('쿠폰이 삭제되었습니다.')
    } catch (e) {
      console.error('쿠폰 삭제 오류:', e)
      setError(e.message || '쿠폰 삭제에 실패했습니다.')
      alert(e.message || '쿠폰 삭제에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const filteredCoupons = coupons.filter(coupon => {
    const searchLower = searchTerm.toLowerCase()
    return (
      coupon.coupon_code?.toLowerCase().includes(searchLower) ||
      coupon.coupon_name?.toLowerCase().includes(searchLower)
    )
  })

  return (
    <div className="admin-coupon-management">
      <div className="header">
        <h2>쿠폰 관리</h2>
        <div className="header-actions">
          <div className="search-box">
            <Search size={18} />
            <input
              type="text"
              placeholder="쿠폰 코드 또는 이름으로 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button onClick={openAddModal} className="btn-primary">
            <Plus size={18} />
            쿠폰 추가
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {loading && !coupons.length && (
        <div className="loading">로딩 중...</div>
      )}

      {!loading && filteredCoupons.length === 0 && (
        <div className="empty-state">
          {searchTerm ? '검색 결과가 없습니다.' : '쿠폰이 없습니다.'}
        </div>
      )}

      {filteredCoupons.length > 0 && (
        <div className="coupons-grid">
          {filteredCoupons.map(coupon => (
            <div key={coupon.coupon_id} className="coupon-card">
              <div className="coupon-header">
                <h3>{coupon.coupon_name || coupon.coupon_code}</h3>
                <div className="coupon-actions">
                  <button
                    onClick={() => openEditModal(coupon)}
                    className="btn-icon"
                    title="수정"
                  >
                    <Edit size={16} />
                  </button>
                  <button
                    onClick={() => handleDelete(coupon.coupon_id)}
                    className="btn-icon btn-danger"
                    title="삭제"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <div className="coupon-body">
                <div className="coupon-field">
                  <span className="field-label">쿠폰 코드:</span>
                  <span className="field-value">{coupon.coupon_code}</span>
                </div>
                <div className="coupon-field">
                  <span className="field-label">할인 타입:</span>
                  <span className="field-value">
                    {coupon.discount_type === 'percentage' ? '퍼센트' : '고정금액'}
                  </span>
                </div>
                <div className="coupon-field">
                  <span className="field-label">할인 값:</span>
                  <span className="field-value">
                    {coupon.discount_type === 'percentage' 
                      ? `${coupon.discount_value}%`
                      : `${parseInt(coupon.discount_value).toLocaleString()}원`}
                  </span>
                </div>
                {coupon.product_variant_id && (
                  <div className="coupon-field">
                    <span className="field-label">적용 상품:</span>
                    <span className="field-value">ID: {coupon.product_variant_id}</span>
                  </div>
                )}
                {coupon.valid_from && (
                  <div className="coupon-field">
                    <span className="field-label">유효 시작:</span>
                    <span className="field-value">
                      {new Date(coupon.valid_from).toLocaleDateString('ko-KR')}
                    </span>
                  </div>
                )}
                {coupon.valid_until && (
                  <div className="coupon-field">
                    <span className="field-label">유효 종료:</span>
                    <span className="field-value">
                      {new Date(coupon.valid_until).toLocaleDateString('ko-KR')}
                    </span>
                  </div>
                )}
                {coupon.created_at && (
                  <div className="coupon-field">
                    <span className="field-label">생성일:</span>
                    <span className="field-value">
                      {new Date(coupon.created_at).toLocaleDateString('ko-KR')}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 쿠폰 추가/수정 모달 */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingCoupon ? '쿠폰 수정' : '쿠폰 추가'}</h3>
              <button onClick={() => setShowModal(false)} className="btn-icon">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="modal-body">
              <div className="form-group">
                <label>쿠폰 코드 *</label>
                <input
                  type="text"
                  value={couponForm.coupon_code}
                  onChange={(e) => setCouponForm({ ...couponForm, coupon_code: e.target.value })}
                  required
                  placeholder="예: WELCOME10"
                />
              </div>
              <div className="form-group">
                <label>쿠폰 이름 *</label>
                <input
                  type="text"
                  value={couponForm.coupon_name}
                  onChange={(e) => setCouponForm({ ...couponForm, coupon_name: e.target.value })}
                  required
                  placeholder="예: 신규 가입 환영 쿠폰"
                />
              </div>
              <div className="form-group">
                <label>할인 타입 *</label>
                <select
                  value={couponForm.discount_type}
                  onChange={(e) => setCouponForm({ ...couponForm, discount_type: e.target.value })}
                  required
                >
                  <option value="percentage">퍼센트 (%)</option>
                  <option value="fixed">고정금액 (원)</option>
                </select>
              </div>
              <div className="form-group">
                <label>할인 값 *</label>
                <input
                  type="number"
                  value={couponForm.discount_value}
                  onChange={(e) => setCouponForm({ ...couponForm, discount_value: e.target.value })}
                  required
                  min="0"
                  step={couponForm.discount_type === 'percentage' ? '1' : '100'}
                  placeholder={couponForm.discount_type === 'percentage' ? '10' : '1000'}
                />
              </div>
              <div className="form-group">
                <label>최소 주문 금액</label>
                <input
                  type="number"
                  value={couponForm.min_order_amount}
                  onChange={(e) => setCouponForm({ ...couponForm, min_order_amount: e.target.value })}
                  min="0"
                  placeholder="0"
                />
              </div>
              <div className="form-group">
                <label>적용 상품 ID (선택)</label>
                <input
                  type="number"
                  value={couponForm.product_variant_id || ''}
                  onChange={(e) => setCouponForm({ ...couponForm, product_variant_id: e.target.value ? parseInt(e.target.value) : null })}
                  placeholder="특정 상품에만 적용하려면 상품 ID 입력"
                />
              </div>
              <div className="form-group">
                <label>유효 시작일</label>
                <input
                  type="date"
                  value={couponForm.valid_from}
                  onChange={(e) => setCouponForm({ ...couponForm, valid_from: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>유효 종료일</label>
                <input
                  type="date"
                  value={couponForm.valid_until}
                  onChange={(e) => setCouponForm({ ...couponForm, valid_until: e.target.value })}
                />
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">
                  취소
                </button>
                <button type="submit" className="btn-primary" disabled={loading}>
                  <Save size={18} />
                  {editingCoupon ? '수정' : '추가'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminCouponManagement


