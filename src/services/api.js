import axios from 'axios'
import { setupCache } from 'axios-cache-interceptor'

const VITE_API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// Create axios instance with caching
const axiosInstance = axios.create({
  baseURL: VITE_API_BASE_URL
})

// Setup cache with 5-minute TTL
const cachedAxios = setupCache(axiosInstance, {
  ttl: 5 * 60 * 1000, // 5 minutes
  interpretHeader: false,
  methods: ['get'],
  cachePredicate: {
    statusCheck: (status) => status >= 200 && status < 300
  }
})

export default cachedAxios

