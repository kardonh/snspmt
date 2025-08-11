import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { generateReferralCode } from '../services/snspopApi'
import { Copy, Share2, Users, Gift } from 'lucide-react'
import './ReferralPage.css'

const ReferralPage = () => {
  const { currentUser } = useAuth()
  const [referralCode, setReferralCode] = useState('')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (currentUser) {
      generateUserReferralCode()
    }
  }, [currentUser])

  const generateUserReferralCode = async () => {
    try {
      setLoading(true)
      const code = await generateReferralCode(currentUser.uid, currentUser.email)
      setReferralCode(code)
      setError(null)
    } catch (err) {
      setError('추천인 코드를 생성하는데 실패했습니다.')
      console.error('추천인 코드 생성 오류:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateCode = async () => {
    try {
      setGenerating(true)
      const code = await generateReferralCode(currentUser.uid, currentUser.email)
      setReferralCode(code)
      setError(null)
    } catch (err) {
      setError('추천인 코드 생성에 실패했습니다.')
      console.error('추천인 코드 생성 오류:', err)
    } finally {
      setGenerating(false)
    }
  }

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(referralCode)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('클립보드 복사 실패:', err)
    }
  }

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'SNSINTO 추천인 코드',
          text: `SNSINTO에서 ${referralCode} 추천인 코드로 가입하면 5% 할인 쿠폰을 받을 수 있습니다!`,
          url: window.location.origin
        })
      } catch (err) {
        console.error('공유 실패:', err)
      }
    } else {
      // 공유 API가 지원되지 않는 경우 클립보드에 복사
      handleCopyCode()
    }
  }

  if (!currentUser) {
    return (
      <div className="referral-page">
        <div className="referral-container">
          <h1>추천인 코드</h1>
          <p>로그인이 필요합니다.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="referral-page">
        <div className="referral-container">
          <h1>추천인 코드</h1>
          <div className="loading">추천인 코드를 생성하는 중...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="referral-page">
      <div className="referral-container">
        <div className="referral-header">
          <h1>추천인 코드</h1>
          <p>친구를 초대하고 함께 혜택을 받아보세요!</p>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <div className="referral-content">
          <div className="code-section">
            <h2>내 추천인 코드</h2>
            {referralCode ? (
              <div className="code-display">
                <div className="code">{referralCode}</div>
                <div className="code-actions">
                  <button 
                    onClick={handleCopyCode} 
                    className={`copy-btn ${copied ? 'copied' : ''}`}
                  >
                    <Copy size={16} />
                    {copied ? '복사됨!' : '복사'}
                  </button>
                  <button onClick={handleShare} className="share-btn">
                    <Share2 size={16} />
                    공유
                  </button>
                </div>
              </div>
            ) : (
              <div className="no-code">
                <p>아직 추천인 코드가 없습니다.</p>
                <button 
                  onClick={handleGenerateCode} 
                  className="generate-btn"
                  disabled={generating}
                >
                  {generating ? '생성 중...' : '추천인 코드 생성'}
                </button>
              </div>
            )}
          </div>

          <div className="benefits-section">
            <h2>추천인 혜택</h2>
            <div className="benefits-grid">
              <div className="benefit-card">
                <div className="benefit-icon">
                  <Users size={24} />
                </div>
                <h3>신규 사용자</h3>
                <p>추천인 코드로 가입하면 <strong>5% 할인 쿠폰</strong>을 받습니다!</p>
              </div>
              <div className="benefit-card">
                <div className="benefit-icon">
                  <Gift size={24} />
                </div>
                <h3>추천인</h3>
                <p>친구를 초대하면 <strong>15% 할인 쿠폰</strong>을 받습니다!</p>
              </div>
            </div>
          </div>

          <div className="how-to-section">
            <h2>사용 방법</h2>
            <div className="steps">
              <div className="step">
                <div className="step-number">1</div>
                <div className="step-content">
                  <h4>추천인 코드 복사</h4>
                  <p>위의 추천인 코드를 복사하세요</p>
                </div>
              </div>
              <div className="step">
                <div className="step-number">2</div>
                <div className="step-content">
                  <h4>친구에게 공유</h4>
                  <p>친구에게 추천인 코드를 전달하세요</p>
                </div>
              </div>
              <div className="step">
                <div className="step-number">3</div>
                <div className="step-content">
                  <h4>쿠폰 지급</h4>
                  <p>친구가 가입하면 양쪽 모두 쿠폰을 받습니다!</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReferralPage
