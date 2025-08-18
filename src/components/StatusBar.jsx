import React, { useState, useEffect } from 'react'
import { CheckCircle } from 'lucide-react'
import './StatusBar.css'

const StatusBar = () => {
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  const formatTime = (date) => {
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).replace(/\./g, '-')
  }

  return (
    <div className="status-bar">
      <div className="status-content">
        <div className="status-indicator">
          <CheckCircle size={16} />
          <span>모든 서비스 정상 가동중</span>
        </div>
        <div className="status-time">
          체크시간: {formatTime(currentTime)}
        </div>
      </div>
    </div>
  )
}

export default StatusBar
