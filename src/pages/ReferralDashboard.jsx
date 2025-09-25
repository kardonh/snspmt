import React, { useState, useEffect } from 'react'
import './ReferralDashboard.css'

const ReferralDashboard = () => {
  const [referralCode, setReferralCode] = useState('')
  const [referralStats, setReferralStats] = useState({
    totalReferrals: 0,
    totalCommission: 0,
    activeReferrals: 0,
    thisMonthReferrals: 0,
    thisMonthCommission: 0
  })
  const [referralHistory, setReferralHistory] = useState([])
  const [commissionHistory, setCommissionHistory] = useState([])
  const [hasReferralCode, setHasReferralCode] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  
  // 커미션 포인트 관련 상태
  const [commissionPoints, setCommissionPoints] = useState({
    total_earned: 0,
    total_paid: 0,
    current_balance: 0
  })
  const [commissionTransactions, setCommissionTransactions] = useState([])
  const [showWithdrawalModal, setShowWithdrawalModal] = useState(false)
  const [withdrawalData, setWithdrawalData] = useState({
    referrer_name: '',
    bank_name: '',
    account_number: '',
    account_holder: '',
    amount: ''
  })

  useEffect(() => {
    checkReferralAccess()
  }, [])

  const checkReferralAccess = async () => {
    try {
      // Firebase 사용자 ID 가져오기
      const userId = localStorage.getItem('userId') || 
                    localStorage.getItem('firebase_user_id') || 
                    'demo_user'
      
      console.log('추천인 대시보드 접근 확인 - 사용자 ID:', userId)
      
      // 사용자 이메일 가져오기 (실제 이메일 우선)
      const userEmail = localStorage.getItem('userEmail') || 
                        localStorage.getItem('firebase_user_email') || 
                        'tambleofficial@gmail.com'  // 실제 사용자 이메일
      
      console.log('🔍 사용자 이메일:', userEmail)
      
      // 사용자가 추천인 코드를 발급받았는지 확인
      const codeResponse = await fetch(`/api/referral/my-codes?user_id=${userEmail}`)
      console.log('추천인 코드 조회 응답:', codeResponse.status)
      
      if (codeResponse.ok) {
        const codeData = await codeResponse.json()
        console.log('추천인 코드 데이터:', codeData)
        
        if (codeData.codes && codeData.codes.length > 0) {
          // 활성화된 코드가 있는지 확인 (다양한 true 값 처리)
          const hasActiveCode = codeData.codes.some(code => 
            code.is_active === true || 
            code.is_active === 1 || 
            code.is_active === 'true' ||
            code.is_active === '1'
          )
          console.log('🔍 추천인 코드 상태 확인:', codeData.codes)
          console.log('✅ 활성화된 코드 존재:', hasActiveCode)
          
          if (hasActiveCode) {
            setHasReferralCode(true)
            // 추천인 코드 설정
            setReferralCode(codeData.codes[0].code)
            console.log('✅ 추천인 대시보드 접근 허용')
            // 데이터 로드 (중복 호출 방지)
            loadReferralData(userEmail)
            loadCommissionPoints(userEmail)
          } else {
            setHasReferralCode(false)
            console.log('❌ 활성화된 추천인 코드가 없습니다')
          }
        } else {
          setHasReferralCode(false)
          console.log('❌ 추천인 코드가 없습니다')
        }
      } else {
        const errorData = await codeResponse.json()
        console.error('추천인 코드 조회 실패:', errorData)
        setHasReferralCode(false)
      }
    } catch (error) {
      console.error('추천인 접근 권한 확인 실패:', error)
      setHasReferralCode(false)
    } finally {
      setIsLoading(false)
    }
  }

  const loadReferralData = async (userEmail) => {
    try {
      // 매개변수로 받은 이메일 사용, 없으면 기본값
      const email = userEmail || localStorage.getItem('userEmail') || 
                    localStorage.getItem('firebase_user_email') || 
                    'tambleofficial@gmail.com'
      
      console.log('📊 추천인 데이터 로드 시작 - 이메일:', email)

      // 추천인 통계 조회 (이메일 사용)
      const statsResponse = await fetch(`/api/referral/stats?user_id=${email}`)
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setReferralStats(statsData)
        console.log('📊 추천인 통계:', statsData)
      } else {
        console.error('❌ 추천인 통계 조회 실패:', statsResponse.status)
        // 폴백 데이터
        setReferralStats({
          totalReferrals: 0,
          totalCommission: 0,
          activeReferrals: 0,
          thisMonthReferrals: 0,
          thisMonthCommission: 0,
        })
      }

      // 추천인 목록 조회 (이메일 사용)
      const referralsResponse = await fetch(`/api/referral/referrals?user_id=${email}`)
      if (referralsResponse.ok) {
        const referralsData = await referralsResponse.json()
        setReferralHistory(referralsData.referrals || [])
        console.log('👥 추천인 목록:', referralsData.referrals)
      } else {
        console.error('❌ 추천인 목록 조회 실패:', referralsResponse.status)
      }

      // 커미션 내역 조회 (이메일 사용)
      const commissionsResponse = await fetch(`/api/referral/commissions?user_id=${email}`)
      if (commissionsResponse.ok) {
        const commissionsData = await commissionsResponse.json()
        setCommissionHistory(commissionsData.commissions || [])
        console.log('💰 커미션 내역:', commissionsData.commissions)
      } else {
        console.error('❌ 커미션 내역 조회 실패:', commissionsResponse.status)
      }
    } catch (error) {
      console.error('추천인 데이터 로드 실패:', error)
      // 폴백으로 기본 데이터 사용
      setReferralStats({
        totalReferrals: 0,
        totalCommission: 0,
        activeReferrals: 0,
        thisMonthReferrals: 0,
        thisMonthCommission: 0,
      })
    }
  }

  // 커미션 포인트 데이터 로드
  const loadCommissionPoints = async (userEmail) => {
    try {
      // 매개변수로 받은 이메일 사용, 없으면 기본값
      const email = userEmail || localStorage.getItem('userEmail') || 
                    localStorage.getItem('firebase_user_email') || 
                    'tambleofficial@gmail.com'
      
      console.log('💰 커미션 포인트 데이터 로드 시작 - 이메일:', email)
      
      // 커미션 포인트 조회
      const pointsResponse = await fetch(`/api/referral/commission-points?referrer_email=${email}`)
      if (pointsResponse.ok) {
        const pointsData = await pointsResponse.json()
        setCommissionPoints(pointsData)
        console.log('💰 커미션 포인트:', pointsData)
      } else {
        console.error('❌ 커미션 포인트 조회 실패:', pointsResponse.status)
      }
      
      // 커미션 포인트 거래 내역 조회
      const transactionsResponse = await fetch(`/api/referral/commission-transactions?referrer_email=${email}`)
      if (transactionsResponse.ok) {
        const transactionsData = await transactionsResponse.json()
        setCommissionTransactions(transactionsData.transactions || [])
        console.log('💰 커미션 거래 내역:', transactionsData.transactions)
      } else {
        console.error('❌ 커미션 거래 내역 조회 실패:', transactionsResponse.status)
      }
      
    } catch (error) {
      console.error('커미션 포인트 데이터 로드 실패:', error)
    }
  }

  const copyReferralCode = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(referralCode)
        alert('추천인 코드가 복사되었습니다!')
      } else {
        // 폴백: 텍스트 선택 방식
        const textArea = document.createElement('textarea')
        textArea.value = referralCode
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        alert('추천인 코드가 복사되었습니다!')
      }
    } catch (error) {
      console.error('클립보드 복사 실패:', error)
      alert('클립보드 복사에 실패했습니다. 수동으로 복사해주세요: ' + referralCode)
    }
  }

  const shareReferralCode = async () => {
    const shareText = `추천인 코드: ${referralCode}\n이 코드로 가입하시면 혜택을 받으실 수 있습니다!`
    try {
      if (navigator.share) {
        await navigator.share({
          title: '추천인 코드',
          text: shareText
        })
      } else {
        // 클립보드 복사 폴백
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(shareText)
          alert('추천인 코드가 복사되었습니다!')
        } else {
          // 텍스트 선택 방식
          const textArea = document.createElement('textarea')
          textArea.value = shareText
          document.body.appendChild(textArea)
          textArea.select()
          document.execCommand('copy')
          document.body.removeChild(textArea)
          alert('추천인 코드가 복사되었습니다!')
        }
      }
    } catch (error) {
      console.error('공유 실패:', error)
      alert('공유에 실패했습니다. 수동으로 복사해주세요: ' + shareText)
    }
  }

  // 환급 신청 처리
  const handleWithdrawalRequest = async () => {
    try {
      const userEmail = localStorage.getItem('userEmail') || 
                       localStorage.getItem('firebase_user_email') || 
                       'demo@example.com'
      
      const response = await fetch('/api/referral/withdrawal-request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          referrer_email: userEmail,
          ...withdrawalData
        })
      })

      if (response.ok) {
        alert('환급 신청이 접수되었습니다!')
        setShowWithdrawalModal(false)
        setWithdrawalData({
          referrer_name: '',
          bank_name: '',
          account_number: '',
          account_holder: '',
          amount: ''
        })
        loadCommissionPoints() // 데이터 새로고침
      } else {
        const errorData = await response.json()
        alert(`환급 신청 실패: ${errorData.error}`)
      }
    } catch (error) {
      console.error('환급 신청 오류:', error)
      alert('환급 신청 중 오류가 발생했습니다.')
    }
  }

  if (isLoading) {
    return (
      <div className="referral-dashboard">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>추천인 정보를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  if (!hasReferralCode) {
    return (
      <div className="referral-dashboard">
        <div className="no-access-container">
          <div className="no-access-icon">🔒</div>
          <h1>추천인 대시보드</h1>
          <p>추천인 코드를 발급받은 사용자만 접근할 수 있습니다.</p>
          <div className="access-info">
            <h3>추천인 코드 발급 방법</h3>
            <ol>
              <li>관리자에게 추천인 코드 발급을 요청하세요</li>
              <li>발급받은 코드로 추천인 대시보드에 접근할 수 있습니다</li>
              <li>친구들에게 추천인 코드를 공유하여 커미션을 받으세요</li>
            </ol>
          </div>
          <button 
            className="request-code-btn"
            onClick={() => window.location.href = '/admin'}
          >
            관리자 페이지로 이동
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="referral-dashboard">
      <div className="dashboard-header">
        <h1>추천인 대시보드</h1>
        <p>추천 현황과 수익을 확인하세요</p>
      </div>

      {/* 추천인 코드 섹션 */}
      <div className="referral-code-section">
        <div className="code-card">
          <h2>내 추천인 코드</h2>
          <div className="code-display">
            <span className="code-text">{referralCode}</span>
            <button className="copy-btn" onClick={copyReferralCode}>
              복사
            </button>
          </div>
          <button className="share-btn" onClick={shareReferralCode}>
            공유하기
          </button>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <h3>총 추천인</h3>
            <p className="stat-number">{referralStats.totalReferrals}</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💰</div>
          <div className="stat-content">
            <h3>총 커미션</h3>
            <p className="stat-number">{referralStats.totalCommission.toLocaleString()}원</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <h3>활성 추천인</h3>
            <p className="stat-number">{referralStats.activeReferrals}</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📅</div>
          <div className="stat-content">
            <h3>이번 달 추천</h3>
            <p className="stat-number">{referralStats.thisMonthReferrals}</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💎</div>
          <div className="stat-content">
            <h3>이번 달 수익</h3>
            <p className="stat-number">{referralStats.thisMonthCommission.toLocaleString()}원</p>
          </div>
        </div>
      </div>

      {/* 커미션 포인트 섹션 */}
      <div className="commission-points-section">
        <div className="points-header">
          <h2>커미션 포인트</h2>
          <button 
            className="withdrawal-btn"
            onClick={() => setShowWithdrawalModal(true)}
            disabled={commissionPoints.current_balance <= 0}
          >
            환급 신청
          </button>
        </div>
        
        <div className="points-grid">
          <div className="points-card">
            <div className="points-icon">💎</div>
            <div className="points-content">
              <h3>현재 잔액</h3>
              <p className="points-number">{commissionPoints.current_balance.toLocaleString()}원</p>
            </div>
          </div>
          <div className="points-card">
            <div className="points-icon">📈</div>
            <div className="points-content">
              <h3>총 적립</h3>
              <p className="points-number">{commissionPoints.total_earned.toLocaleString()}원</p>
            </div>
          </div>
          <div className="points-card">
            <div className="points-icon">💸</div>
            <div className="points-content">
              <h3>총 환급</h3>
              <p className="points-number">{commissionPoints.total_paid.toLocaleString()}원</p>
            </div>
          </div>
        </div>
      </div>

      {/* 추천인 목록 */}
      <div className="referral-list-section">
        <div className="section-card">
          <h2>추천인 목록</h2>
          <div className="table-container">
            <table className="referral-table">
              <thead>
                <tr>
                  <th>사용자</th>
                  <th>가입일</th>
                  <th>상태</th>
                  <th>커미션</th>
                </tr>
              </thead>
              <tbody>
                {referralHistory.map((referral) => (
                  <tr key={referral.id}>
                    <td>{referral.user}</td>
                    <td>{referral.joinDate}</td>
                    <td>
                      <span className={`status-badge ${referral.status === '활성' ? 'active' : 'inactive'}`}>
                        {referral.status}
                      </span>
                    </td>
                    <td>{referral.commission.toLocaleString()}원</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 커미션 내역 */}
      <div className="commission-section">
        <div className="section-card">
          <h2>커미션 내역</h2>
          <div className="commission-summary">
            <div className="summary-item">
              <span className="summary-label">총 커미션</span>
              <span className="summary-value">{referralStats.totalCommission.toLocaleString()}원</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">이번 달 커미션</span>
              <span className="summary-value">{referralStats.thisMonthCommission.toLocaleString()}원</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">커미션율</span>
              <span className="summary-value">10%</span>
            </div>
          </div>
          <div className="table-container">
            <table className="commission-table">
              <thead>
                <tr>
                  <th>피추천인</th>
                  <th>구매 금액</th>
                  <th>커미션 금액</th>
                  <th>커미션율</th>
                  <th>지급일</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                {commissionHistory.length > 0 ? (
                  commissionHistory.map((commission) => (
                    <tr key={commission.id}>
                      <td className="user-info">
                        <div className="user-avatar">👤</div>
                        <span>{commission.referredUser}</span>
                      </td>
                      <td className="purchase-amount">{commission.purchaseAmount.toLocaleString()}원</td>
                      <td className="commission-amount">
                        <span className="amount">+{commission.commissionAmount.toLocaleString()}원</span>
                      </td>
                      <td className="commission-rate">{(commission.commissionRate * 100).toFixed(1)}%</td>
                      <td className="payment-date">{commission.paymentDate}</td>
                      <td className="status">
                        <span className="status-badge completed">지급완료</span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="6" className="no-data">
                      <div className="no-data-content">
                        <div className="no-data-icon">💰</div>
                        <p>아직 커미션 내역이 없습니다</p>
                        <small>친구를 추천하고 커미션을 받아보세요!</small>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 추천인 혜택 안내 */}
      <div className="benefits-section">
        <div className="section-card">
          <h2>추천인 혜택</h2>
          <div className="benefits-grid">
            <div className="benefit-item">
              <div className="benefit-icon">🎁</div>
              <h3>추천인 보상</h3>
              <p>추천한 사용자가 구매할 때마다 5% 커미션 지급</p>
            </div>
            <div className="benefit-item">
              <div className="benefit-icon">💎</div>
              <h3>추천인 할인</h3>
              <p>추천인 본인도 10% 할인 혜택 제공</p>
            </div>
            <div className="benefit-item">
              <div className="benefit-icon">🏆</div>
              <h3>등급 혜택</h3>
              <p>추천 수에 따라 등급별 추가 혜택 제공</p>
            </div>
          </div>
        </div>
      </div>

      {/* 환급 신청 모달 */}
      {showWithdrawalModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>환급 신청</h2>
              <button 
                className="close-btn"
                onClick={() => setShowWithdrawalModal(false)}
              >
                ×
              </button>
            </div>
            
            <div className="modal-body">
              <div className="form-group">
                <label>이름</label>
                <input
                  type="text"
                  value={withdrawalData.referrer_name}
                  onChange={(e) => setWithdrawalData({...withdrawalData, referrer_name: e.target.value})}
                  placeholder="실명을 입력하세요"
                />
              </div>
              
              <div className="form-group">
                <label>은행명</label>
                <input
                  type="text"
                  value={withdrawalData.bank_name}
                  onChange={(e) => setWithdrawalData({...withdrawalData, bank_name: e.target.value})}
                  placeholder="예: 국민은행"
                />
              </div>
              
              <div className="form-group">
                <label>계좌번호</label>
                <input
                  type="text"
                  value={withdrawalData.account_number}
                  onChange={(e) => setWithdrawalData({...withdrawalData, account_number: e.target.value})}
                  placeholder="계좌번호를 입력하세요"
                />
              </div>
              
              <div className="form-group">
                <label>예금주명</label>
                <input
                  type="text"
                  value={withdrawalData.account_holder}
                  onChange={(e) => setWithdrawalData({...withdrawalData, account_holder: e.target.value})}
                  placeholder="예금주명을 입력하세요"
                />
              </div>
              
              <div className="form-group">
                <label>환급 신청 금액</label>
                <input
                  type="number"
                  value={withdrawalData.amount}
                  onChange={(e) => setWithdrawalData({...withdrawalData, amount: e.target.value})}
                  placeholder="환급받을 금액을 입력하세요"
                  max={commissionPoints.current_balance}
                />
                <small>최대 {commissionPoints.current_balance.toLocaleString()}원까지 신청 가능</small>
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                className="cancel-btn"
                onClick={() => setShowWithdrawalModal(false)}
              >
                취소
              </button>
              <button 
                className="submit-btn"
                onClick={handleWithdrawalRequest}
                disabled={!withdrawalData.referrer_name || !withdrawalData.bank_name || !withdrawalData.account_number || !withdrawalData.account_holder || !withdrawalData.amount}
              >
                신청하기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ReferralDashboard
