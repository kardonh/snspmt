import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, ArrowRight } from 'lucide-react';
import './LoginPage.css';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();

    try {
      setError('');
      setLoading(true);
      await login(email, password);
      navigate('/');
    } catch (error) {
      setError('로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.');
    }
    setLoading(false);
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="logo-container">
            <div className="logo">Sociality</div>
          </div>
          <h2 className="login-title">로그인</h2>
          <p className="login-subtitle">Sociality에 오신 것을 환영합니다</p>
        </div>
        
        {error && (
          <div className="error-message">
            <div className="error-icon">⚠️</div>
            <span>{error}</span>
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
                type="password"
                id="password"
                className="form-input"
                placeholder="비밀번호를 입력하세요"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>
          
          <button 
            disabled={loading} 
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
