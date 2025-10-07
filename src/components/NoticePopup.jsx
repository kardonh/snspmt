import React from 'react'
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

  if (!showNoticePopup || notices.length === 0) {
    return null
  }

  return (
    <div className="notice-popup-overlay">
      <div className="notice-popup">
        <div className="notice-popup-header">
          <h3>{notices[currentNoticeIndex]?.title}</h3>
          <button 
            className="notice-popup-close"
            onClick={handleCloseNotice}
          >
            ×
          </button>
        </div>
        <div className="notice-popup-content">
          {notices[currentNoticeIndex]?.image_url && (
            <img 
              src={notices[currentNoticeIndex].image_url} 
              alt="공지사항 이미지" 
              className="notice-popup-image"
            />
          )}
          <p>{notices[currentNoticeIndex]?.content}</p>
        </div>
        <div className="notice-popup-footer">
          <button 
            className="notice-dismiss-btn"
            onClick={handleDismissToday}
          >
            오늘 하루 보지 않기
          </button>
          <div className="notice-popup-actions">
            {currentNoticeIndex < notices.length - 1 ? (
              <button 
                className="notice-next-btn"
                onClick={handleNextNotice}
              >
                다음 공지사항
              </button>
            ) : (
              <button 
                className="notice-close-btn"
                onClick={handleCloseNotice}
              >
                확인
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default NoticePopup
