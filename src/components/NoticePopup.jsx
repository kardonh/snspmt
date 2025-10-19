import React, { useState } from 'react'
import { useNotice } from '../contexts/NoticeContext'
import './NoticePopup.css'

const NoticePopup = () => {
  const {
    notices,
    showNoticePopup,
    currentNoticeIndex,
    handleDismissToday,
    handleCloseNotice,
    handleNextNotice
  } = useNotice()

  const [imageLoading, setImageLoading] = useState(true)
  const [imageError, setImageError] = useState(false)

  // 공지사항이 변경될 때마다 이미지 상태 초기화
  React.useEffect(() => {
    setImageLoading(true)
    setImageError(false)
  }, [currentNoticeIndex])

  if (!showNoticePopup || notices.length === 0) {
    return null
  }

  const currentNotice = notices[currentNoticeIndex]
  const handleImageLoad = () => {
    setImageLoading(false)
    setImageError(false)
  }

  const handleImageError = () => {
    setImageLoading(false)
    setImageError(true)
  }

  const handleNextOrClose = () => {
    if (currentNoticeIndex < notices.length - 1) {
      handleNextNotice()
    } else {
      handleCloseNotice()
    }
  }

  return (
    <div className="notice-popup-overlay">
      <div className="notice-popup">
        <div className="notice-popup-header">
          <h3>공지사항 ({currentNoticeIndex + 1}/{notices.length})</h3>
          <button 
            className="notice-popup-close"
            onClick={handleCloseNotice}
          >
            ×
          </button>
        </div>
        <div className="notice-popup-content">
          <div className="notice-image-container">
            {currentNotice?.image_url && (
              <img 
                src={currentNotice.image_url} 
                alt="공지사항 이미지" 
                className="notice-popup-image"
              />
            )}
          </div>
        </div>
        <div className="notice-popup-footer">
          <button 
            className="notice-dismiss-btn"
            onClick={handleDismissToday}
          >
            오늘 하루 보지 않기
          </button>
          <button 
            className="notice-close-btn"
            onClick={handleNextOrClose}
          >
            {currentNoticeIndex < notices.length - 1 ? '다음' : '확인'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default NoticePopup
