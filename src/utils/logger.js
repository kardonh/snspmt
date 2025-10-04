// 로깅 유틸리티 함수들

const LOG_LEVELS = {
  ERROR: 0,
  WARN: 1,
  INFO: 2,
  DEBUG: 3
}

class Logger {
  constructor() {
    this.logLevel = process.env.NODE_ENV === 'production' ? LOG_LEVELS.WARN : LOG_LEVELS.DEBUG
  }

  formatMessage(level, message, data = null) {
    const timestamp = new Date().toISOString()
    const logEntry = {
      timestamp,
      level,
      message,
      data,
      url: window.location.href,
      userAgent: navigator.userAgent
    }
    return logEntry
  }

  log(level, message, data = null) {
    if (level > this.logLevel) return

    const logEntry = this.formatMessage(level, message, data)
    
    // 콘솔에 출력
    const levelNames = ['ERROR', 'WARN', 'INFO', 'DEBUG']
    const levelName = levelNames[level]
    
    switch (level) {
      case LOG_LEVELS.ERROR:
        console.error(`[${levelName}] ${message}`, data || '')
        break
      case LOG_LEVELS.WARN:
        console.warn(`[${levelName}] ${message}`, data || '')
        break
      case LOG_LEVELS.INFO:
        console.info(`[${levelName}] ${message}`, data || '')
        break
      default:
        console.log(`[${levelName}] ${message}`, data || '')
    }

    // 프로덕션에서는 에러를 외부 서비스로 전송
    if (process.env.NODE_ENV === 'production' && level <= LOG_LEVELS.ERROR) {
      this.sendToExternalService(logEntry)
    }
  }

  error(message, data = null) {
    this.log(LOG_LEVELS.ERROR, message, data)
  }

  warn(message, data = null) {
    this.log(LOG_LEVELS.WARN, message, data)
  }

  info(message, data = null) {
    this.log(LOG_LEVELS.INFO, message, data)
  }

  debug(message, data = null) {
    this.log(LOG_LEVELS.DEBUG, message, data)
  }

  // API 호출 로깅
  apiCall(method, url, data = null, response = null, duration = null) {
    const message = `API ${method} ${url}`
    const logData = {
      method,
      url,
      requestData: data,
      responseData: response,
      duration: duration ? `${duration}ms` : null
    }
    
    if (response && response.status >= 400) {
      this.error(message, logData)
    } else {
      this.info(message, logData)
    }
  }

  // 사용자 액션 로깅
  userAction(action, data = null) {
    this.info(`User Action: ${action}`, data)
  }

  // 성능 메트릭 로깅
  performance(metric, value, unit = 'ms') {
    this.info(`Performance: ${metric}`, { value, unit })
  }

  // 외부 서비스로 에러 전송 (선택사항)
  sendToExternalService(logEntry) {
    // 실제 구현에서는 Sentry, LogRocket 등의 서비스 사용
    // 예시: Sentry.captureException(new Error(logEntry.message))
    console.log('Sending error to external service:', logEntry)
  }
}

// 싱글톤 인스턴스
const logger = new Logger()

// 전역 에러 핸들러
window.addEventListener('error', (event) => {
  logger.error('Global JavaScript Error', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    error: event.error
  })
})

window.addEventListener('unhandledrejection', (event) => {
  logger.error('Unhandled Promise Rejection', {
    reason: event.reason,
    promise: event.promise
  })
})

export default logger
