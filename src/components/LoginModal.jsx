import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import { X, Mail, Lock, Eye, EyeOff } from 'lucide-react'
import './LoginModal.css'

const LoginModal = ({ isOpen, onClose }) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [rememberLogin, setRememberLogin] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!email.trim() || !password.trim()) {
      setError('아이디와 비밀번호를 입력해주세요.')
      return
    }

    try {
      setError('')
      setLoading(true)
      
      await login(email, password)
      
      if (rememberLogin) {
        localStorage.setItem('rememberedEmail', email)
      }
      
      onClose()
      navigate('/')
      
    } catch (error) {
      setError('로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.')
    } finally {
      setLoading(false)
    }
  }

  const handleForgotPassword = () => {
    // 비밀번호 찾기 로직
    console.log('비밀번호 찾기')
  }

  if (!isOpen) return null

  return (
    <div className="login-modal-overlay" onClick={onClose}>
      <div className="login-modal" onClick={(e) => e.stopPropagation()}>
        <div className="login-modal-header">
          <h2>로그인</h2>
          <Link to="/signup" className="signup-link">
            아직 회원이 아니신가요? 회원가입하기
          </Link>
        </div>
        
        <div className="login-modal-content">
          <p className="welcome-message">
            SNS샵은 잘 이용하고 계신가요? 오늘도 즐거운 일 가득하시길 바래요.
          </p>
          
          <form onSubmit={handleSubmit} className="login-form">
            {error && (
              <div className="error-message">
                {error}
              </div>
            )}
            
            <div className="form-group">
              <label htmlFor="email">아이디</label>
              <input
                type="text"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="아이디를 입력하세요"
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">비밀번호</label>
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
            
            <button 
              type="submit" 
              className="login-button"
              disabled={loading}
            >
              {loading ? '로그인 중...' : '로그인'}
            </button>
            
            <div className="login-options">
              <label className="remember-login">
                <input
                  type="checkbox"
                  checked={rememberLogin}
                  onChange={(e) => setRememberLogin(e.target.checked)}
                />
                로그인정보 기억하기
              </label>
              <button
                type="button"
                className="forgot-password"
                onClick={handleForgotPassword}
              >
                비밀번호 찾기
              </button>
            </div>
          </form>
        </div>
        
        <button className="close-button" onClick={onClose}>
          <X size={20} />
        </button>
      </div>
    </div>
  )
}

export default LoginModal
