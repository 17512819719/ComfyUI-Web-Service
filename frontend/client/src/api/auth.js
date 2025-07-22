import axios from 'axios'
import { useAuthStore } from '@/store/auth'

// 创建一个获取完整 API URL 的函数
const getApiUrl = (endpoint) => {
  const authStore = useAuthStore()
  return `${authStore.apiBase}${endpoint}`
}

export const login = async (username, password) => {
  try {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    
    const response = await axios.post(getApiUrl('/auth/login'), formData)
    return response.data
  } catch (error) {
    throw error.response?.data || error.message
  }
}

export const logout = async () => {
  try {
    const authStore = useAuthStore()
    const response = await axios.post(getApiUrl('/auth/logout'), null, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    return response.data
  } catch (error) {
    throw error.response?.data || error.message
  }
}

export const refreshToken = async () => {
  try {
    const authStore = useAuthStore()
    const response = await axios.post(getApiUrl('/auth/refresh'), null, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    return response.data
  } catch (error) {
    throw error.response?.data || error.message
  }
} 