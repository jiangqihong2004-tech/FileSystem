import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, removeToken, removeUserInfo } from '@/utils/storage'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 30000
})

request.interceptors.request.use(
  config => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = 'Bearer ' + token
    }
    return config
  },
  error => Promise.reject(error)
)

request.interceptors.response.use(
  response => response.data,
  error => {
    // 若调用方明确指定 silentOnError，则不展示全局 ElMessage
    const isSilent = !!(error && error.config && error.config.silentOnError)
    if (error.response) {
      if (error.response.status === 401) {
        ElMessage.error('登录已过期，请重新登录')
        removeToken()
        removeUserInfo()
        setTimeout(() => {
          window.location.href = '/login'
        }, 1500)
      } else if (!isSilent) {
        // 只在非静默场景下展示详细错误信息
        const msg = error.response.data?.detail || '请求失败'
        ElMessage.error(String(msg).slice(0, 60))
      }
    } else if (!isSilent) {
      // 网络连接失败：不持续打扰用户，做一次简短提示
      ElMessage({ type: 'warning', message: '网络连接失败，请检查网络或稍后重试', duration: 2000 })
    }
    return Promise.reject(error)
  }
)

export default request
