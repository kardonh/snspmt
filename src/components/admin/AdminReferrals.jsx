import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, UserPlus, Eye, Trash2, CheckCircle, Edit } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import api from '@/services/api';

export default function AdminReferrals() {
  const [referrals, setReferrals] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [detailsModal, setDetailsModal] = useState(false);
  const [selectedReferral, setSelectedReferral] = useState(null);
  const [commissionRate, setCommissionRate] = useState(10);
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [registrationForm, setRegistrationForm] = useState({
    userId: '',
    email: '',
    name: '',
    phone: ''
  });

  const loadReferrals = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/referral/list');
      setReferrals(data.referrals || []);
    } catch (error) {
      console.error('Failed to load referrals:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const { data } = await api.get('/admin/users');
      setUsers(data.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  useEffect(() => { 
    loadReferrals();
    loadUsers();
  }, []);

  const handleUserSelect = (userId) => {
    const user = users.find(u => u.user_id.toString() === userId);
    if (user) {
      setRegistrationForm({
        userId: user.user_id,
        email: user.email,
        name: user.display_name || user.username,
        phone: user.phone || ''
      });
    }
  };

  const handleRegisterReferral = async () => {
    if (!registrationForm.email) {
      alert('이메일을 입력해주세요.');
      return;
    }
    try {
      await api.post('/admin/referral/register', {
        email: registrationForm.email,
        name: registrationForm.name,
        phone: registrationForm.phone
      });
      await loadReferrals();
      setShowModal(false);
      setRegistrationForm({ userId: '', email: '', name: '', phone: '' });
      alert(`추천인이 성공적으로 등록되었습니다!\n이메일: ${registrationForm.email}`);
    } catch (error) {
      console.error('Failed to register referral:', error);
      alert('추천인 등록에 실패했습니다.');
    }
  };

  const handleActivateAllCodes = async () => {
    if (!confirm('모든 추천인 코드를 활성화하시겠습니까?')) return;
    try {
      await api.post('/admin/referral/activate-all');
      await loadReferrals();
      alert('모든 코드가 활성화되었습니다.');
    } catch (error) {
      console.error('Failed to activate codes:', error);
      alert('코드 활성화에 실패했습니다.');
    }
  };

  const handleDeleteReferral = async (code, userId) => {
    if (!confirm(`정말로 추천인 코드 "${code}"를 삭제하시겠습니까?`)) return;
    try {
      await api.delete(`/admin/referral/codes/${code}`);
      await loadReferrals();
      alert('추천인 코드가 삭제되었습니다.');
    } catch (error) {
      console.error('Failed to delete referral:', error);
      alert('삭제에 실패했습니다.');
    }
  };

  const handleViewDetails = (referral) => {
    setSelectedReferral(referral);
    setCommissionRate(((referral.commission_rate || 0.1) * 100).toFixed(1));
    setDetailsModal(true);
  };

  const handleUpdateCommission = async () => {
    try {
      const rate = parseFloat(commissionRate) / 100;
      await api.put('/admin/referral/update-commission-rate', {
        referrer_email: selectedReferral.email,
        referrer_user_id: selectedReferral.id,
        commission_rate: rate
      });
      await loadReferrals();
      setDetailsModal(false);
      alert(`커미션 비율이 ${commissionRate}%로 변경되었습니다.`);
    } catch (error) {
      console.error('Failed to update commission:', error);
      alert('커미션 비율 변경에 실패했습니다.');
    }
  };

  const filtered = referrals.filter(r => 
    r.name?.toLowerCase().includes(search.toLowerCase()) ||
    r.email?.toLowerCase().includes(search.toLowerCase()) ||
    r.referralCode?.toLowerCase().includes(search.toLowerCase())
  );

  const filteredUsers = users.filter(u =>
    u.email?.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.username?.toLowerCase().includes(userSearch.toLowerCase()) ||
    u.display_name?.toLowerCase().includes(userSearch.toLowerCase())
  );

  const getStatusBadge = (status) => {
    const styles = {
      active: 'bg-green-100 text-green-700',
      inactive: 'bg-gray-100 text-gray-700'
    };
    const labels = { active: '활성', inactive: '비활성' };
    return { style: styles[status] || 'bg-gray-100 text-gray-700', label: labels[status] || status };
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">추천인 관리</h2>
          <div className="flex gap-2">
            <Button onClick={loadReferrals} disabled={loading} variant="outline">
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              새로고침
            </Button>
            <Button variant="secondary" onClick={handleActivateAllCodes}>
              <CheckCircle className="h-4 w-4 mr-2" />
              모든 코드 활성화
            </Button>
            <Button variant="default" onClick={() => setShowModal(true)}>
              <UserPlus className="h-4 w-4 mr-2" />
              추천인 등록
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-4">
          <Search className="h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="이름, 이메일, 추천코드 검색..."
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
                <th className="px-4 py-3 text-left text-sm font-semibold">전화번호</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">추천코드</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">상태</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">가입일</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">작업</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-4 py-8 text-center text-gray-500">
                    {loading ? '로딩 중...' : '추천인이 없습니다'}
                  </td>
                </tr>
              ) : (
                filtered.map((referral) => {
                  const badge = getStatusBadge(referral.status);
                  return (
                    <tr key={referral.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm">{referral.id}</td>
                      <td className="px-4 py-3 text-sm font-medium">{referral.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{referral.email}</td>
                      <td className="px-4 py-3 text-sm">
                        {referral.phone ? (
                          referral.phone
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-mono">
                          {referral.referralCode}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${badge.style}`} style={{wordBreak:'keep-all'}}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {new Date(referral.joinDate).toLocaleDateString('ko-KR')}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline" onClick={() => handleViewDetails(referral)}>
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button size="sm" variant="destructive" onClick={() => handleDeleteReferral(referral.referralCode, referral.id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex justify-between items-center">
          <div className="text-sm text-gray-600">
            총 {filtered.length}명의 추천인
          </div>
          <div className="bg-blue-50 px-4 py-2 rounded-lg">
            <span className="text-sm text-blue-700 font-medium">
              전체 추천인 수: {referrals.length}명
            </span>
          </div>
        </div>
      </div>

      {/* Referral Registration Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>추천인 등록</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">사용자 검색 및 선택</label>
              <div className="mt-1 space-y-2">
                <Input
                  placeholder="사용자 이름 또는 이메일로 검색..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                />
                {userSearch && (
                  <div className="max-h-48 overflow-y-auto border rounded-lg">
                    {filteredUsers.length === 0 ? (
                      <div className="p-4 text-center text-gray-500">검색 결과가 없습니다</div>
                    ) : (
                      filteredUsers.map((user) => (
                        <button
                          key={user.user_id}
                          onClick={() => {
                            handleUserSelect(user.user_id.toString());
                            setUserSearch('');
                          }}
                          className="w-full px-4 py-2 text-left hover:bg-gray-50 border-b last:border-b-0"
                        >
                          <div className="font-medium">{user.display_name || user.username}</div>
                          <div className="text-sm text-gray-600">{user.email}</div>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="border-t pt-4">
              <p className="text-sm text-gray-600 mb-3">또는 직접 입력</p>
              
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-gray-700">이메일 *</label>
                  <Input
                    type="email"
                    value={registrationForm.email}
                    onChange={(e) => setRegistrationForm({ ...registrationForm, email: e.target.value })}
                    placeholder="example@email.com"
                    className="mt-1"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-700">이름</label>
                  <Input
                    value={registrationForm.name}
                    onChange={(e) => setRegistrationForm({ ...registrationForm, name: e.target.value })}
                    placeholder="홍길동"
                    className="mt-1"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-700">전화번호</label>
                  <Input
                    value={registrationForm.phone}
                    onChange={(e) => setRegistrationForm({ ...registrationForm, phone: e.target.value })}
                    placeholder="010-1234-5678"
                    className="mt-1"
                  />
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setShowModal(false);
              setRegistrationForm({ userId: '', email: '', name: '', phone: '' });
              setUserSearch('');
            }}>
              취소
            </Button>
            <Button onClick={handleRegisterReferral}>
              <UserPlus className="h-4 w-4 mr-2" />
              등록
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Referral Details Modal */}
      <Dialog open={detailsModal} onOpenChange={setDetailsModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>추천인 세부정보</DialogTitle>
          </DialogHeader>
          {selectedReferral && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700">추천인 코드</label>
                <div className="mt-1 px-4 py-2 bg-gray-100 rounded font-mono text-lg font-bold">
                  {selectedReferral.referralCode}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">이름</label>
                <Input value={selectedReferral.name || ''} readOnly className="mt-1 bg-gray-50" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">이메일</label>
                <Input value={selectedReferral.email || ''} readOnly className="mt-1 bg-gray-50" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">전화번호</label>
                <Input value={selectedReferral.phone || '-'} readOnly className="mt-1 bg-gray-50" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">상태</label>
                <div className="mt-1">
                  {(() => {
                    const badge = getStatusBadge(selectedReferral.status);
                    return (
                      <span className={`px-3 py-1 rounded text-sm font-medium ${badge.style}`}>
                        {badge.label}
                      </span>
                    );
                  })()}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">가입일</label>
                <Input 
                  value={new Date(selectedReferral.joinDate).toLocaleString('ko-KR')} 
                  readOnly 
                  className="mt-1 bg-gray-50" 
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">커미션 비율 (%)</label>
                <div className="flex gap-2 mt-1">
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={commissionRate}
                    onChange={(e) => setCommissionRate(e.target.value)}
                    className="flex-1"
                  />
                  <Button onClick={handleUpdateCommission}>
                    <Edit className="h-4 w-4 mr-2" />
                    저장
                  </Button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  현재 커미션 비율: {commissionRate}% (기본값: 10%)
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailsModal(false)}>
              닫기
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

