import React, { useState } from 'react'
import { X, LogIn, UserPlus, Mail, Lock, User, Building2, Briefcase } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './AuthModal.css'

const AuthModal = ({ isOpen, onClose, onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [accountType, setAccountType] = useState('personal') // 'personal' or 'business'
  const [businessNumber, setBusinessNumber] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [representative, setRepresentative] = useState('')
  const [contactPhone, setContactPhone] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const { login, signup } = useAuth()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isLogin) {
        await login(email, password)
      } else {
        // 비즈니스 계정일 때 필수 정보 확인
        if (accountType === 'business') {
          if (!businessNumber.trim() || !businessName.trim() || !representative.trim() || !contactPhone.trim() || !contactEmail.trim()) {
            setError('비즈니스 계정의 모든 필수 정보를 입력해주세요.')
            setLoading(false)
            return
          }
        }

        await signup(email, password, displayName, {
          accountType,
          businessNumber: businessNumber.trim(),
          businessName: businessName.trim(),
          representative: representative.trim(),
          contactPhone: contactPhone.trim(),
          contactEmail: contactEmail.trim()
        })
      }
      console.log('Auth successful:', isLogin ? 'login' : 'signup')
      onSuccess()
      onClose()
    } catch (error) {
      console.error('Auth error:', error)
      // Firebase 에러 메시지를 한국어로 변환
      let errorMessage = error.message
      if (error.code === 'auth/user-not-found') {
        errorMessage = '등록되지 않은 이메일입니다.'
      } else if (error.code === 'auth/wrong-password') {
        errorMessage = '비밀번호가 올바르지 않습니다.'
      } else if (error.code === 'auth/invalid-email') {
        errorMessage = '유효하지 않은 이메일 형식입니다.'
      } else if (error.code === 'auth/weak-password') {
        errorMessage = '비밀번호는 최소 6자 이상이어야 합니다.'
      } else if (error.code === 'auth/email-already-in-use') {
        errorMessage = '이미 사용 중인 이메일입니다.'
      } else if (error.code === 'auth/too-many-requests') {
        errorMessage = '너무 많은 로그인 시도가 있었습니다. 잠시 후 다시 시도해주세요.'
      }
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const switchMode = () => {
    setIsLogin(!isLogin)
    setError('')
    setEmail('')
    setPassword('')
    setDisplayName('')
    setAccountType('personal')
    setBusinessNumber('')
    setBusinessName('')
    setRepresentative('')
    setContactPhone('')
    setContactEmail('')
  }

  if (!isOpen) return null

  return (
    <div className="auth-modal-overlay">
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        {/* 로그인하지 않은 상태에서는 닫기 버튼 숨김 */}
        {false && (
          <button className="auth-modal-close" onClick={onClose}>
            <X size={24} />
          </button>
        )}

        <div className="auth-modal-header">
          <div className="auth-modal-icon">
            {isLogin ? <LogIn size={32} /> : <UserPlus size={32} />}
          </div>
          <h2>{isLogin ? '로그인' : '회원가입'}</h2>
          <p>{isLogin ? '계정에 로그인하세요' : '새 계정을 만드세요'}</p>
          {isLogin && (
            <div style={{ 
              background: '#f0f9ff', 
              border: '1px solid #0ea5e9', 
              borderRadius: '8px', 
              padding: '12px', 
              marginTop: '12px',
              fontSize: '12px',
              color: '#0369a1'
            }}>
              <strong>테스트 계정:</strong><br/>
              이메일: test@example.com<br/>
              비밀번호: 123456
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {!isLogin && (
            <>
              {/* 계정 타입 선택 */}
              <div className="form-group">
                <label className="form-label">계정 타입</label>
                <div className="account-type-options">
                  <label className="account-type-option">
                    <input
                      type="radio"
                      name="accountType"
                      value="personal"
                      checked={accountType === 'personal'}
                      onChange={(e) => setAccountType(e.target.value)}
                    />
                    <User size={16} className="account-type-icon" />
                    <span>개인 계정</span>
                  </label>
                  <label className="account-type-option">
                    <input
                      type="radio"
                      name="accountType"
                      value="business"
                      checked={accountType === 'business'}
                      onChange={(e) => setAccountType(e.target.value)}
                    />
                    <Building2 size={16} className="account-type-icon" />
                    <span>비즈니스 계정</span>
                  </label>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="displayName">
                  <User size={16} />
                  이름
                </label>
                <input
                  type="text"
                  id="displayName"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="이름을 입력하세요"
                  required={!isLogin}
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="email">
              <Mail size={16} />
              이메일
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="이메일을 입력하세요"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">
              <Lock size={16} />
              비밀번호
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="비밀번호를 입력하세요"
              required
            />
          </div>

          {/* 비즈니스 계정 정보 */}
          {!isLogin && accountType === 'business' && (
            <div className="business-info-section">
              <h3 className="business-info-title">
                <Briefcase size={16} />
                비즈니스 정보
              </h3>
              
              <div className="form-group">
                <label htmlFor="businessNumber">사업자등록번호</label>
                <input
                  type="text"
                  id="businessNumber"
                  value={businessNumber}
                  onChange={(e) => setBusinessNumber(e.target.value)}
                  placeholder="사업자등록번호를 입력하세요 (예: 123-45-67890)"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="businessName">회사명</label>
                <input
                  type="text"
                  id="businessName"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  placeholder="회사명을 입력하세요"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="representative">대표자</label>
                <input
                  type="text"
                  id="representative"
                  value={representative}
                  onChange={(e) => setRepresentative(e.target.value)}
                  placeholder="대표자명을 입력하세요"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="contactPhone">담당자 연락처</label>
                <input
                  type="tel"
                  id="contactPhone"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  placeholder="담당자 연락처를 입력하세요 (예: 010-1234-5678)"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="contactEmail">담당자 메일주소</label>
                <input
                  type="email"
                  id="contactEmail"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  placeholder="담당자 메일주소를 입력하세요"
                  required
                />
              </div>
            </div>
          )}

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? '처리중...' : (isLogin ? '로그인' : '회원가입')}
          </button>
        </form>

        <div className="auth-modal-footer">
          <p>
            {isLogin ? '계정이 없으신가요?' : '이미 계정이 있으신가요?'}
            <button onClick={switchMode} className="auth-switch-btn">
              {isLogin ? '회원가입' : '로그인'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}

export default AuthModal
