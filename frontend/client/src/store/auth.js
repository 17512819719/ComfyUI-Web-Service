import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('authToken') || null)
  const apiServer = ref(localStorage.getItem('apiServer') || 'http://localhost:8000')
  
  const apiBase = computed(() => {
    return `${apiServer.value.replace(/\/$/, '')}/api`
  })

  const isAuthenticated = computed(() => !!token.value)

  const login = async (username, password) => {
    try {
      const formData = new FormData()
      formData.append('username', username)
      formData.append('password', password)

      const response = await fetch(`${apiBase.value}/auth/login`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('登录失败，请检查用户名和密码')
      }

      const data = await response.json()
      token.value = data.access_token
      localStorage.setItem('authToken', data.access_token)
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    token.value = null
    localStorage.removeItem('authToken')
  }

  const setApiServer = (url) => {
    apiServer.value = url.replace(/\/$/, '')
    localStorage.setItem('apiServer', apiServer.value)
  }

  return {
    token,
    apiServer,
    apiBase,
    isAuthenticated,
    login,
    logout,
    setApiServer
  }
}) 