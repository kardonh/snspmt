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
  const { currentUser } = useAuth()
  const [isMobile, setIsMobile] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
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

  // 로그인 상태 체크
  useEffect(() => {
    // 로딩이 완료된 후에만 체크
    if (currentUser === null) {
      setShowAuthModal(true)
    } else if (currentUser) {
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
          // 로그인하지 않은 상태에서는 모달을 닫을 수 없음
          if (!currentUser) {
            return
          }
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