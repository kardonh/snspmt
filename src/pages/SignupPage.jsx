import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { User, Mail, Lock, ArrowRight, Building2, Briefcase } from 'lucide-react';
import './SignupPage.css';

export default function SignupPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [accountType, setAccountType] = useState('personal'); // 'personal' or 'business'
  const [businessNumber, setBusinessNumber] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [representative, setRepresentative] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [referralCode, setReferralCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();

    if (password !== confirmPassword) {
      return setError('비밀번호가 일치하지 않습니다.');
    }

    if (password.length < 6) {
      return setError('비밀번호는 최소 6자 이상이어야 합니다.');
    }

    // 비즈니스 계정일 때 필수 정보 확인
    if (accountType === 'business') {
      if (!businessNumber.trim() || !businessName.trim() || !representative.trim() || !contactPhone.trim() || !contactEmail.trim()) {
        return setError('비즈니스 계정의 모든 필수 정보를 입력해주세요.');
      }
    }

    try {
      setError('');
      setLoading(true);
      await signup(email, password, username, {
        accountType,
        businessNumber: businessNumber.trim(),
        businessName: businessName.trim(),
        representative: representative.trim(),
        contactPhone: contactPhone.trim(),
        contactEmail: contactEmail.trim(),
        referralCode: referralCode.trim()
      });
      navigate('/');
    } catch (error) {
      if (error.code === 'auth/email-already-in-use') {
        setError('이미 사용 중인 이메일입니다.');
      } else {
        setError('회원가입에 실패했습니다. 다시 시도해주세요.');
      }
    }
    setLoading(false);
  }

  return (
    <div className="signup-container">
      <div className="signup-card">
        <div className="signup-header">
          <div className="logo-container">
            <div className="logo">Sociality</div>
          </div>
          <h2 className="signup-title">회원가입</h2>
          <p className="signup-subtitle">Sociality 계정을 만들어보세요</p>
        </div>
        
        {error && (
          <div className="error-message">
            <div className="error-icon">⚠️</div>
            <span>{error}</span>
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="signup-form">
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
                <User size={20} className="account-type-icon" />
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
                <Building2 size={20} className="account-type-icon" />
                <span>비즈니스 계정</span>
              </label>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="username" className="form-label">사용자명</label>
            <div className="input-wrapper">
              <User size={20} className="input-icon" />
              <input
                type="text"
                id="username"
                className="form-input"
                placeholder="사용자명을 입력하세요"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
          </div>
          
          <div className="form-group">
            <label htmlFor="email" className="form-label">이메일</label>
            <div className="input-wrapper">
              <Mail size={20} className="input-icon" />
              <input
                type="email"
                id="email"
                className="form-input"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>
          
          <div className="form-group">
            <label htmlFor="password" className="form-label">비밀번호</label>
            <div className="input-wrapper">
              <Lock size={20} className="input-icon" />
              <input
                type="password"
                id="password"
                className="form-input"
                placeholder="비밀번호를 입력하세요 (최소 6자)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>
          
          <div className="form-group">
            <label htmlFor="confirmPassword" className="form-label">비밀번호 확인</label>
            <div className="input-wrapper">
              <Lock size={20} className="input-icon" />
              <input
                type="password"
                id="confirmPassword"
                className="form-input"
                placeholder="비밀번호를 다시 입력하세요"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
          </div>

          {/* 비즈니스 계정 정보 */}
          {accountType === 'business' && (
            <div className="business-info-section">
              <h3 className="business-info-title">
                <Briefcase size={20} />
                비즈니스 정보
              </h3>
              
              <div className="form-group">
                <label htmlFor="businessNumber" className="form-label">사업자등록번호</label>
                <div className="input-wrapper">
                  <Building2 size={20} className="input-icon" />
                  <input
                    type="text"
                    id="businessNumber"
                    className="form-input"
                    placeholder="사업자등록번호를 입력하세요 (예: 123-45-67890)"
                    value={businessNumber}
                    onChange={(e) => setBusinessNumber(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="businessName" className="form-label">회사명</label>
                <div className="input-wrapper">
                  <Building2 size={20} className="input-icon" />
                  <input
                    type="text"
                    id="businessName"
                    className="form-input"
                    placeholder="회사명을 입력하세요"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="representative" className="form-label">대표자</label>
                <div className="input-wrapper">
                  <User size={20} className="input-icon" />
                  <input
                    type="text"
                    id="representative"
                    className="form-input"
                    placeholder="대표자명을 입력하세요"
                    value={representative}
                    onChange={(e) => setRepresentative(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="contactPhone" className="form-label">담당자 연락처</label>
                <div className="input-wrapper">
                  <User size={20} className="input-icon" />
                  <input
                    type="tel"
                    id="contactPhone"
                    className="form-input"
                    placeholder="담당자 연락처를 입력하세요 (예: 010-1234-5678)"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="contactEmail" className="form-label">담당자 메일주소</label>
                <div className="input-wrapper">
                  <Mail size={20} className="input-icon" />
                  <input
                    type="email"
                    id="contactEmail"
                    className="form-input"
                    placeholder="담당자 메일주소를 입력하세요"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>
          )}

          {/* 추천인 코드 입력 */}
          <div className="form-group">
            <label htmlFor="referralCode" className="form-label">
              추천인 코드 (선택사항)
            </label>
            <div className="input-wrapper">
              <User size={20} className="input-icon" />
              <input
                type="text"
                id="referralCode"
                className="form-input"
                placeholder="추천인 코드를 입력하세요"
                value={referralCode}
                onChange={(e) => setReferralCode(e.target.value.toUpperCase())}
              />
            </div>
            <p className="form-help">
              추천인 코드가 있으시면 입력해주세요. 추천인에게 15% 커미션이 지급됩니다.
            </p>
          </div>
          
          <button 
            disabled={loading} 
            type="submit" 
            className="btn btn-primary signup-button"
          >
            {loading ? (
              <div className="loading-spinner"></div>
            ) : (
              <>
                회원가입
                <ArrowRight size={20} />
              </>
            )}
          </button>
        </form>
        
        <div className="login-link">
          <span>이미 계정이 있으신가요?</span>
          <Link to="/login" className="login-button">
            로그인
          </Link>
        </div>
      </div>
    </div>
  );
}
