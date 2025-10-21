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
  const [paymentMethod, setPaymentMethod] = useState('kcp') // 'kcp' 또는 'manual'
  const [buyerName, setBuyerName] = useState('')
  const [bankInfo, setBankInfo] = useState('')
  const [depositorName, setDepositorName] = useState('')
  const [receiptType, setReceiptType] = useState('none')
  const [companyName, setCompanyName] = useState('')
  const [companyNumber, setCompanyNumber] = useState('')
  const [cashReceiptNumber, setCashReceiptNumber] = useState('')
  const [showAccountModal, setShowAccountModal] = useState(false)

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

      let registerResult
      try {
        registerResult = await registerResponse.json()
      } catch (jsonErr) {
        console.error('JSON 파싱 실패:', jsonErr)
        console.error('응답 상태:', registerResponse.status)
        console.error('응답 텍스트:', await registerResponse.text())
        throw new Error('서버 응답 형식 오류가 발생했습니다.')
      }
      
      if (!registerResult.success) {
        console.error('KCP 거래등록 실패 응답:', registerResult)
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

      let formResult
      try {
        formResult = await formResponse.json()
      } catch (jsonErr) {
        console.error('결제창 데이터 JSON 파싱 실패:', jsonErr)
        console.error('응답 상태:', formResponse.status)
        console.error('응답 텍스트:', await formResponse.text())
        throw new Error('결제창 데이터 생성 중 서버 오류가 발생했습니다.')
      }
      
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
    if (paymentMethod === 'kcp') {
      handleKcpPayment()
    } else {
      handleManualPurchase()
    }
  }

  const handleManualPurchase = async () => {
    if (!selectedAmount || selectedAmount <= 0) {
      alert('포인트 금액을 선택해주세요.')
      return
    }

    if (!buyerName.trim()) {
      alert('입금자명을 입력해주세요.')
      return
    }

    if (!bankInfo.trim()) {
      alert('계좌 정보를 입력해주세요.')
      return
    }

    setIsLoading(true)
    try {
      console.log('🔍 수동 포인트 구매 신청 - 금액:', selectedAmount)
      
      const response = await fetch('/api/points/purchase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: currentUser?.uid || localStorage.getItem('userId') || 'demo_user',
          amount: selectedAmount,
          price: selectedAmount,
          buyer_name: buyerName,
          bank_info: bankInfo
        })
      })

      const data = await response.json()
      console.log('🔍 수동 구매 신청 응답:', data)

      if (data.success) {
        alert('포인트 구매 신청이 완료되었습니다. 관리자 승인 후 포인트가 충전됩니다.')
        loadUserPoints()
        loadPurchaseHistory()
        // 폼 초기화
        setBuyerName('')
        setBankInfo('')
        setDepositorName('')
        setSelectedAmount(0)
      } else {
        alert(`포인트 구매 신청 실패: ${data.error}`)
      }
    } catch (error) {
      console.error('❌ 수동 구매 신청 오류:', error)
      alert(`포인트 구매 신청 중 오류가 발생했습니다: ${error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const getSelectedPackage = () => {
    const found = pointPackages.find(pkg => pkg.amount === selectedAmount)
    return found || { amount: 0, price: 0 }
  }

  const copyToClipboard = async (text, type) => {
    try {
      await navigator.clipboard.writeText(text)
      alert(`${type}이 복사되었습니다!`)
    } catch (err) {
      // 클립보드 API가 지원되지 않는 경우 대체 방법
      const textArea = document.createElement('textarea')
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      alert(`${type}이 복사되었습니다!`)
    }
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
          
          {/* 결제 방식 선택 */}
          <div className="payment-method-section">
            <h3>결제 방식</h3>
            <div className="payment-method-options">
              <div 
                className={`payment-method-option ${paymentMethod === 'kcp' ? 'selected' : ''}`}
                onClick={() => setPaymentMethod('kcp')}
              >
                <CreditCard className="payment-method-icon" />
                <div className="payment-method-content">
                  <span className="payment-method-label">KCP 카드결제 (즉시충전)</span>
                  <span className="payment-method-badge">추천</span>
                  <div className="payment-method-description">
                    <p>💳 신용카드로 안전하고 빠른 결제</p>
                    <p>⚡ 결제 완료 즉시 포인트 자동 충전</p>
                    <p>🔒 KCP 보안 시스템으로 안전한 결제</p>
                  </div>
                </div>
              </div>
              
              <div 
                className={`payment-method-option ${paymentMethod === 'manual' ? 'selected' : ''}`}
                onClick={() => setPaymentMethod('manual')}
              >
                <Building2 className="payment-method-icon" />
                <div className="payment-method-content">
                  <span className="payment-method-label">계좌이체 (수동승인)</span>
                  <div className="payment-method-description">
                    <p>🏦 계좌이체 후 관리자 승인</p>
                    <p>⏰ 승인 후 포인트 충전</p>
                    <p>📋 입금자명과 계좌정보 입력 필요</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 수동 승인 폼 */}
          {paymentMethod === 'manual' && (
            <div className="manual-payment-form">
              <h3>입금 정보</h3>
              <div className="form-group">
                <label htmlFor="buyerName">입금자명 *</label>
                <input
                  type="text"
                  id="buyerName"
                  value={buyerName}
                  onChange={(e) => setBuyerName(e.target.value)}
                  placeholder="입금자명을 입력하세요"
                  required
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="bankInfo">계좌 정보 *</label>
                <input
                  type="text"
                  id="bankInfo"
                  value={bankInfo}
                  onChange={(e) => setBankInfo(e.target.value)}
                  placeholder="은행명, 계좌번호를 입력하세요"
                  required
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="depositorName">예금주명</label>
                <input
                  type="text"
                  id="depositorName"
                  value={depositorName}
                  onChange={(e) => setDepositorName(e.target.value)}
                  placeholder="예금주명을 입력하세요 (선택사항)"
                />
              </div>
              
              <button
                type="button"
                className="account-info-btn"
                onClick={() => setShowAccountModal(true)}
              >
                <Building2 size={20} />
                입금 계좌 정보 보기
              </button>
            </div>
          )}





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
            {isLoading ? '처리중...' : isKcpLoading ? 'KCP 결제 준비중...' : 
             paymentMethod === 'kcp' ? 'KCP 카드결제' : '포인트 구매 신청'}
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

      {/* 계좌 정보 모달 */}
      {showAccountModal && (
        <div className="modal-overlay" onClick={() => setShowAccountModal(false)}>
          <div className="modal-content account-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>입금 계좌 정보</h2>
              <button 
                className="close-btn"
                onClick={() => setShowAccountModal(false)}
              >
                ×
              </button>
            </div>
            
            <div className="modal-body">
              <div className="modal-info">
                <p>💰 아래 계좌로 입금 후 입금자명과 계좌정보를 입력해주세요</p>
                <p>입금 확인 후 관리자가 승인하여 포인트가 충전됩니다</p>
              </div>
              
              <div className="account-details">
                <div className="account-item">
                  <span className="account-label">예금주</span>
                  <div className="account-value-with-copy">
                    <span className="account-value">SOCIALITY</span>
                    <button 
                      className="copy-btn"
                      onClick={() => copyToClipboard('SOCIALITY', '예금주명')}
                    >
                      <Copy size={16} />
                    </button>
                  </div>
                </div>
                
                <div className="account-item">
                  <span className="account-label">은행명</span>
                  <div className="account-value-with-copy">
                    <span className="account-value">국민은행</span>
                    <button 
                      className="copy-btn"
                      onClick={() => copyToClipboard('국민은행', '은행명')}
                    >
                      <Copy size={16} />
                    </button>
                  </div>
                </div>
                
                <div className="account-item">
                  <span className="account-label">계좌번호</span>
                  <div className="account-value-with-copy">
                    <span className="account-value">123456-78-901234</span>
                    <button 
                      className="copy-btn"
                      onClick={() => copyToClipboard('123456-78-901234', '계좌번호')}
                    >
                      <Copy size={16} />
                    </button>
                  </div>
                </div>
              </div>
              
              <div className="account-note">
                <p>⚠️ 입금 시 반드시 입금자명을 정확히 입력해주세요</p>
                <p>입금 확인 후 1-2시간 내에 포인트가 충전됩니다</p>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

export default PointsPage
