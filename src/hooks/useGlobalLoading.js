import { useState, useCallback } from 'react'

// 전역 로딩 상태 관리 훅
export const useGlobalLoading = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('')

  const startLoading = useCallback((message = '처리 중...') => {
    setIsLoading(true)
    setLoadingMessage(message)
  }, [])

  const stopLoading = useCallback(() => {
    setIsLoading(false)
    setLoadingMessage('')
  }, [])

  const withLoading = useCallback(async (asyncFunction, message = '처리 중...') => {
    try {
      startLoading(message)
      const result = await asyncFunction()
      return result
    } finally {
      stopLoading()
    }
  }, [startLoading, stopLoading])

  return {
    isLoading,
    loadingMessage,
    startLoading,
    stopLoading,
    withLoading
  }
}

// 전역 에러 상태 관리 훅
export const useGlobalError = () => {
  const [error, setError] = useState(null)

  const setErrorWithTimeout = useCallback((errorMessage, timeout = 5000) => {
    setError(errorMessage)
    setTimeout(() => setError(null), timeout)
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    error,
    setError: setErrorWithTimeout,
    clearError
  }
}

// API 호출을 위한 통합 훅
export const useApiCall = () => {
  const { isLoading, withLoading } = useGlobalLoading()
  const { error, setError, clearError } = useGlobalError()

  const callApi = useCallback(async (apiFunction, loadingMessage = 'API 호출 중...') => {
    try {
      clearError()
      const result = await withLoading(apiFunction, loadingMessage)
      return result
    } catch (err) {
      const errorMessage = err.message || '알 수 없는 오류가 발생했습니다.'
      setError(errorMessage)
      throw err
    }
  }, [withLoading, setError, clearError])

  return {
    isLoading,
    error,
    callApi,
    clearError
  }
}
