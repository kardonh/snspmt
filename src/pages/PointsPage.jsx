import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import smmpanelApi from '../services/snspopApi'
import { CreditCard, Building2, User, DollarSign, Receipt, FileText, X, Copy, Check } from 'lucide-react'
import './PointsPage.css'

const PointsPage = () => {
  const { currentUser } = useAuth()
  const [userPoints, setUserPoints] = useState(0)
  const [selectedAmount, setSelectedAmount] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [purchaseHistory, setPurchaseHistory] = useState([])
  const [userInfo, setUserInfo] = useState(null)
  const [isKcpLoading, setIsKcpLoading] = useState(false)

  const pointPackages = [
    { amount: 5000, price: 5000 },
    { amount: 10000, price: 10000 },
    { amount: 50000, price: 50000 },
    { amount: 100000, price: 100000 },
    { amount: 500000, price: 500000 },
    { amount: 1000000, price: 1000000 }
  ]

  useEffect(() => {
    if (currentUser) {
      loadUserPoints()
      loadPurchaseHistory()
      loadUserInfo()
    }
  }, [currentUser])


  const loadUserPoints = async () => {
    try {
      const userId = currentUser?.uid || localStorage.getItem('userId') || 'demo_user'
      console.log('🔍 포인트 조회 - 사용자 ID:', userId)
      
      const response = await fetch(`/api/points?user_id=${userId}`)
      if (response.ok) {
        const data = await response.json()
        setUserPoints(data.points || 0)
        console.log('✅ 포인트 조회 성공:', data.points)
      } else {
        console.error('❌ 포인트 조회 실패:', response.status)
      }
    } catch (error) {
      console.error('❌ 포인트 조회 오류:', error)
    }
  }

  const loadPurchaseHistory = async () => {
    try {
      const userId = currentUser?.uid || localStorage.getItem('userId') || 'demo_user'
      console.log('🔍 구매 내역 조회 - 사용자 ID:', userId)
      
      const response = await fetch(`/api/points/purchase-history?user_id=${userId}`)
      if (response.ok) {
        const data = await response.json()
        setPurchaseHistory(data.purchases || [])
        console.log('✅ 구매 내역 조회 성공:', data.purchases)
      } else {
        console.error('❌ 구매 내역 조회 실패:', response.status)
      }
    } catch (error) {
      console.error('❌ 구매 내역 조회 오류:', error)
    }
  }

  const loadUserInfo = async () => {
    try {
              const response = await smmpanelApi.getUserInfo(currentUser.uid)
      console.log('사용자 정보 로드:', response)
      setUserInfo(response.user || null)
    } catch (error) {
      console.error('사용자 정보 조회 실패:', error)
    }
  }



  // KCP 결제 처리
  const handleKcpPayment = async () => {
    if (selectedAmount === 0) {
      alert('포인트 금액을 선택해주세요.')
      return
    }

    setIsKcpLoading(true)
    try {
      // 1단계: KCP 거래등록
      const registerResponse = await fetch('/api/points/purchase-kcp/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: currentUser.uid,
          amount: selectedAmount,
          price: pointPackages.find(pkg => pkg.amount === selectedAmount)?.price || selectedAmount,
          good_name: '포인트 구매',
          pay_method: 'CARD'
        })
      })

      const registerResult = await registerResponse.json()
      
      if (!registerResult.success) {
        throw new Error(registerResult.error || 'KCP 거래등록 실패')
      }

      // 2단계: 결제창 호출 데이터 생성
      const formResponse = await fetch('/api/points/purchase-kcp/payment-form', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ordr_idxx: registerResult.ordr_idxx,
          approval_key: registerResult.kcp_response.approvalKey,
          pay_url: registerResult.kcp_response.PayUrl,
          pay_method: 'CARD',
          good_mny: String(pointPackages.find(pkg => pkg.amount === selectedAmount)?.price || selectedAmount),
          buyr_name: userInfo?.displayName || userInfo?.email || '사용자',
          buyr_mail: userInfo?.email || '',
          buyr_tel2: userInfo?.phoneNumber || '',
          shop_user_id: currentUser.uid
        })
      })

      const formResult = await formResponse.json()
      
      if (!formResult.success) {
        throw new Error(formResult.error || '결제창 데이터 생성 실패')
      }

      // 3단계: KCP 결제창 호출
      const form = document.createElement('form')
      form.method = 'POST'
      form.action = formResult.payment_form_data.PayUrl.substring(0, formResult.payment_form_data.PayUrl.lastIndexOf("/")) + "/jsp/encodingFilter/encodingFilter.jsp"
      form.target = '_blank'
      
      Object.keys(formResult.payment_form_data).forEach(key => {
        const input = document.createElement('input')
        input.type = 'hidden'
        input.name = key
        input.value = formResult.payment_form_data[key]
        form.appendChild(input)
      })
      
      document.body.appendChild(form)
      form.submit()
      document.body.removeChild(form)

      // 폼 초기화
      setSelectedAmount(0)
      loadPurchaseHistory()

    } catch (error) {
      console.error('KCP 결제 실패:', error)
      alert('KCP 결제 중 오류가 발생했습니다: ' + error.message)
    } finally {
      setIsKcpLoading(false)
    }
  }


  const handlePurchase = () => {
    handleKcpPayment()
  }

  const getSelectedPackage = () => {
    const found = pointPackages.find(pkg => pkg.amount === selectedAmount)
    return found || { amount: 0, price: 0 }
  }

  return (
    <div className="points-page">
      <div className="points-header">
        <h1>포인트 구매</h1>
        <div className="current-points">
          <DollarSign size={24} />
          <span>현재 포인트: {userPoints.toLocaleString()}P</span>
        </div>
      </div>

      <div className="points-content">
        {/* 충전금액 선택 */}
        <div className="charge-amount-section">
          <h2>충전금액</h2>
          <div className="amount-display">
            <div className={`amount-input-container ${selectedAmount === 0 ? 'zero-amount' : ''}`}>
              <span className="amount-display-text">
                <span className="amount-number">
                  {selectedAmount === 0 ? '0' : selectedAmount.toLocaleString()}
                </span>
                <span className="amount-unit">원</span>
              </span>
              {selectedAmount > 0 && (
                <button 
                  className="clear-amount-btn"
                  onClick={() => setSelectedAmount(0)}
                  title="금액 초기화"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          </div>
          <div className="amount-buttons-grid">
            {pointPackages.map((pkg) => (
              <button
                key={pkg.amount}
                className="amount-add-btn"
                onClick={() => setSelectedAmount(selectedAmount + pkg.amount)}
              >
                + {pkg.amount >= 10000 ? `${(pkg.amount / 10000).toLocaleString()}만원` : `${pkg.amount.toLocaleString()}원`}
              </button>
            ))}
          </div>
        </div>

        {/* 구매 정보 입력 */}
        <div className="purchase-form">
          <h2>구매 정보 입력</h2>
          
          {/* 결제 방식 - KCP 카드결제만 사용 */}
          <div className="payment-method-section">
            <h3>결제 방식</h3>
            <div className="payment-method-info">
              <div className="selected-payment-method">
                <CreditCard className="payment-method-icon" />
                <span className="payment-method-label">KCP 카드결제 (즉시충전)</span>
                <span className="payment-method-badge">추천</span>
              </div>
              <div className="payment-method-description">
                <p>💳 신용카드로 안전하고 빠른 결제</p>
                <p>⚡ 결제 완료 즉시 포인트 자동 충전</p>
                <p>🔒 KCP 보안 시스템으로 안전한 결제</p>
              </div>
            </div>
          </div>





          <div className="purchase-summary">
            <div className="summary-item">
              <span>선택한 포인트:</span>
              <span>{getSelectedPackage().amount.toLocaleString()}P</span>
            </div>
            <div className="summary-item">
              <span>결제 금액:</span>
              <span>{getSelectedPackage().price.toLocaleString()}원</span>
            </div>
          </div>

          <button
            onClick={handlePurchase}
            disabled={isLoading || isKcpLoading || selectedAmount === 0}
            className="purchase-btn"
          >
            {isLoading ? '처리중...' : isKcpLoading ? 'KCP 결제 준비중...' : 'KCP 카드결제'}
          </button>
        </div>

        {/* 구매 내역 */}
        <div className="purchase-history">
          <h2>구매 내역</h2>
          {purchaseHistory.length === 0 ? (
            <div className="no-history">구매 내역이 없습니다.</div>
          ) : (
            <div className="history-list">
              {purchaseHistory.map((purchase) => (
                <div key={purchase.id} className="history-item">
                  <div className="history-info">
                    <div className="history-amount">{purchase.amount.toLocaleString()}P</div>
                    <div className="history-date">
                      {purchase.createdAt || purchase.created_at || purchase.date ? 
                        new Date(purchase.createdAt || purchase.created_at || purchase.date).toLocaleDateString() : 
                        '날짜 없음'
                      }
                    </div>
                  </div>
                  <div className="history-actions">
                    <div className={`history-status ${purchase.status}`}>
                      {purchase.status === 'pending' && '승인 대기중'}
                      {purchase.status === 'approved' && '승인 완료'}
                      {purchase.status === 'rejected' && '승인 거절'}
                      {purchase.status === 'kcp_registered' && 'KCP 결제 대기중'}
                      {purchase.status === 'kcp_approved' && 'KCP 결제 완료'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>


    </div>
  )
}

export default PointsPage
