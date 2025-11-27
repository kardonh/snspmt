import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, Plus, Edit, Trash2, X, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/services/api';

export default function AdminCoupons() {
  const [coupons, setCoupons] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState(null);
  const [couponForm, setCouponForm] = useState({
    coupon_code: '',
    coupon_name: '',
    discount_type: 'percentage',
    discount_value: '',
    product_variant_id: null,
    min_order_amount: '',
    valid_from: '',
    valid_until: ''
  });

  const loadCoupons = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/coupons');
      setCoupons(data.coupons || []);
    } catch (error) {
      console.error('Failed to load coupons:', error);
      alert('쿠폰 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadCoupons(); }, []);

  const openAddModal = () => {
    setEditingCoupon(null);
    setCouponForm({
      coupon_code: '',
      coupon_name: '',
      discount_type: 'percentage',
      discount_value: '',
      product_variant_id: null,
      min_order_amount: '',
      valid_from: '',
      valid_until: ''
    });
    setShowModal(true);
  };

  const openEditModal = (coupon) => {
    setEditingCoupon(coupon);
    setCouponForm({
      coupon_code: coupon.coupon_code || '',
      coupon_name: coupon.coupon_name || '',
      discount_type: coupon.discount_type || 'percentage',
      discount_value: coupon.discount_value || '',
      product_variant_id: coupon.product_variant_id || null,
      min_order_amount: coupon.min_order_amount || '',
      valid_from: coupon.valid_from ? coupon.valid_from.split('T')[0] : '',
      valid_until: coupon.valid_until ? coupon.valid_until.split('T')[0] : ''
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const url = editingCoupon ? `/admin/coupons/${editingCoupon.coupon_id}` : '/admin/coupons';
      const method = editingCoupon ? 'put' : 'post';
      await api[method](url, couponForm);
      await loadCoupons();
      setShowModal(false);
      alert(editingCoupon ? '쿠폰이 수정되었습니다.' : '쿠폰이 추가되었습니다.');
    } catch (error) {
      console.error('Failed to save coupon:', error);
      alert('쿠폰 저장에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (couponId) => {
    if (!confirm('정말 이 쿠폰을 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/admin/coupons/${couponId}`);
      await loadCoupons();
      alert('쿠폰이 삭제되었습니다.');
    } catch (error) {
      console.error('Failed to delete coupon:', error);
      alert('쿠폰 삭제에 실패했습니다.');
    }
  };

  const filtered = coupons.filter(c => {
    const searchLower = search.toLowerCase();
    return c.coupon_code?.toLowerCase().includes(searchLower) ||
           c.coupon_name?.toLowerCase().includes(searchLower);
  });

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">쿠폰 관리</h2>
          <div className="flex gap-2">
            <Button onClick={loadCoupons} disabled={loading} variant="outline">
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              새로고침
            </Button>
            <Button onClick={openAddModal}>
              <Plus className="h-4 w-4 mr-2" />
              쿠폰 추가
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-4">
          <Search className="h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="쿠폰 코드 또는 이름으로 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">쿠폰 코드</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">쿠폰 이름</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">할인 타입</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">할인 값</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">유효기간</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">작업</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-4 py-8 text-center text-gray-500">
                    {loading ? '로딩 중...' : search ? '검색 결과가 없습니다.' : '쿠폰이 없습니다.'}
                  </td>
                </tr>
              ) : (
                filtered.map((coupon) => (
                  <tr key={coupon.coupon_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium">{coupon.coupon_code}</td>
                    <td className="px-4 py-3 text-sm">{coupon.coupon_name}</td>
                    <td className="px-4 py-3 text-sm">
                      {coupon.discount_type === 'percentage' ? '퍼센트' : '고정금액'}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium">
                      {coupon.discount_type === 'percentage' 
                        ? `${coupon.discount_value}%`
                        : `₩${parseInt(coupon.discount_value).toLocaleString()}`}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {coupon.valid_from && coupon.valid_until ? (
                        <span>
                          {new Date(coupon.valid_from).toLocaleDateString('ko-KR')} ~ {new Date(coupon.valid_until).toLocaleDateString('ko-KR')}
                        </span>
                      ) : '무제한'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => openEditModal(coupon)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleDelete(coupon.coupon_id)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-sm text-gray-600">
          총 {filtered.length}개의 쿠폰
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
              <h3 className="text-lg font-bold">{editingCoupon ? '쿠폰 수정' : '쿠폰 추가'}</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">쿠폰 코드 *</label>
                <input
                  type="text"
                  value={couponForm.coupon_code}
                  onChange={(e) => setCouponForm({ ...couponForm, coupon_code: e.target.value })}
                  required
                  placeholder="예: WELCOME10"
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">쿠폰 이름 *</label>
                <input
                  type="text"
                  value={couponForm.coupon_name}
                  onChange={(e) => setCouponForm({ ...couponForm, coupon_name: e.target.value })}
                  required
                  placeholder="예: 신규 가입 환영 쿠폰"
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">할인 타입 *</label>
                  <select
                    value={couponForm.discount_type}
                    onChange={(e) => setCouponForm({ ...couponForm, discount_type: e.target.value })}
                    required
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="percentage">퍼센트 (%)</option>
                    <option value="fixed">고정금액 (원)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">할인 값 *</label>
                  <input
                    type="number"
                    value={couponForm.discount_value}
                    onChange={(e) => setCouponForm({ ...couponForm, discount_value: e.target.value })}
                    required
                    min="0"
                    step={couponForm.discount_type === 'percentage' ? '1' : '100'}
                    placeholder={couponForm.discount_type === 'percentage' ? '10' : '1000'}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">최소 주문 금액</label>
                  <input
                    type="number"
                    value={couponForm.min_order_amount}
                    onChange={(e) => setCouponForm({ ...couponForm, min_order_amount: e.target.value })}
                    min="0"
                    placeholder="0"
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">적용 상품 ID</label>
                  <input
                    type="number"
                    value={couponForm.product_variant_id || ''}
                    onChange={(e) => setCouponForm({ ...couponForm, product_variant_id: e.target.value ? parseInt(e.target.value) : null })}
                    placeholder="특정 상품에만 적용시 입력"
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">유효 시작일</label>
                  <input
                    type="date"
                    value={couponForm.valid_from}
                    onChange={(e) => setCouponForm({ ...couponForm, valid_from: e.target.value })}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">유효 종료일</label>
                  <input
                    type="date"
                    value={couponForm.valid_until}
                    onChange={(e) => setCouponForm({ ...couponForm, valid_until: e.target.value })}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={() => setShowModal(false)}>
                  취소
                </Button>
                <Button type="submit" disabled={loading}>
                  <Save className="h-4 w-4 mr-2" />
                  {editingCoupon ? '수정' : '추가'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
