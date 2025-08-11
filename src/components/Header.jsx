import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { User, LogOut, Copy, Check } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { generateReferralCode } from '../services/snspopApi'
import './Header.css'

const Header = () => {
  const { currentUser, logout } = useAuth()
  const [referralCode, setReferralCode] = useState('')
  const [isCopied, setIsCopied] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  // 사용자의 추천인 코드 가져오기
  useEffect(() => {
    if (currentUser) {
      fetchReferralCode()
    }
  }, [currentUser])

  const fetchReferralCode = async () => {
    if (!currentUser) return
    
    setIsLoading(true)
    try {
      // 백엔드에서 사용자의 추천인 코드를 가져오는 API 호출
      const response = await fetch(`/api/referral/user/${currentUser.email}`)
      if (response.ok) {
        const data = await response.json()
        if (data.referral_code) {
          setReferralCode(data.referral_code)
        } else {
          // 추천인 코드가 없으면 새로 생성
          console.log('추천인 코드가 없습니다. 새로 생성합니다...')
          const generateResponse = await fetch('/api/referral/generate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              user_id: currentUser.uid,
              user_email: currentUser.email
            })
          })
          
          if (generateResponse.ok) {
            const generateData = await generateResponse.json()
            if (generateData.success) {
              console.log('추천인 코드가 생성되었습니다:', generateData.referral_code)
              setReferralCode(generateData.referral_code)
            } else {
              console.error('추천인 코드 생성 실패:', generateData.error || '알 수 없는 오류')
            }
          } else {
            console.error('추천인 코드 생성 API 호출 실패:', generateResponse.status)
          }
        }
      } else {
        console.error('추천인 코드 조회 API 호출 실패')
      }
    } catch (error) {
      console.error('추천인 코드 가져오기 실패:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopyReferralCode = async () => {
    if (!referralCode) return
    
    try {
      await navigator.clipboard.writeText(referralCode)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    } catch (error) {
      console.error('복사 실패:', error)
      // fallback: 텍스트 선택
      const textArea = document.createElement('textarea')
      textArea.value = referralCode
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    }
  }

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      console.error('로그아웃 실패:', error)
    }
  }

  return (
    <header className="header">
      <div className="header-container">
        <Link to="/" className="logo">
          SNSINTO
        </Link>
        <div className="header-right">
          {currentUser ? (
            <div className="user-info">
              <Link to="/orders" className="orders-link">
                주문 내역
              </Link>
              <Link to="/coupons" className="coupons-link">
                내 쿠폰
              </Link>
              <div className="referral-code-section">
                <span className="referral-label">내 추천인 코드:</span>
                {isLoading ? (
                  <span className="referral-loading">로딩중...</span>
                ) : referralCode ? (
                  <div className="referral-code-display">
                    <span className="referral-code">{referralCode}</span>
                    <button 
                      onClick={handleCopyReferralCode}
                      className="copy-referral-btn"
                      title="추천인 코드 복사"
                    >
                      {isCopied ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  </div>
                ) : (
                  <span className="referral-error">코드 없음</span>
                )}
              </div>
              <span className="username">{currentUser.displayName || currentUser.email}</span>
              <button onClick={handleLogout} className="logout-btn">
                <LogOut size={16} />
                <span>로그아웃</span>
              </button>
            </div>
          ) : (
            <Link to="/login" className="member-btn">
              <User size={20} />
              <span>로그인</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header
