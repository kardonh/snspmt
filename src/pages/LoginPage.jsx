import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useGuest } from '../contexts/GuestContext';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, ArrowRight, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import './LoginPage.css';

// Force cache refresh - Updated login page with Sociality logo
export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loginAttempts, setLoginAttempts] = useState(0);
  const [isLocked, setIsLocked] = useState(false);
  const [lockoutTime, setLockoutTime] = useState(0);
  const { login } = useAuth();
  const { isGuest, guestData } = useGuest();
  const navigate = useNavigate();

  // 로그인 시도 제한 확인
  useEffect(() => {
    const attempts = localStorage.getItem('loginAttempts') || 0;
    const lastAttempt = localStorage.getItem('lastLoginAttempt') || 0;
    const lockoutUntil = localStorage.getItem('lockoutUntil') || 0;
    
    const now = Date.now();
    
    if (lockoutUntil > now) {
      setIsLocked(true);
      setLockoutTime(Math.ceil((lockoutUntil - now) / 1000));
    } else if (lockoutUntil > 0 && lockoutUntil <= now) {
      // 잠금 해제
      localStorage.removeItem('lockoutUntil');
      localStorage.setItem('loginAttempts', '0');
      setIsLocked(false);
      setLoginAttempts(0);
    } else {
      setLoginAttempts(parseInt(attempts));
    }
  }, []);

  // 잠금 시간 카운트다운
  useEffect(() => {
    if (isLocked && lockoutTime > 0) {
      const timer = setTimeout(() => {
        setLockoutTime(lockoutTime - 1);
        if (lockoutTime <= 1) {
          setIsLocked(false);
          setLoginAttempts(0);
          localStorage.removeItem('lockoutUntil');
          localStorage.setItem('loginAttempts', '0');
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
    
    return true;
  };

  // 로그인 시도 제한 관리
  const handleLoginAttempt = (success) => {
    const now = Date.now();
    let attempts = parseInt(localStorage.getItem('loginAttempts') || '0');
    
    if (success) {
      // 로그인 성공 시 초기화
      localStorage.removeItem('loginAttempts');
      localStorage.removeItem('lastLoginAttempt');
      localStorage.removeItem('lockoutUntil');
      setLoginAttempts(0);
      setIsLocked(false);
    } else {
      // 로그인 실패 시 카운트 증가
      attempts += 1;
      localStorage.setItem('loginAttempts', attempts.toString());
      localStorage.setItem('lastLoginAttempt', now.toString());
      setLoginAttempts(attempts);
      
      // 5회 실패 시 15분 잠금
      if (attempts >= 5) {
        const lockoutUntil = now + (15 * 60 * 1000); // 15분
        localStorage.setItem('lockoutUntil', lockoutUntil.toString());
        setIsLocked(true);
        setLockoutTime(15 * 60);
      }
    }
  };

  async function handleSubmit(e) {
    e.preventDefault();

    if (isLocked) {
      setError(`로그인이 잠겨있습니다. ${Math.floor(lockoutTime / 60)}분 ${lockoutTime % 60}초 후에 다시 시도해주세요.`);
      return;
    }

    if (!validateInputs()) {
      return;
    }

    try {
      setError('');
      setLoading(true);
      
      // 로그인 시도
      await login(email, password);
      
      // 성공 시 처리
      handleLoginAttempt(true);
      
      // 로그인 성공 - 게스트 모드는 자동으로 비활성화됨
      
      navigate('/');
      
    } catch (error) {
      // 실패 시 처리
      handleLoginAttempt(false);
      
      if (loginAttempts >= 4) {
        setError('로그인 시도가 너무 많습니다. 15분 후에 다시 시도해주세요.');
      } else {
        setError(`로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요. (${5 - loginAttempts}회 남음)`);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="logo-container">
            <div className="logo">Sociality</div>
          </div>
          <h2 className="login-title">
            <ArrowRight size={24} />
            로그인
          </h2>
          <p className="login-subtitle">Sociality에 오신 것을 환영합니다</p>
        </div>
        
        {error && (
          <div className="error-message">
            <div className="error-icon">⚠️</div>
            <span>{error}</span>
          </div>
        )}

        {isLocked && (
          <div className="lockout-message">
            <div className="lockout-icon">🔒</div>
            <div className="lockout-content">
              <strong>로그인이 잠겨있습니다</strong>
              <p>보안을 위해 로그인이 일시적으로 잠겨있습니다.</p>
              <div className="lockout-timer">
                {Math.floor(lockoutTime / 60)}분 {lockoutTime % 60}초 후에 다시 시도해주세요.
              </div>
            </div>
          </div>
        )}

        {loginAttempts > 0 && !isLocked && (
          <div className="attempt-warning">
            <AlertTriangle size={16} />
            <span>로그인 시도: {loginAttempts}/5 (5회 실패 시 15분 잠금)</span>
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="login-form">
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
                type={showPassword ? "text" : "password"}
                id="password"
                className="form-input"
                placeholder="비밀번호를 입력하세요"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLocked}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isLocked}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
          
          <button 
            disabled={loading || isLocked} 
            type="submit" 
            className="btn btn-primary login-button"
          >
            {loading ? (
              <div className="loading-spinner"></div>
            ) : (
              <>
                로그인
                <ArrowRight size={20} />
              </>
            )}
          </button>
        </form>
        
        <div className="signup-link">
          <span>계정이 없으신가요?</span>
          <Link to="/signup" className="signup-button">
            회원가입
          </Link>
        </div>
      </div>
    </div>
  );
}
