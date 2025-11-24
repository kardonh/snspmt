import React, { useState, useEffect } from 'react';
import { Search, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/services/api';

export default function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(false);

  const loadOrders = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/transactions');
      setOrders(data.transactions || []);
    } catch (error) {
      console.error('Failed to load orders:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadOrders(); }, []);

  const filtered = orders.filter(o => {
    const matchSearch = o.order_id?.toString().includes(search) ||
      o.service_name?.toLowerCase().includes(search.toLowerCase()) ||
      o.user_id?.toString().includes(search);
    const matchStatus = statusFilter === 'all' || o.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-700',
      processing: 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700'
    };
    const labels = {
      pending: '대기중',
      processing: '처리중',
      completed: '완료',
      failed: '실패'
    };
    return { style: styles[status] || 'bg-gray-100 text-gray-700', label: labels[status] || status };
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">주문 관리</h2>
          <Button onClick={loadOrders} disabled={loading} variant="outline">
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            새로고침
          </Button>
        </div>

        <div className="flex gap-3 mb-4">
          <div className="flex items-center gap-2 flex-1">
            <Search className="h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="주문 검색..."
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
            <option value="processing">처리중</option>
            <option value="completed">완료</option>
            <option value="failed">실패</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">주문ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">사용자ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">서비스</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">수량</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">가격</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">상태</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">주문일</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                    {loading ? '로딩 중...' : '주문이 없습니다'}
                  </td>
                </tr>
              ) : (
                filtered.map((order) => {
                  const badge = getStatusBadge(order.status);
                  return (
                    <tr key={order.order_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono">{order.order_id}</td>
                      <td className="px-4 py-3 text-sm">{order.user_id}</td>
                      <td className="px-4 py-3 text-sm max-w-xs truncate" title={order.service_name}>
                        {order.service_name}
                      </td>
                      <td className="px-4 py-3 text-sm">{order.quantity}</td>
                      <td className="px-4 py-3 text-sm font-medium">₩{order.total_amount.toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${badge.style}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {new Date(order.created_at).toLocaleDateString('ko-KR')}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-sm text-gray-600">
          총 {filtered.length}개의 주문
        </div>
      </div>
    </div>
  );
}

