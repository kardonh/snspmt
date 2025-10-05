import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import smmpanelApi from '../services/snspopApi'
import { CreditCard, Building2, User, DollarSign, Receipt, FileText, X, Copy, Check } from 'lucide-react'
import './PointsPage.css'

const PointsPage = () => {
  const { currentUser } = useAuth()
  const [userPoints, setUserPoints] = useState(0)
  const [selectedAmount, setSelectedAmount] = useState(0)
  const [depositorName, setDepositorName] = useState('')
  const [bankName, setBankName] = useState('')
  const [receiptType, setReceiptType] = useState('none') // 'tax', 'cash', 'none'
  const [businessNumber, setBusinessNumber] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [representative, setRepresentative] = useState('')
  const [contactPhone, setContactPhone] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [cashReceiptPhone, setCashReceiptPhone] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [purchaseHistory, setPurchaseHistory] = useState([])
  const [userInfo, setUserInfo] = useState(null)
  const [copiedItems, setCopiedItems] = useState({})
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

  // userInfo가 로드되고 세금계산서가 선택된 경우 자동 입력
  useEffect(() => {
    if (userInfo && receiptType === 'tax' && userInfo.accountType === 'business') {
      setBusinessNumber(userInfo.businessNumber || '')
      setBusinessName(userInfo.businessName || '')
      setRepresentative(userInfo.representative || '')
      setContactPhone(userInfo.contactPhone || '')
      setContactEmail(userInfo.contactEmail || '')
    }
  }, [userInfo, receiptType])

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


  // 복사 기능
  const handleCopy = async (text, itemType) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItems(prev => ({ ...prev, [itemType]: true }))
      
      // 2초 후 복사 상태 초기화
      setTimeout(() => {
        setCopiedItems(prev => ({ ...prev, [itemType]: false }))
      }, 2000)
    } catch (err) {
      console.error('복사 실패:', err)
      // 폴백: 선택 영역으로 복사
      const textArea = document.createElement('textarea')
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      
      setCopiedItems(prev => ({ ...prev, [itemType]: true }))
      setTimeout(() => {
        setCopiedItems(prev => ({ ...prev, [itemType]: false }))
      }, 2000)
    }
  }

  const handleReceiptTypeChange = (type) => {
    setReceiptType(type)
    
    console.log('영수증 타입 변경:', type)
    console.log('현재 사용자 정보:', userInfo)
    
    // 비즈니스 계정이고 세금계산서를 선택한 경우 자동으로 정보 입력
    if (type === 'tax' && userInfo && userInfo.accountType === 'business') {
      console.log('비즈니스 계정 자동 입력 시작')
      setBusinessNumber(userInfo.businessNumber || '')
      setBusinessName(userInfo.businessName || '')
      setRepresentative(userInfo.representative || '')
      setContactPhone(userInfo.contactPhone || '')
      setContactEmail(userInfo.contactEmail || '')
      
      // 자동 입력 완료 메시지
      setTimeout(() => {
        alert('비즈니스 계정 정보가 자동으로 입력되었습니다.')
      }, 100)
    } else if (type === 'tax') {
      console.log('비즈니스 계정이 아님 또는 사용자 정보 없음')
      console.log('userInfo:', userInfo)
      console.log('accountType:', userInfo?.accountType)
    }
  }

  const handlePurchase = async () => {
    if (!depositorName.trim() || !bankName.trim()) {
      alert('입금자 명과 은행을 모두 입력해주세요.')
      return
    }

    // 세금계산서 선택 시 모든 필수 정보 입력 확인
    if (receiptType === 'tax' && (!businessNumber.trim() || !businessName.trim() || !representative.trim() || !contactPhone.trim() || !contactEmail.trim())) {
      alert('세금계산서 발급을 위해 모든 필수 정보를 입력해주세요.')
      return
    }

    // 현금영수증 선택 시 전화번호 필수
    if (receiptType === 'cash' && !cashReceiptPhone.trim()) {
      alert('현금영수증 발급을 위해 전화번호를 입력해주세요.')
      return
    }

    setIsLoading(true)
    try {
      const purchaseData = {
        user_id: currentUser.uid,
        depositorName: depositorName.trim(),
        bankName: bankName.trim(),
        receiptType: receiptType,
        businessNumber: businessNumber.trim(),
        businessName: businessName.trim(),
        representative: representative.trim(),
        contactPhone: contactPhone.trim(),
        contactEmail: contactEmail.trim(),
        cashReceiptPhone: cashReceiptPhone.trim(),
        amount: selectedAmount,
        price: pointPackages.find(pkg => pkg.amount === selectedAmount)?.price || selectedAmount,
        status: 'pending'
      }

      // 내부 API로 포인트 구매 신청
      const response = await fetch('/api/points/purchase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': currentUser.uid
        },
        body: JSON.stringify({
          user_id: currentUser.uid,
          amount: selectedAmount,
          price: pointPackages.find(pkg => pkg.amount === selectedAmount)?.price || selectedAmount,
          buyer_name: depositorName.trim(),
          bank_info: bankName.trim()
        })
      })
      
      const result = await response.json()
      
      if (response.ok && result.purchase_id) {
        alert('포인트 구매 신청이 완료되었습니다. 관리자 승인 후 포인트가 추가됩니다.')
        
        // 계좌 정보 모달 자동으로 열기
        setShowAccountModal(true)
        
        setDepositorName('')
        setBankName('')
        setReceiptType('none')
        setBusinessNumber('')
        setBusinessName('')
        setRepresentative('')
        setContactPhone('')
        setContactEmail('')
        setCashReceiptPhone('')
        loadPurchaseHistory()
      } else {
        alert(`구매 신청 중 오류가 발생했습니다: ${result.error || '알 수 없는 오류'}`)
      }
    } catch (error) {
      console.error('구매 신청 실패:', error)
      alert('구매 신청 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
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
          <div className="form-group">
            <label>
              <User size={16} />
              입금자 명
            </label>
            <input
              type="text"
              value={depositorName}
              onChange={(e) => setDepositorName(e.target.value)}
              placeholder="입금자 명을 입력하세요"
              className="form-input"
            />
          </div>
          
          <div className="form-group">
            <label>
              <Building2 size={16} />
              은행
            </label>
            <input
              type="text"
              value={bankName}
              onChange={(e) => setBankName(e.target.value)}
              placeholder="은행명을 입력하세요 (예: 신한은행)"
              className="form-input"
            />
          </div>


          {/* 영수증 계산서 선택 */}
          <div className="receipt-section">
            <h3>
              <Receipt size={20} />
              영수증 계산서
            </h3>
            <div className="receipt-options">
              <label className="receipt-option">
                <input
                  type="radio"
                  name="receiptType"
                  value="none"
                  checked={receiptType === 'none'}
                  onChange={(e) => handleReceiptTypeChange(e.target.value)}
                />
                <X className="receipt-option-icon" />
                <span className="receipt-label">선택안함</span>
              </label>
              <label className="receipt-option">
                <input
                  type="radio"
                  name="receiptType"
                  value="cash"
                  checked={receiptType === 'cash'}
                  onChange={(e) => handleReceiptTypeChange(e.target.value)}
                />
                <Receipt className="receipt-option-icon" />
                <span className="receipt-label">현금영수증</span>
              </label>
              <label className="receipt-option">
                <input
                  type="radio"
                  name="receiptType"
                  value="tax"
                  checked={receiptType === 'tax'}
                  onChange={(e) => handleReceiptTypeChange(e.target.value)}
                />
                <FileText className="receipt-option-icon" />
                <span className="receipt-label">세금계산서</span>
              </label>
            </div>
          </div>

          {/* 세금계산서 선택 시 추가 정보 */}
          {receiptType === 'tax' && (
            <>
              <div className="form-group">
                <label>
                  <User size={16} />
                  사업자등록번호
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="text"
                  value={businessNumber}
                  onChange={(e) => setBusinessNumber(e.target.value)}
                  placeholder="사업자등록번호를 입력하세요 (예: 123-45-67890)"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
              <div className="form-group">
                <label>
                  <Building2 size={16} />
                  상호명
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  placeholder="상호명을 입력하세요"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
              <div className="form-group">
                <label>
                  <User size={16} />
                  대표자
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="text"
                  value={representative}
                  onChange={(e) => setRepresentative(e.target.value)}
                  placeholder="대표자명을 입력하세요"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
              <div className="form-group">
                <label>
                  <User size={16} />
                  담당자 연락처
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="tel"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  placeholder="담당자 연락처를 입력하세요 (예: 010-1234-5678)"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
              <div className="form-group">
                <label>
                  <User size={16} />
                  메일주소
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  placeholder="메일주소를 입력하세요"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
            </>
          )}

          {/* 현금영수증 선택 시 추가 정보 */}
          {receiptType === 'cash' && (
            <div className="form-group">
              <label>
                <User size={16} />
                전화번호
              </label>
              <input
                type="tel"
                value={cashReceiptPhone}
                onChange={(e) => setCashReceiptPhone(e.target.value)}
                placeholder="현금영수증 발급용 전화번호를 입력하세요 (예: 010-1234-5678)"
                className="form-input"
              />
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
            disabled={isLoading || selectedAmount === 0 || !depositorName.trim() || !bankName.trim() || (receiptType === 'tax' && (!businessNumber.trim() || !businessName.trim() || !representative.trim() || !contactPhone.trim() || !contactEmail.trim())) || (receiptType === 'cash' && !cashReceiptPhone.trim())}
            className="purchase-btn"
          >
            {isLoading ? '처리중...' : '포인트 구매 신청'}
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
                    <button 
                      className="account-info-btn-small"
                      onClick={() => setShowAccountModal(true)}
                      title="입금 계좌 정보 보기"
                    >
                      <CreditCard size={16} />
                    </button>
                    <div className={`history-status ${purchase.status}`}>
                      {purchase.status === 'pending' && '승인 대기중'}
                      {purchase.status === 'approved' && '승인 완료'}
                      {purchase.status === 'rejected' && '승인 거절'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>

      {/* 입금 계좌 정보 모달 */}
      {showAccountModal && (
        <div className="modal-overlay" onClick={() => setShowAccountModal(false)}>
          <div className="modal-content account-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                <CreditCard size={24} />
                💳 입금 계좌 정보
              </h2>
              <button 
                className="modal-close-btn"
                onClick={() => setShowAccountModal(false)}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="modal-body">
              <div className="modal-info">
                <p>✅ 포인트 구매 신청이 완료되었습니다!</p>
                <p>아래 계좌로 입금하시면 30분 내에 자동으로 포인트가 충전됩니다.</p>
              </div>
              
              <div className="account-details">
                <div className="account-item">
                  <span className="account-label">은행명</span>
                  <div className="account-value-with-copy">
                    <span className="account-value">카카오뱅크</span>
                    <button 
                      className={`copy-btn ${copiedItems.bank ? 'copied' : ''}`}
                      onClick={() => handleCopy('카카오뱅크', 'bank')}
                      title="은행명 복사"
                    >
                      {copiedItems.bank ? <Check size={16} /> : <Copy size={16} />}
                    </button>
                  </div>
                </div>
                <div className="account-item">
                  <span className="account-label">계좌번호</span>
                  <div className="account-value-with-copy">
                    <span className="account-value">3333-34-9347430</span>
                    <button 
                      className={`copy-btn ${copiedItems.account ? 'copied' : ''}`}
                      onClick={() => handleCopy('3333-34-9347430', 'account')}
                      title="계좌번호 복사"
                    >
                      {copiedItems.account ? <Check size={16} /> : <Copy size={16} />}
                    </button>
                  </div>
                </div>
                <div className="account-item">
                  <span className="account-label">예금주</span>
                  <div className="account-value-with-copy">
                    <span className="account-value">서동현((템블)tamble)</span>
                    <button 
                      className={`copy-btn ${copiedItems.holder ? 'copied' : ''}`}
                      onClick={() => handleCopy('서동현((템블)tamble)', 'holder')}
                      title="예금주명 복사"
                    >
                      {copiedItems.holder ? <Check size={16} /> : <Copy size={16} />}
                    </button>
                  </div>
                </div>
              </div>
              
              <div className="account-note">
                <p>※ 충전 신청란의 [입금자명] 과 입금시 [입금자명]이 일치해야 30분내로 자동으로 충전 됩니다.</p>
                <p>※ 30분내 충전이 안될시 카카오채널(링크)로 문의 해주세요</p>
                <p>※ 세금계산서 및 현금영수증 필요하시면 꼭 선택 부탁드립니다.</p>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

export default PointsPage
