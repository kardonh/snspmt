import React, { useState, useEffect } from 'react'
import { Edit, X, Save, Search, AlertTriangle } from 'lucide-react'
import './AdminUserManagement.css'

const AdminUserManagement = ({ adminFetch }) => {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  
  // 모달 상태
  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  
  // 폼 상태
  const [userForm, setUserForm] = useState({
    username: '',
    display_name: '',
    email: '',
    referral_code: '',
    is_active: true,
    balance: 0,
    password: ''
  })
  
  // 모달 타입 (edit, delete, password, balance)
  const [modalType, setModalType] = useState('edit')

  // 사용자 목록 로드
  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await adminFetch('/api/admin/users')
      if (!response.ok) {
        throw new Error('사용자 목록을 불러오는데 실패했습니다.')
      }
      const data = await response.json()
      setUsers(data.users || [])
    } catch (e) {
      console.error('사용자 목록 로드 오류:', e)
      setError(e.message || '사용자 목록을 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const openEditModal = (user, type = 'edit') => {
    setEditingUser(user)
    setModalType(type)
    setUserForm({
      username: user.username || '',
      display_name: user.display_name || '',
      email: user.email || '',
      referral_code: user.referral_code || '',
      is_active: user.is_active !== undefined ? user.is_active : true,
      balance: user.balance || 0,
      password: ''
    })
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingUser(null)
    setError(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)

      if (modalType === 'delete') {
        if (!confirm(`정말로 사용자 "${editingUser.email || editingUser.username}"를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
          setLoading(false)
          return
        }
        
        const response = await adminFetch(`/api/admin/users/${editingUser.user_id}`, {
          method: 'DELETE'
        })

        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || '사용자 삭제에 실패했습니다.')
        }

        alert('사용자가 성공적으로 삭제되었습니다.')
        closeModal()
        loadUsers()
        return
      }

      let requestBody = {}
      
      if (modalType === 'password') {
        if (!userForm.password || userForm.password.length < 6) {
          throw new Error('비밀번호는 최소 6자 이상이어야 합니다.')
        }
        requestBody = { password: userForm.password }
      } else if (modalType === 'balance') {
        const balance = parseFloat(userForm.balance)
        if (isNaN(balance) || balance < 0) {
          throw new Error('올바른 포인트 값을 입력해주세요.')
        }
        requestBody = { balance: balance }
      } else {
        // 일반 수정
        requestBody = {
          username: userForm.username,
          display_name: userForm.display_name,
          email: userForm.email,
          referral_code: userForm.referral_code,
          is_active: userForm.is_active
        }
      }

      const response = await adminFetch(`/api/admin/users/${editingUser.user_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || '사용자 정보 수정에 실패했습니다.')
      }

      alert(`사용자 ${modalType === 'password' ? '비밀번호' : modalType === 'balance' ? '포인트' : '정보'}가 성공적으로 수정되었습니다.`)
      closeModal()
      loadUsers()
    } catch (e) {
      console.error('사용자 수정 오류:', e)
      setError(e.message || '사용자 정보 수정에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }
  
  const handleDeleteUser = (user) => {
    openEditModal(user, 'delete')
  }
  
  const handleChangePassword = (user) => {
    openEditModal(user, 'password')
  }
  
  const handleChangeBalance = (user) => {
    openEditModal(user, 'balance')
  }

  const handleFormChange = (e) => {
    const { name, value, type, checked } = e.target
    setUserForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  // 검색 필터링
  const filteredUsers = users.filter(user => {
    const searchLower = searchTerm.toLowerCase()
    return (
      (user.email && user.email.toLowerCase().includes(searchLower)) ||
      (user.username && user.username.toLowerCase().includes(searchLower)) ||
      (user.display_name && user.display_name.toLowerCase().includes(searchLower)) ||
      (user.referral_code && user.referral_code.toLowerCase().includes(searchLower))
    )
  })

  return (
    <div className="admin-user-management">
      <div className="user-header">
        <h2>사용자 관리</h2>
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="이메일, 이름, 추천인 코드로 검색..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <div className="error-message">
          <AlertTriangle size={20} /> {error}
        </div>
      )}

      {loading && !users.length ? (
        <div className="loading-message">로딩 중...</div>
      ) : (
        <div className="user-list">
          {filteredUsers.length === 0 ? (
            <div className="empty-state">
              {searchTerm ? '검색 결과가 없습니다.' : '등록된 사용자가 없습니다.'}
            </div>
          ) : (
            filteredUsers.map(user => (
              <div key={user.user_id} className="user-card">
                <div className="user-info">
                  <div className="user-main-info">
                    <h3>{user.display_name || user.username || '이름 없음'}</h3>
                    <span className="user-email">{user.email || '이메일 없음'}</span>
                  </div>
                  <div className="user-details">
                    <div className="detail-item">
                      <span className="detail-label">사용자 ID:</span>
                      <span className="detail-value">{user.user_id}</span>
                    </div>
                    {user.username && (
                      <div className="detail-item">
                        <span className="detail-label">사용자명:</span>
                        <span className="detail-value">{user.username}</span>
                      </div>
                    )}
                    {user.referral_code && (
                      <div className="detail-item">
                        <span className="detail-label">추천인 코드:</span>
                        <span className="detail-value">{user.referral_code}</span>
                      </div>
                    )}
                    <div className="detail-item">
                      <span className="detail-label">포인트:</span>
                      <span className="detail-value">{parseFloat(user.balance || 0).toLocaleString()}원</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">상태:</span>
                      <span className={`detail-value status ${user.is_active ? 'active' : 'inactive'}`}>
                        {user.is_active ? '활성' : '비활성'}
                      </span>
                    </div>
                    {user.created_at && (
                      <div className="detail-item">
                        <span className="detail-label">가입일:</span>
                        <span className="detail-value">
                          {new Date(user.created_at).toLocaleDateString('ko-KR')}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="user-actions">
                  <button
                    className="btn-icon"
                    onClick={() => openEditModal(user, 'edit')}
                    title="수정"
                  >
                    <Edit size={18} />
                  </button>
                  <button
                    className="btn-icon btn-danger"
                    onClick={() => handleDeleteUser(user)}
                    title="삭제"
                  >
                    <X size={18} />
                  </button>
                  <button
                    className="btn-icon btn-warning"
                    onClick={() => handleChangePassword(user)}
                    title="비밀번호 수정"
                  >
                    🔒
                  </button>
                  <button
                    className="btn-icon btn-info"
                    onClick={() => handleChangeBalance(user)}
                    title="포인트 수정"
                  >
                    💰
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>
                {modalType === 'delete' ? '사용자 삭제' :
                 modalType === 'password' ? '비밀번호 수정' :
                 modalType === 'balance' ? '포인트 수정' :
                 '사용자 정보 수정'}
              </h2>
              <button className="btn-icon" onClick={closeModal}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              {modalType === 'delete' ? (
                <div className="delete-confirmation">
                  <p>정말로 사용자 <strong>{editingUser?.email || editingUser?.username}</strong>를 삭제하시겠습니까?</p>
                  <p className="warning-text">⚠️ 이 작업은 되돌릴 수 없습니다.</p>
                </div>
              ) : modalType === 'password' ? (
                <div className="form-group">
                  <label>새 비밀번호</label>
                  <input
                    type="password"
                    name="password"
                    value={userForm.password}
                    onChange={handleFormChange}
                    placeholder="최소 6자 이상"
                    required
                  />
                </div>
              ) : modalType === 'balance' ? (
                <div className="form-group">
                  <label>포인트</label>
                  <input
                    type="number"
                    name="balance"
                    value={userForm.balance}
                    onChange={handleFormChange}
                    placeholder="포인트"
                    min="0"
                    step="1"
                    required
                  />
                  <p className="form-hint">현재 포인트: {parseFloat(editingUser?.balance || 0).toLocaleString()}원</p>
                </div>
              ) : (
                <>
                  <div className="form-group">
                    <label>사용자명</label>
                    <input
                      type="text"
                      name="username"
                      value={userForm.username}
                      onChange={handleFormChange}
                      placeholder="사용자명"
                    />
                  </div>
                  <div className="form-group">
                    <label>표시 이름</label>
                    <input
                      type="text"
                      name="display_name"
                      value={userForm.display_name}
                      onChange={handleFormChange}
                      placeholder="표시 이름"
                    />
                  </div>
                  <div className="form-group">
                    <label>이메일</label>
                    <input
                      type="email"
                      name="email"
                      value={userForm.email}
                      onChange={handleFormChange}
                      placeholder="이메일"
                    />
                  </div>
                  <div className="form-group">
                    <label>추천인 코드</label>
                    <input
                      type="text"
                      name="referral_code"
                      value={userForm.referral_code}
                      onChange={handleFormChange}
                      placeholder="추천인 코드"
                    />
                  </div>
                  <div className="form-group">
                    <label>
                      <input
                        type="checkbox"
                        name="is_active"
                        checked={userForm.is_active}
                        onChange={handleFormChange}
                      />
                      활성화
                    </label>
                  </div>
                </>
              )}
              {error && <p className="form-error">{error}</p>}
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={closeModal}>
                  <X size={20} /> 취소
                </button>
                <button 
                  type="submit" 
                  className={modalType === 'delete' ? 'btn-danger' : 'btn-primary'} 
                  disabled={loading}
                >
                  {modalType === 'delete' ? (
                    <>
                      <X size={20} /> 삭제
                    </>
                  ) : (
                    <>
                      <Save size={20} /> 저장
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminUserManagement
