import axios from 'axios'
import { useAuthStore } from '@/store/auth'

const createAxiosInstance = () => {
  const authStore = useAuthStore()
  
  const instance = axios.create({
    baseURL: authStore.apiBase,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authStore.token}`
    }
  })

  // 响应拦截器
  instance.interceptors.response.use(
    response => response.data,
    error => {
      if (error.response?.status === 401) {
        authStore.logout()
        window.location.reload()
      }
      throw error.response?.data || error.message
    }
  )

  return instance
}

// 获取任务列表
export const getTasks = async () => {
  const api = createAxiosInstance()
  return api.get('/v2/tasks')
}

// 获取任务状态
export const getTaskStatus = async (taskId) => {
  const api = createAxiosInstance()
  return api.get(`/v2/tasks/${taskId}/status`)
}

// 文生图
export const textToImage = async (params) => {
  const api = createAxiosInstance()
  return api.post('/v2/tasks/text-to-image', params)
}

// 图生视频
export const imageToVideo = async (params) => {
  const api = createAxiosInstance()
  return api.post('/v2/tasks/image-to-video', params)
}

// 上传图片
export const uploadImage = async (file) => {
  const api = createAxiosInstance()
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/v2/upload/image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 下载图片
export const downloadImage = async (taskId, index) => {
  const api = createAxiosInstance()
  return api.get(`/v2/tasks/${taskId}/download`, {
    params: { index },
    responseType: 'blob'
  })
}

// 重新加载任务
export const reloadTask = async (taskId) => {
  const api = createAxiosInstance()
  return api.post('/v2/tasks/reload', { task_id: taskId })
}