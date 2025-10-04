import React, { useState, useRef, useEffect } from 'react'
import './OptimizedImage.css'

const OptimizedImage = ({ 
  src, 
  alt, 
  className = '', 
  placeholder = '/placeholder.png',
  lazy = true,
  onLoad,
  onError,
  ...props 
}) => {
  const [isLoaded, setIsLoaded] = useState(false)
  const [isInView, setIsInView] = useState(!lazy)
  const [hasError, setHasError] = useState(false)
  const imgRef = useRef(null)

  // Intersection Observer for lazy loading
  useEffect(() => {
    if (!lazy || isInView) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true)
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.1 }
    )

    if (imgRef.current) {
      observer.observe(imgRef.current)
    }

    return () => observer.disconnect()
  }, [lazy, isInView])

  const handleLoad = () => {
    setIsLoaded(true)
    if (onLoad) onLoad()
  }

  const handleError = () => {
    setHasError(true)
    if (onError) onError()
  }

  return (
    <div 
      ref={imgRef}
      className={`optimized-image-container ${className}`}
      {...props}
    >
      {!isInView && lazy && (
        <div className="image-placeholder">
          <div className="placeholder-content">
            <div className="placeholder-icon">📷</div>
            <span>이미지 로딩 중...</span>
          </div>
        </div>
      )}
      
      {isInView && (
        <>
          {!isLoaded && !hasError && (
            <div className="image-loading">
              <div className="loading-spinner">
                <div className="spinner"></div>
              </div>
            </div>
          )}
          
          <img
            src={hasError ? placeholder : src}
            alt={alt}
            className={`optimized-image ${isLoaded ? 'loaded' : ''} ${hasError ? 'error' : ''}`}
            onLoad={handleLoad}
            onError={handleError}
            loading={lazy ? 'lazy' : 'eager'}
          />
        </>
      )}
    </div>
  )
}

export default OptimizedImage
