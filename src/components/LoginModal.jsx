import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import { X, Mail, Lock, Eye, EyeOff, ArrowRight } from 'lucide-react'
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
          <div className="logo-container">
            <div className="logo">Sociality</div>
          </div>
          <h2 className="login-title">
            <ArrowRight size={24} />
            로그인
          </h2>
          <p className="login-subtitle">Sociality에 오신 것을 환영합니다</p>
        </div>
        
        <div className="login-modal-content">
          <form onSubmit={handleSubmit} className="login-form">
            {error && (
              <div className="error-message">
                {error}
              </div>
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
            
            <button 
              type="submit" 
              className="login-button"
              disabled={loading}
            >
              {loading ? '로그인 중...' : '로그인'}
            </button>
          </form>
          
          <div className="signup-section">
            <span>계정이 없으신가요?</span>
            <Link to="/signup" className="signup-link">
              회원가입
            </Link>
          </div>
        </div>
        
        <button className="close-button" onClick={onClose}>
          <X size={20} />
        </button>
      </div>
    </div>
  )
}

export default LoginModal
