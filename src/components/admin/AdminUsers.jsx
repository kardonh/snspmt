import React, { useState, useEffect } from 'react';
import { Search, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/services/api';

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/users');
      setUsers(data.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadUsers(); }, []);

  const filtered = users.filter(u => 
    u.username?.toLowerCase().includes(search.toLowerCase()) ||
    u.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">사용자 관리</h2>
          <Button onClick={loadUsers} disabled={loading} variant="outline">
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            새로고침
          </Button>
        </div>

        <div className="flex items-center gap-2 mb-4">
          <Search className="h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="사용자 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">이름</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">이메일</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">잔액</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">추천코드</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">상태</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">가입일</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                    {loading ? '로딩 중...' : '사용자가 없습니다'}
                  </td>
                </tr>
              ) : (
                filtered.map((user) => (
                  <tr key={user.user_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">{user.user_id}</td>
                    <td className="px-4 py-3 text-sm font-medium">{user.display_name || user.username}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{user.email}</td>
                    <td className="px-4 py-3 text-sm font-medium">₩{user.balance.toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm">
                      {user.referral_code ? (
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-mono">
                          {user.referral_code}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {user.is_active ? '활성' : '비활성'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {new Date(user.created_at).toLocaleDateString('ko-KR')}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-sm text-gray-600">
          총 {filtered.length}명의 사용자
        </div>
      </div>
    </div>
  );
}

