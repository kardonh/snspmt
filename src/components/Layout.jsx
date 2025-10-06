import React, { useState, useEffect } from 'react'
import { Menu, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import StatusBar from './StatusBar'
import Sidebar from './Sidebar'
import BottomTabBar from './BottomTabBar'
import GuidePanel from './GuidePanel'
import AuthModal from './AuthModal'
import './Layout.css'

const Layout = ({ children }) => {
  const { currentUser, showAuthModal, setShowAuthModal } = useAuth()
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
        onClose={() => {
          setShowAuthModal(false)
        }}
        onSuccess={() => {
          setShowAuthModal(false)
        }}
      />
    </div>
  )
}

export default Layout