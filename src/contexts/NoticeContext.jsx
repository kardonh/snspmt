import React, { createContext, useContext, useState, useEffect } from 'react'

const NoticeContext = createContext()

export const useNotice = () => {
  const context = useContext(NoticeContext)
  if (!context) {
    throw new Error('useNotice must be used within a NoticeProvider')
  }
  return context
}

export const NoticeProvider = ({ children }) => {
  const [notices, setNotices] = useState([])
  const [showNoticePopup, setShowNoticePopup] = useState(false)
  const [currentNoticeIndex, setCurrentNoticeIndex] = useState(0)

  // 공지사항 로드
  const loadNotices = async () => {
    try {
      console.log('🔍 공지사항 로드 시작...')
      const response = await fetch('/api/notices/active')
      console.log('📡 공지사항 API 응답:', response.status)
      
      if (response.ok) {
        const data = await response.json()
        console.log('📋 공지사항 데이터:', data)
        setNotices(data.notices || [])
        
        // 오늘 하루 보지 않기 체크
        const today = new Date().toDateString()
        const dismissedNotices = JSON.parse(localStorage.getItem('dismissedNotices') || '{}')
        console.log('📅 오늘 날짜:', today)
        console.log('🚫 보지 않기 설정:', dismissedNotices)
        
        // 오늘 보지 않은 공지사항이 있고, 활성 공지사항이 있으면 팝업 표시
        if (data.notices && data.notices.length > 0 && dismissedNotices[today] !== true) {
          console.log('✅ 공지사항 팝업 표시')
          setShowNoticePopup(true)
        } else {
          console.log('❌ 공지사항 팝업 표시 안함 - 공지사항 없음 또는 이미 보지 않기 설정됨')
        }
      } else {
        console.log('❌ 공지사항 API 오류:', response.status)
      }
    } catch (error) {
      console.log('❌ 공지사항 로드 실패:', error)
    }
  }

  // 오늘 하루 보지 않기
  const handleDismissToday = () => {
    const today = new Date().toDateString()
    const dismissedNotices = JSON.parse(localStorage.getItem('dismissedNotices') || '{}')
    dismissedNotices[today] = true
    localStorage.setItem('dismissedNotices', JSON.stringify(dismissedNotices))
    setShowNoticePopup(false)
  }

  // 공지사항 닫기
  const handleCloseNotice = () => {
    setShowNoticePopup(false)
  }

  // 다음 공지사항 보기
  const handleNextNotice = () => {
    if (currentNoticeIndex < notices.length - 1) {
      setCurrentNoticeIndex(currentNoticeIndex + 1)
    } else {
      setShowNoticePopup(false)
    }
  }

  // 컴포넌트 마운트 시 공지사항 로드
  useEffect(() => {
    loadNotices()
  }, [])

  const value = {
    notices,
    showNoticePopup,
    currentNoticeIndex,
    setShowNoticePopup,
    setCurrentNoticeIndex,
    handleDismissToday,
    handleCloseNotice,
    handleNextNotice,
    loadNotices
  }

  return (
    <NoticeContext.Provider value={value}>
      {children}
    </NoticeContext.Provider>
  )
}
