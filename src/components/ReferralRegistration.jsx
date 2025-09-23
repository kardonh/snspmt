import React, { useState } from 'react'
import { X, UserPlus, Mail, CheckCircle } from 'lucide-react'
import './ReferralRegistration.css'

const ReferralRegistration = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    email: '',
    referralCode: '',
    name: '',
    phone: ''
  })
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const generateReferralCode = () => {
    const code = 'REF' + Math.random().toString(36).substr(2, 8).toUpperCase()
    setFormData(prev => ({
      ...prev,
      referralCode: code
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      // 이메일 유효성 검사
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(formData.email)) {
        throw new Error('올바른 이메일 주소를 입력해주세요.')
      }

      // 추천인 코드가 없으면 자동 생성
      if (!formData.referralCode) {
        generateReferralCode()
      }

      // 임시로 프론트엔드에서만 처리 (백엔드 연동 전까지)
      const result = {
        id: Date.now(),
        email: formData.email,
        referralCode: formData.referralCode || 'REF' + Math.random().toString(36).substr(2, 8).toUpperCase(),
        name: formData.name || '',
        phone: formData.phone || '',
        registeredBy: 'admin',
        createdAt: new Date().toISOString()
      }

      // 성공 상태로 설정
      setSuccess(true)
      
      // 성공 콜백 호출
      if (onSuccess) {
        onSuccess(result)
      }

      // 폼 초기화
      setFormData({
        email: '',
        referralCode: '',
        name: '',
        phone: ''
      })

      // 2초 후 모달 닫기
      setTimeout(() => {
        onClose()
      }, 2000)

    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const getAuthToken = async () => {
    // 실제로는 현재 사용자의 토큰을 가져와야 함
    return 'admin-token'
  }

  if (success) {
    return (
      <div className="referral-registration-modal">
        <div className="modal-overlay" onClick={onClose}></div>
        <div className="modal-content success-modal">
          <div className="success-icon">
            <CheckCircle size={48} color="#28a745" />
          </div>
          <h2>추천인 등록 완료!</h2>
          <p>이메일: {formData.email}</p>
          <p>추천인 코드: {formData.referralCode}</p>
          <p>추천인이 성공적으로 등록되었습니다.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="referral-registration-modal">
      <div className="modal-overlay" onClick={onClose}></div>
      <div className="modal-content">
        <div className="modal-header">
          <h2>
            <UserPlus size={24} />
            추천인 등록
          </h2>
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="referral-form">
          <div className="form-group">
            <label htmlFor="email">
              <Mail size={16} />
              이메일 주소 *
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="example@email.com"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="referralCode">
              추천인 코드
            </label>
            <div className="code-input-group">
              <input
                type="text"
                id="referralCode"
                name="referralCode"
                value={formData.referralCode}
                onChange={handleInputChange}
                placeholder="자동 생성됩니다"
                readOnly
              />
              <button
                type="button"
                className="generate-btn"
                onClick={generateReferralCode}
              >
                생성
              </button>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="name">
              이름 (선택사항)
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              placeholder="추천인 이름"
            />
          </div>

          <div className="form-group">
            <label htmlFor="phone">
              전화번호 (선택사항)
            </label>
            <input
              type="tel"
              id="phone"
              name="phone"
              value={formData.phone}
              onChange={handleInputChange}
              placeholder="010-1234-5678"
            />
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <div className="form-actions">
            <button
              type="button"
              className="cancel-btn"
              onClick={onClose}
              disabled={isLoading}
            >
              취소
            </button>
            <button
              type="submit"
              className="submit-btn"
              disabled={isLoading}
            >
              {isLoading ? '등록 중...' : '추천인 등록'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ReferralRegistration
