import React, { useState, useEffect } from 'react'
import { X, LogIn, UserPlus, Mail, Lock, User, Building2, Briefcase, Eye, EyeOff, AlertTriangle, ArrowRight } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import kakaoAuth from '../utils/kakaoAuth'
import './AuthModal.css'

const AuthModal = ({ isOpen, onClose, onSuccess, initialMode = 'login' }) => {
  const [isLogin, setIsLogin] = useState(initialMode === 'login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [accountType, setAccountType] = useState('personal') // 'personal' or 'business'
  const [phoneNumber, setPhoneNumber] = useState('') // 개인 계정용 전화번호
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
  const [referralCodeValidating, setReferralCodeValidating] = useState(false)
  const [autoLogin, setAutoLogin] = useState(false)
  
  const { login, signup, kakaoLogin, googleLogin } = useAuth()

  // initialMode가 변경될 때 isLogin 상태 업데이트
  useEffect(() => {
    setIsLogin(initialMode === 'login')
  }, [initialMode])

  // 추천인 코드 검증
  const validateReferralCode = async (code) => {
    if (!code.trim()) {
      setReferralCodeValid(false)
      setReferralCodeError('')
      return
    }

    setReferralCodeValidating(true)
    setReferralCodeError('')

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
    } finally {
      setReferralCodeValidating(false)
    }
  }

  // URL 파라미터에서 추천인 코드 읽기 (자동 검증 없이 입력 필드에만 채움)
  useEffect(() => {
    if (isOpen && !isLogin) {
      // URL 파라미터에서 추천인 코드 읽기 (ref 또는 referral)
      const urlParams = new URLSearchParams(window.location.search)
      const refCode = urlParams.get('ref') || urlParams.get('referral')
      
      if (refCode) {
        console.log('🔗 추천인 링크에서 코드 감지:', refCode)
        setReferralCode(refCode)
        // 검증은 사용자가 확인 버튼을 눌렀을 때만 수행
      }
    }
  }, [isOpen, isLogin])

  // 모바일에서 모달이 열릴 때 body 스크롤 방지
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
      document.body.style.position = 'fixed'
      document.body.style.width = '100%'
    } else {
      document.body.style.overflow = ''
      document.body.style.position = ''
      document.body.style.width = ''
    }

    return () => {
      document.body.style.overflow = ''
      document.body.style.position = ''
      document.body.style.width = ''
    }
  }, [isOpen])

  // 비즈니스 정보가 입력될 때 세금계산서 필드에 자동 입력
  useEffect(() => {
    if (accountType === 'business' && businessNumber && businessName && representative && contactPhone && contactEmail) {
      // 비즈니스 정보가 모두 입력되면 세금계산서 필드에 자동으로 채우기
      // 이 부분은 실제 세금계산서 입력 필드가 있을 때 구현
    }
  }, [accountType, businessNumber, businessName, representative, contactPhone, contactEmail])

  // 추천인 코드 변경 핸들러
  const handleReferralCodeChange = (e) => {
    const code = e.target.value
    setReferralCode(code)
    // 입력이 변경되면 검증 상태 초기화
    if (code.trim() !== referralCode.trim()) {
      setReferralCodeValid(false)
      setReferralCodeError('')
    }
  }

  // 추천인 코드 확인 버튼 핸들러
  const handleValidateReferralCode = () => {
    if (referralCode.trim()) {
      validateReferralCode(referralCode)
    } else {
      setReferralCodeError('추천인 코드를 입력해주세요.')
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
    
    // 회원가입 시 전화번호 검증
    if (!isLogin && !phoneNumber.trim()) {
      setError('전화번호를 입력해주세요.');
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

  // 카카오 로그인 처리
  const handleKakaoLogin = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('카카오 로그인 시작...');
      const result = await kakaoAuth.login();
      
      if (result && result.success) {
        console.log('카카오 로그인 리다이렉트 시작:', result.message);
        // 리다이렉트가 시작되므로 로딩 상태 유지
        return;
      }
    } catch (error) {
      console.error('카카오 로그인 오류:', error);
      
      // 구체적인 오류 메시지 제공
      let errorMessage = '카카오 로그인 중 오류가 발생했습니다.';
      
      if (error.message.includes('SDK') || error.message.includes('로딩')) {
        errorMessage = '카카오 SDK 로딩에 실패했습니다. 페이지를 새로고침해주세요.';
      } else if (error.message.includes('앱 키')) {
        errorMessage = '카카오 앱 설정에 문제가 있습니다. 관리자에게 문의해주세요.';
      } else if (error.message.includes('네트워크')) {
        errorMessage = '네트워크 연결을 확인해주세요.';
      } else if (error.message.includes('취소')) {
        errorMessage = '카카오 로그인이 취소되었습니다.';
      }
      
      setError(errorMessage);
      setLoading(false);
    }
  };

  // 구글 로그인 처리 (AuthContext의 googleLogin 사용)
  const handleGoogleLogin = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('구글 로그인 시작...');
      const user = await googleLogin();
      console.log('로그인 성공:', user);
      
      // 로그인 성공
      onSuccess && onSuccess(user);
      onClose();
    } catch (error) {
      console.error('구글 로그인 오류:', error);
      setError(error.message);
    } finally {
      setLoading(false);
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
          phoneNumber: phoneNumber.trim(),
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
    setPhoneNumber('')
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
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        {/* 닫기 버튼 활성화 */}
        <button className="auth-modal-close" onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}>
          <X size={24} />
        </button>

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
                <img 
                  src="/logo.png" 
                  alt="Sociality" 
                  className="logo" 
                  onClick={() => window.location.href = '/'}
                  style={{ cursor: 'pointer' }}
                />
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
                    <span>비즈니스 계정</span>
                  </label>
                </div>
              </div>

              {/* 가입경로 선택 */}
              <div className="form-group">
                <label htmlFor="signupSource">
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
                  추천인 코드 (선택사항)
                  {referralCode && referralCodeValid && (
                    <span className="valid-icon">✓</span>
                  )}
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    id="referralCode"
                    value={referralCode}
                    onChange={handleReferralCodeChange}
                    placeholder="추천인 코드를 입력하세요"
                    className={referralCode ? (referralCodeValid ? 'valid' : 'invalid') : ''}
                    style={{ flex: 1 }}
                  />
                  <button
                    type="button"
                    onClick={handleValidateReferralCode}
                    disabled={referralCodeValidating || !referralCode.trim()}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: referralCodeValidating ? '#ccc' : '#007bff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: referralCodeValidating || !referralCode.trim() ? 'not-allowed' : 'pointer',
                      whiteSpace: 'nowrap',
                      fontSize: '14px'
                    }}
                  >
                    {referralCodeValidating ? '확인중...' : '확인'}
                  </button>
                </div>
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
                  <label htmlFor="phoneNumber">
                    전화번호
                  </label>
                  <input
                    type="tel"
                    id="phoneNumber"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="전화번호를 입력하세요 (예: 010-1234-5678)"
                    required={!isLogin}
                  />
                </div>
              </div>

              <div className="signup-form-row">
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

              {/* 자동 로그인 체크박스 */}
              <div className="auto-login-section">
                <label className="auto-login-checkbox">
                  <input
                    type="checkbox"
                    checked={autoLogin}
                    onChange={(e) => setAutoLogin(e.target.checked)}
                  />
                  <span className="checkmark"></span>
                  <span className="auto-login-text">자동 로그인</span>
                </label>
              </div>
            </>
          )}

          {isLogin && (
            <div className="login-form-row">
              <div className="form-group">
                <label htmlFor="email">
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
                  <a href="https://drive.google.com/file/d/1Nn3ABQFUbRSUpD25IAdyJrfjBbDn70Ji/view?usp=sharing" target="_blank" className="terms-link">이용약관</a> 및 
                  <a href="https://drive.google.com/file/d/1PWCtiDv_tFrP2EyNVaQw4CY-pi0K5Hrc/view?usp=sharing" target="_blank" className="terms-link">개인정보처리방침</a>에 동의합니다
                </span>
              </label>
            </div>
          )}

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-submit" disabled={loading || (!isLogin && !agreeToTerms)}>
            {loading ? '처리중...' : (isLogin ? '로그인' : '회원가입')}
          </button>
        </form>

        {/* 소셜 로그인 버튼들 */}
        <div className="social-login-section">
          {/* 구글 로그인 버튼 */}
          <button
            type="button"
            className="google-login-btn"
            onClick={handleGoogleLogin}
            disabled={loading}
          >
            <img 
              src="https://developers.google.com/identity/images/g-logo.png" 
              alt="구글" 
              className="google-icon"
            />
            구글
          </button>

          {/* 카카오 로그인 버튼 */}
          <button
            type="button"
            className="kakao-login-btn"
            onClick={handleKakaoLogin}
            disabled={loading}
          >
            <img 
              src="/images/kakao-talk-simple.png" 
              alt="카카오" 
              className="kakao-icon"
            />
            카카오
          </button>
        </div>

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
