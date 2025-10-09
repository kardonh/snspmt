import React, { useState, useEffect } from 'react'
import { Menu, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import StatusBar from './StatusBar'
import Sidebar from './Sidebar'
import BottomTabBar from './BottomTabBar'
import GuidePanel from './GuidePanel'
import AuthModal from './AuthModal'
import NoticePopup from './NoticePopup'
import './Layout.css'
import './GuidePanel.css'
import '../pages/Home.css'

const Layout = ({ children }) => {
  const { currentUser, showAuthModal, setShowAuthModal, authModalMode, showOrderMethodModal, setShowOrderMethodModal } = useAuth()
  const [isMobile, setIsMobile] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // 화면 크기 감지
  useEffect(() => {
    const checkIsMobile = () => {
      const mobile = window.innerWidth <= 768
      setIsMobile(mobile)
    }
    
    checkIsMobile()
    window.addEventListener('resize', checkIsMobile)
    
    return () => window.removeEventListener('resize', checkIsMobile)
  }, [])

  // 로그인 상태 체크 - 자동으로 모달을 열지 않음
  useEffect(() => {
    // 로그인된 상태에서는 모달 닫기
    if (currentUser) {
      setShowAuthModal(false)
    }
  }, [currentUser])

  return (
    <div className="layout">
      <StatusBar />
      <div className="layout-content">

        
        {/* Sidebar - 데스크톱에서만 표시 */}
        {!isMobile && (
          <div className="sidebar-container">
            <Sidebar />
          </div>
        )}
        
        <main className="main-content">
          {children}
        </main>
        <GuidePanel />
        
        {/* Bottom Tab Bar - 모바일에서만 표시 */}
        <BottomTabBar />
        

      </div>

      {/* Auth Modal */}
      <AuthModal 
        isOpen={showAuthModal}
        initialMode={authModalMode}
        onClose={() => {
          setShowAuthModal(false)
        }}
        onSuccess={() => {
          setShowAuthModal(false)
        }}
      />

      {/* Notice Popup */}
      <NoticePopup />

      {/* 1:1 상담 버튼 - 전체 화면 고정 */}
      <div className="consultation-section">
        <button 
          className="consultation-btn"
          onClick={() => window.open('http://pf.kakao.com/_QqyKn', '_blank')}
        >
          <img src="/images/kakao-talk-simple.png" alt="1:1 상담" className="consult-image" />
        </button>
      </div>

      {/* 주문방법 모달 */}
      {showOrderMethodModal && (
        <div className="order-method-modal-overlay">
          <div className="order-method-modal">
            <div className="modal-header">
              <h3>📋 주문방법 가이드</h3>
              <button 
                className="modal-close-btn"
                onClick={() => setShowOrderMethodModal(false)}
              >
                ✕
              </button>
            </div>
            
            <div className="modal-content">
              <div className="order-steps">
                <div className="step">
                  <div className="step-number">1</div>
                  <div className="step-content">
                    <h4>서비스 선택</h4>
                    <p>원하는 플랫폼과 서비스를 선택하세요</p>
                  </div>
                </div>
                
                <div className="step">
                  <div className="step-number">2</div>
                  <div className="step-content">
                    <h4>수량 입력</h4>
                    <p>원하는 수량을 입력하세요 (최소 수량 이상)</p>
                  </div>
                </div>
                
                <div className="step">
                  <div className="step-number">3</div>
                  <div className="step-content">
                    <h4>링크 입력</h4>
                    <p>대상 게시물의 URL 또는 사용자명을 입력하세요</p>
                  </div>
                </div>
                
                <div className="step">
                  <div className="step-number">4</div>
                  <div className="step-content">
                    <h4>구매하기</h4>
                    <p>모든 정보를 확인하고 구매하기 버튼을 클릭하세요</p>
                  </div>
                </div>
              </div>
              
              <div className="important-notes">
                <h4>⚠️ 주의사항</h4>
                <ul>
                  <li>공개 계정의 게시물만 주문 가능합니다</li>
                  <li>링크는 정확한 URL 또는 사용자명을 입력해주세요</li>
                  <li>수량은 최소 수량 이상 입력해주세요</li>
                  <li>주문 후 취소는 불가능하니 신중히 선택해주세요</li>
                </ul>
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                className="modal-confirm-btn"
                onClick={() => setShowOrderMethodModal(false)}
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Layout