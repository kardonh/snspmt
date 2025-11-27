import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/services/api';

export default function AdminPoints() {
  const [purchases, setPurchases] = useState([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(false);

  const loadPurchases = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/purchases');
      setPurchases(data.purchases || []);
    } catch (error) {
      console.error('Failed to load purchases:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadPurchases(); }, []);

  const handleApprove = async (id) => {
    if (!confirm('이 구매 신청을 승인하시겠습니까?')) return;
    try {
      await api.put(`/admin/purchases/${id}`, { status: 'approved' });
      await loadPurchases();
    } catch (error) {
      console.error('Failed to approve:', error);
      alert('승인 실패');
    }
  };

  const handleReject = async (id) => {
    if (!confirm('이 구매 신청을 거절하시겠습니까?')) return;
    try {
      await api.put(`/admin/purchases/${id}`, { status: 'rejected' });
      await loadPurchases();
    } catch (error) {
      console.error('Failed to reject:', error);
      alert('거절 실패');
    }
  };

  const filtered = purchases.filter(p => {
    const matchSearch = p.buyer_name?.toLowerCase().includes(search.toLowerCase()) ||
      p.email?.toLowerCase().includes(search.toLowerCase()) ||
      p.bank_info?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || p.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-700',
      approved: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700'
    };
    const labels = { pending: '대기중', approved: '승인됨', rejected: '거절됨' };
    return { style: styles[status] || 'bg-gray-100 text-gray-700', label: labels[status] || status };
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">포인트 구매 신청</h2>
          <Button onClick={loadPurchases} disabled={loading} variant="outline">
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            새로고침
          </Button>
        </div>

        <div className="flex gap-3 mb-4">
          <div className="flex items-center gap-2 flex-1">
            <Search className="h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="구매자 이름, 이메일, 은행정보 검색..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">전체</option>
            <option value="pending">대기중</option>
            <option value="approved">승인됨</option>
            <option value="rejected">거절됨</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">구매자</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">이메일</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">은행정보</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">금액</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">상태</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">신청일</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">작업</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-4 py-8 text-center text-gray-500">
                    {loading ? '로딩 중...' : '구매 신청이 없습니다'}
                  </td>
                </tr>
              ) : (
                filtered.map((purchase) => {
                  const badge = getStatusBadge(purchase.status);
                  return (
                    <tr key={purchase.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm">{purchase.id}</td>
                      <td className="px-4 py-3 text-sm font-medium">{purchase.buyer_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{purchase.email}</td>
                      <td className="px-4 py-3 text-sm">{purchase.bank_info}</td>
                      <td className="px-4 py-3 text-sm font-medium">₩{purchase.amount.toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${badge.style}`}
                        style={{wordBreak:'keep-all'}}
                        >
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {new Date(purchase.created_at).toLocaleDateString('ko-KR')}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {purchase.status === 'pending' && (
                          <div className="flex gap-2">
                            <Button size="sm" onClick={() => handleApprove(purchase.id)} className="bg-green-500 hover:bg-green-600">
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="destructive" onClick={() => handleReject(purchase.id)}>
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-sm text-gray-600">
          총 {filtered.length}개의 신청
        </div>
      </div>
    </div>
  );
}

