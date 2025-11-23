// Simple cache utility
const cache = new Map()
const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

export const getCachedData = (key) => {
  const cached = cache.get(key)
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    return cached.data
  }
  return null
}

export const setCachedData = (key, data) => {
  cache.set(key, { data, timestamp: Date.now() })
}

export const clearCache = (key) => {
  if (key) cache.delete(key)
  else cache.clear()
}

