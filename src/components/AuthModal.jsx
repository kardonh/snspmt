import React, { useState, useEffect } from 'react'
import { X, LogIn, UserPlus, Mail, Lock, User, Building2, Briefcase, Eye, EyeOff, AlertTriangle, ArrowRight } from 'lucide-react'
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
  const [showPassword, setShowPassword] = useState(false)
  const [loginAttempts, setLoginAttempts] = useState(0)
  const [isLocked, setIsLocked] = useState(false)
  const [lockoutTime, setLockoutTime] = useState(0)
  const [agreeToTerms, setAgreeToTerms] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [signupSource, setSignupSource] = useState('')
  const [referralCode, setReferralCode] = useState('')
  const [referralCodeValid, setReferralCodeValid] = useState(false)
  const [referralCodeError, setReferralCodeError] = useState('')
  
  const { login, signup } = useAuth()

  // 추천인 코드 검증
  const validateReferralCode = async (code) => {
    if (!code.trim()) {
      setReferralCodeValid(false)
      setReferralCodeError('')
      return
    }

    try {
      const response = await fetch(`/api/referral/validate-code?code=${encodeURIComponent(code)}`)
      if (response.ok) {
        const data = await response.json()
        if (data.valid) {
          setReferralCodeValid(true)
          setReferralCodeError('')
        } else {
          setReferralCodeValid(false)
          setReferralCodeError('유효하지 않은 추천인 코드입니다.')
        }
      } else {
        setReferralCodeValid(false)
        setReferralCodeError('추천인 코드를 확인할 수 없습니다.')
      }
    } catch (error) {
      setReferralCodeValid(false)
      setReferralCodeError('추천인 코드 검증 중 오류가 발생했습니다.')
    }
  }

  // 추천인 코드 변경 핸들러
  const handleReferralCodeChange = (e) => {
    const code = e.target.value
    setReferralCode(code)
    if (code.trim()) {
      validateReferralCode(code)
    } else {
      setReferralCodeValid(false)
      setReferralCodeError('')
    }
  }

  // 로그인 시도 제한 확인 (AuthModal용)
  useEffect(() => {
    if (isLogin) {
      const attempts = localStorage.getItem('modalLoginAttempts') || 0;
      const lockoutUntil = localStorage.getItem('modalLockoutUntil') || 0;
      
      const now = Date.now();
      
      if (lockoutUntil > now) {
        setIsLocked(true);
        setLockoutTime(Math.ceil((lockoutUntil - now) / 1000));
      } else if (lockoutUntil > 0 && lockoutUntil <= now) {
        localStorage.removeItem('modalLockoutUntil');
        localStorage.setItem('modalLoginAttempts', '0');
        setIsLocked(false);
        setLoginAttempts(0);
      } else {
        setLoginAttempts(parseInt(attempts));
      }
    }
  }, [isLogin]);

  // 잠금 시간 카운트다운
  useEffect(() => {
    if (isLocked && lockoutTime > 0) {
      const timer = setTimeout(() => {
        setLockoutTime(lockoutTime - 1);
        if (lockoutTime <= 1) {
          setIsLocked(false);
          setLoginAttempts(0);
          localStorage.removeItem('modalLockoutUntil');
          localStorage.setItem('modalLoginAttempts', '0');
        }
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [isLocked, lockoutTime]);

  // 입력 검증
  const validateInputs = () => {
    if (!email.trim()) {
      setError('이메일을 입력해주세요.');
      return false;
    }
    
    if (!email.includes('@') || !email.includes('.')) {
      setError('올바른 이메일 형식을 입력해주세요.');
      return false;
    }
    
    if (!password.trim()) {
      setError('비밀번호를 입력해주세요.');
      return false;
    }
    
    if (password.length < 6) {
      setError('비밀번호는 최소 6자 이상이어야 합니다.');
      return false;
    }
    
    // 회원가입 시 이름 검증
    if (!isLogin && !displayName.trim()) {
      setError('이름을 입력해주세요.');
      return false;
    }
    
    return true;
  };

  // 로그인 시도 제한 관리 (AuthModal용)
  const handleLoginAttempt = (success) => {
    const now = Date.now();
    let attempts = parseInt(localStorage.getItem('modalLoginAttempts') || '0');
    
    if (success) {
      localStorage.removeItem('modalLoginAttempts');
      localStorage.removeItem('modalLockoutUntil');
      setLoginAttempts(0);
      setIsLocked(false);
    } else {
      attempts += 1;
      localStorage.setItem('modalLoginAttempts', attempts.toString());
      setLoginAttempts(attempts);
      
      if (attempts >= 5) {
        const lockoutUntil = now + (15 * 60 * 1000);
        localStorage.setItem('modalLockoutUntil', lockoutUntil.toString());
        setIsLocked(true);
        setLockoutTime(15 * 60);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (isLocked) {
      setError(`로그인이 잠겨있습니다. ${Math.floor(lockoutTime / 60)}분 ${lockoutTime % 60}초 후에 다시 시도해주세요.`);
      return;
    }

    if (!validateInputs()) {
      return;
    }

    setError('')
    setLoading(true)

    try {
      if (isLogin) {
        await login(email, password)
        handleLoginAttempt(true)
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
          contactEmail: contactEmail.trim(),
          signupSource: signupSource,
          referralCode: referralCode.trim()
        })
      }
      console.log('Auth successful:', isLogin ? 'login' : 'signup')
      onSuccess()
      onClose()
    } catch (error) {
      console.error('Auth error:', error)
      
      if (isLogin) {
        handleLoginAttempt(false)
      }
      
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
      
      if (isLogin && loginAttempts >= 4) {
        errorMessage = '로그인 시도가 너무 많습니다. 15분 후에 다시 시도해주세요.';
      } else if (isLogin) {
        errorMessage += ` (${5 - loginAttempts}회 남음)`;
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
    setAgreeToTerms(false)
    setRememberMe(false)
    setSignupSource('')
    setReferralCode('')
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

        <div className="auth-modal-content">
          {/* 모바일용 상단 이미지 섹션 */}
          <div className="auth-modal-image-mobile">
            <img 
              src="/sns_illustration.png" 
              alt="Sociality 로그인"
              className="auth-image-mobile"
            />
          </div>

          {/* 데스크톱용 왼쪽 이미지 섹션 */}
          <div className="auth-modal-image">
            <img 
              src="/sns_illustration.png" 
              alt="Sociality 로그인"
              className="auth-image"
            />
          </div>

          {/* 오른쪽 폼 섹션 */}
          <div className="auth-modal-form">
            <div className="auth-modal-header">
              <div className="header-content">
                <img src="/logo.png" alt="Sociality" className="logo" />
                <h2 className="login-title">
                  {isLogin ? '로그인' : '회원가입'}
                </h2>
              </div>
              {!isLogin && (
                <p className="welcome-message">
                  반가워요! 당신을 SNS마케팅의 놀라운 세계로 초대합니다.
                </p>
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

              {/* 가입경로 선택 */}
              <div className="form-group">
                <label htmlFor="signupSource">
                  <Briefcase size={16} />
                  가입경로
                </label>
                <select
                  id="signupSource"
                  value={signupSource}
                  onChange={(e) => setSignupSource(e.target.value)}
                  required={!isLogin}
                >
                  <option value="">가입경로를 선택하세요</option>
                  <option value="naver">네이버</option>
                  <option value="instagram">인스타그램</option>
                  <option value="google">구글</option>
                  <option value="youtube">유튜브</option>
                  <option value="referral">지인소개</option>
                  <option value="other">기타</option>
                </select>
              </div>

              {/* 추천인 코드 */}
              <div className="form-group">
                <label htmlFor="referralCode">
                  <User size={16} />
                  추천인 코드 (선택사항)
                  {referralCode && referralCodeValid && (
                    <span className="valid-icon">✓</span>
                  )}
                </label>
                <input
                  type="text"
                  id="referralCode"
                  value={referralCode}
                  onChange={handleReferralCodeChange}
                  placeholder="추천인 코드를 입력하세요"
                  className={referralCode ? (referralCodeValid ? 'valid' : 'invalid') : ''}
                />
                {referralCodeError && (
                  <div className="error-message">{referralCodeError}</div>
                )}
                {referralCode && referralCodeValid && (
                  <div className="success-message">유효한 추천인 코드입니다! 5% 할인 쿠폰을 받으실 수 있습니다.</div>
                )}
              </div>

              <div className="signup-form-row">
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
                    placeholder="your@email.com"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="password">
                  <Lock size={16} />
                  비밀번호
                </label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="비밀번호를 입력하세요"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
            </>
          )}

          {isLogin && (
            <div className="login-form-row">
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
                  placeholder="your@email.com"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">
                  <Lock size={16} />
                  비밀번호
                </label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="비밀번호를 입력하세요"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
            </div>
          )}

          {isLogin && (
            <div className="remember-me">
              <label className="remember-checkbox">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span className="checkmark"></span>
                <span className="remember-text">자동 로그인</span>
              </label>
            </div>
          )}

          {/* 비즈니스 계정 정보 */}
          {!isLogin && accountType === 'business' && (
            <div className="business-info-section">
              <h3 className="business-info-title">
                <Briefcase size={16} />
                비즈니스 정보 세금 계산서 발행용
              </h3>
              
              <div className="business-form-row">
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
                  <label htmlFor="businessName">상호명</label>
                  <input
                    type="text"
                    id="businessName"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="상호명을 입력하세요"
                    required
                  />
                </div>
              </div>

              <div className="business-form-row">
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

          {!isLogin && (
            <div className="terms-agreement">
              <label className="terms-checkbox">
                <input
                  type="checkbox"
                  checked={agreeToTerms}
                  onChange={(e) => setAgreeToTerms(e.target.checked)}
                  required
                />
                <span className="checkmark"></span>
                <span className="terms-text">
                  <a href="/terms" target="_blank" className="terms-link">이용약관</a> 및 
                  <a href="/privacy" target="_blank" className="terms-link">개인정보처리방침</a>에 동의합니다
                </span>
              </label>
            </div>
          )}

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-submit" disabled={loading || (!isLogin && !agreeToTerms)}>
            {loading ? '처리중...' : (isLogin ? '로그인' : '회원가입')}
          </button>
        </form>

        {isLogin && (
          <div className="signup-section">
            <span>계정이 없으신가요?</span>
            <button onClick={switchMode} className="signup-link">
              회원가입
            </button>
          </div>
        )}

        {!isLogin && (
          <div className="auth-modal-footer">
            <p>
              이미 계정이 있으신가요?
              <button onClick={switchMode} className="auth-switch-btn">
                로그인
              </button>
            </p>
          </div>
        )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AuthModal
