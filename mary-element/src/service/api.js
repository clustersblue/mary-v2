import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import {
  authToastsSuppressed,
  guardOwnsRedirectNow,
  resetSessionNow,
  suppressAuthErrorToasts,
  waitForSessionValidation
} from '@/service/authGate'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
})

const originalMessageError = ElMessage.error.bind(ElMessage)
ElMessage.error = (input) => {
  if (authToastsSuppressed()) return
  return originalMessageError(input)
}

function isSessionProbe(url) {
  const path = String(url || '').split('?')[0].replace(/\/+$/, '')
  return path === '/login' || path === '/me' || path === '/forgot-password' || path === '/reset-password'
}

api.interceptors.request.use(
  async (config) => {
    if (!isSessionProbe(config.url)) {
      await waitForSessionValidation()
    }
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401 && router.currentRoute.value?.path !== '/login') {
      error.skipErrorToast = true
      suppressAuthErrorToasts()
      resetSessionNow()
      if (!guardOwnsRedirectNow()) {
        const redirect = router.currentRoute.value?.fullPath
        router.push({ path: '/login', query: { reason: 'expired', redirect } })
      }
    }
    return Promise.reject(error)
  }
)

export default api
