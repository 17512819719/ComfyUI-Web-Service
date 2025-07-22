import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const isGenerating = ref(false)
  const currentBatchId = ref(null)
  const batchCounter = ref(0)
  const currentMode = ref('text-to-image')
  const uploadedImageData = ref(null)

  // 轮询相关状态
  const pollingTasks = ref(new Map()) // 存储正在轮询的任务ID和定时器
  const pollingRetryCount = ref(new Map()) // 存储每个任务的重试次数

  const authStore = useAuthStore()

  const fetchTasks = async () => {
    // 检查是否有有效的认证token
    if (!authStore.token) {
      console.log('无认证token，跳过获取任务列表')
      return
    }

    try {
      const response = await fetch(`${authStore.apiBase}/v2/tasks`, {
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
          'Accept': 'application/json'
        }
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('401 未授权')
        }
        throw new Error(`获取任务列表失败: ${response.status}`)
      }

      const data = await response.json()
      if (data.tasks && Array.isArray(data.tasks)) {
        tasks.value = data.tasks.map(task => {
          let resultUrls = []
          if (task.status === 'completed') {
            if (task.resultUrls) {
              resultUrls = task.resultUrls
              console.log(`[TaskStore] 使用后端提供的resultUrls:`, resultUrls)
            } else if (task.result_data?.files) {
              resultUrls = task.result_data.files.map((file, index) =>
                `${authStore.apiBase}/v2/tasks/${task.task_id}/download?index=${index}`
              )
              // console.log(`[TaskStore] 生成下载URL:`, resultUrls)
            }
          }

          return {
            id: task.task_id,
            task_id: task.task_id, // 保留原始task_id字段
            status: task.status,
            prompt: task.result_data?.prompt || '',
            negative_prompt: task.result_data?.negative_prompt || '',
            width: task.result_data?.width || 1024,
            height: task.result_data?.height || 1024,
            workflow_name: task.result_data?.workflow_name || 'sd_basic',
            checkpoint: task.result_data?.checkpoint || '',
            seed: task.result_data?.seed || -1,
            batch_id: task.result_data?.batch_id || `batch_${task.task_id}`,
            progress: task.progress || 0,
            message: task.message || '',
            error_message: task.error_message,
            created_at: task.created_at,
            updated_at: task.updated_at,
            resultUrls
          }
        })

        // 检查并开始轮询进行中的任务
        checkAndStartPolling()
      }
    } catch (error) {
      console.error('获取任务列表失败:', error)
      throw error
    }
  }

  const submitTextToImage = async (formData) => {
    try {
      isGenerating.value = true
      batchCounter.value++
      currentBatchId.value = `batch_${Date.now()}_${batchCounter.value}`

      const response = await fetch(`${authStore.apiBase}/v2/tasks/text-to-image`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          batch_id: currentBatchId.value
        })
      })

      if (!response.ok) {
        throw new Error('提交任务失败')
      }

      const data = await response.json()
      const task = {
        id: data.task_id,
        status: 'queued',
        prompt: formData.prompt,
        negative_prompt: formData.negative_prompt,
        width: formData.width,
        height: formData.height,
        workflow_name: formData.workflow_name,
        checkpoint: formData.checkpoint,
        batch_id: currentBatchId.value,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      tasks.value.unshift(task)

      // 立即开始轮询任务状态
      startPollingTask(task.id)

      return task
    } catch (error) {
      console.error('提交文生图任务失败:', error)
      throw error
    } finally {
      isGenerating.value = false
      currentBatchId.value = null
    }
  }

  const submitImageToVideo = async (formData) => {
    try {
      if (!uploadedImageData.value) {
        throw new Error('请先上传图片')
      }

      isGenerating.value = true
      batchCounter.value++
      currentBatchId.value = `batch_${Date.now()}_${batchCounter.value}`

      const response = await fetch(`${authStore.apiBase}/v2/tasks/image-to-video`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prompt: formData.prompt,
          negative_prompt: formData.negative_prompt,
          image: uploadedImageData.value.relative_path,
          workflow_name: 'Wan2.1 i2v',
          batch_id: currentBatchId.value
        })
      })

      if (!response.ok) {
        throw new Error('提交任务失败')
      }

      const data = await response.json()
      const task = {
        id: data.task_id,
        status: 'queued',
        prompt: formData.prompt,
        negative_prompt: formData.negative_prompt,
        workflow_name: 'Wan2.1 i2v',
        batch_id: currentBatchId.value,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      tasks.value.unshift(task)

      // 立即开始轮询任务状态
      startPollingTask(task.id)

      return task
    } catch (error) {
      console.error('提交图生视频任务失败:', error)
      throw error
    } finally {
      isGenerating.value = false
      currentBatchId.value = null
    }
  }

  const downloadImage = async (taskId, index) => {
    try {
      const response = await fetch(`${authStore.apiBase}/v2/tasks/${taskId}/download?index=${index}`, {
        headers: {
          'Authorization': `Bearer ${authStore.token}`
        }
      })

      if (!response.ok) {
        throw new Error('下载失败')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `image_${taskId}_${index}.png`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('下载失败:', error)
      throw error
    }
  }

  const setMode = (mode) => {
    currentMode.value = mode
    if (mode === 'text-to-image') {
      uploadedImageData.value = null
    }
  }

  const setUploadedImage = (data) => {
    uploadedImageData.value = data

    // 如果设置了图片数据，自动切换到图生视频模式
    if (data && currentMode.value !== 'image-to-video') {
      setMode('image-to-video')
    }
  }

  // 计算轮询间隔
  const calculatePollingInterval = (status, retryCount = 0) => {
    if (status === 'processing') {
      return 1000 // 处理中时每秒更新
    } else if (status === 'queued') {
      return Math.min(2000 * Math.pow(1.5, retryCount), 10000) // 排队中时逐渐增加间隔
    }
    return 2000 // 默认间隔
  }

  // 轮询单个任务状态
  const pollTaskStatus = async (taskId) => {
    // 检查是否还有有效的认证token，如果没有则停止轮询
    if (!authStore.token) {
      console.log('无认证token，停止轮询任务:', taskId)
      stopPollingTask(taskId)
      return
    }

    try {
      const response = await fetch(`${authStore.apiBase}/v2/tasks/${taskId}/status`, {
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
          'Accept': 'application/json'
        }
      })

      if (!response.ok) {
        if (response.status === 401) {
          console.log('认证失败，停止轮询任务:', taskId)
          stopPollingTask(taskId)
          return
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log('任务状态轮询:', taskId, data.status)

      // 查找并更新任务
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        const task = tasks.value[taskIndex]

        // 更新任务状态
        task.status = data.status
        task.progress = data.progress || 0

        // 如果任务完成，更新结果
        if (data.status === 'completed' && data.result) {
          task.images = data.result.images || []
          task.created_at = data.result.created_at || task.created_at
        }

        // 如果任务失败，更新错误信息
        if (data.status === 'failed') {
          task.error = data.error || '任务执行失败'
        }
      }

      // 继续轮询未完成的任务
      if (data.status === 'queued' || data.status === 'processing') {
        // 再次检查认证状态
        if (!authStore.token) {
          console.log('认证已失效，停止轮询任务:', taskId)
          stopPollingTask(taskId)
          return
        }

        const retryCount = pollingRetryCount.value.get(taskId) || 0
        const interval = calculatePollingInterval(data.status, retryCount)

        const timeoutId = setTimeout(() => pollTaskStatus(taskId), interval)
        pollingTasks.value.set(taskId, timeoutId)
        pollingRetryCount.value.set(taskId, retryCount + 1)
      } else {
        // 任务完成或失败，停止轮询
        stopPollingTask(taskId)

        // 如果任务完成且仍有认证token，延迟刷新任务列表以获取最新数据
        if (data.status === 'completed' && authStore.token) {
          setTimeout(() => {
            // 再次检查认证状态
            if (authStore.token) {
              fetchTasks()
            }
          }, 500)
        }
      }
    } catch (error) {
      console.error('轮询任务状态出错:', taskId, error)

      // 检查是否还有认证token，如果没有则停止轮询
      if (!authStore.token) {
        console.log('无认证token，停止重试轮询任务:', taskId)
        stopPollingTask(taskId)
        return
      }

      // 出错时继续轮询，但增加间隔
      const retryCount = pollingRetryCount.value.get(taskId) || 0
      const timeoutId = setTimeout(() => pollTaskStatus(taskId), 3000)
      pollingTasks.value.set(taskId, timeoutId)
      pollingRetryCount.value.set(taskId, retryCount + 1)
    }
  }

  // 开始轮询任务
  const startPollingTask = (taskId) => {
    // 如果已经在轮询，先停止
    stopPollingTask(taskId)

    // 重置重试计数
    pollingRetryCount.value.set(taskId, 0)

    // 立即开始轮询
    pollTaskStatus(taskId)
  }

  // 停止轮询任务
  const stopPollingTask = (taskId) => {
    const timeoutId = pollingTasks.value.get(taskId)
    if (timeoutId) {
      clearTimeout(timeoutId)
      pollingTasks.value.delete(taskId)
    }
    pollingRetryCount.value.delete(taskId)
  }

  // 停止所有轮询
  const stopAllPolling = () => {
    pollingTasks.value.forEach((timeoutId) => {
      clearTimeout(timeoutId)
    })
    pollingTasks.value.clear()
    pollingRetryCount.value.clear()
  }

  // 检查并开始轮询进行中的任务
  const checkAndStartPolling = () => {
    tasks.value.forEach(task => {
      if ((task.status === 'queued' || task.status === 'processing') &&
          !pollingTasks.value.has(task.id)) {
        startPollingTask(task.id)
      }
    })
  }

  // 检查连接状态
  const checkConnection = async () => {
    // 检查是否有有效的认证token
    if (!authStore.token) {
      console.log('无认证token，跳过连接检查')
      return false // 静默返回false而不是抛出错误
    }

    try {
      const response = await fetch(`${authStore.apiBase}/v2/tasks`, {
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
          'Accept': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error('连接失败')
      }

      return true
    } catch (error) {
      console.error('连接检查失败:', error)
      throw error
    }
  }

  // 重新加载任务
  const reloadTask = async (taskId) => {
    if (!authStore.token) {
      throw new Error('未登录')
    }

    try {
      const response = await fetch(`${authStore.apiBase}/v2/tasks/reload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ task_id: taskId })
      })

      if (!response.ok) {
        if (response.status === 401) {
          authStore.logout()
          throw new Error('认证失败，请重新登录')
        }
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `重新加载任务失败: ${response.status}`)
      }

      const data = await response.json()
      console.log('任务重新加载成功:', data)

      // 开始轮询任务状态（使用原有的task_id）
      if (data.task_id) {
        startPollingTask(data.task_id)
      }

      // 刷新任务列表
      await fetchTasks()

      return data
    } catch (error) {
      console.error('重新加载任务失败:', error)
      throw error
    }
  }

  return {
    tasks,
    isGenerating,
    currentBatchId,
    currentMode,
    uploadedImageData,
    fetchTasks,
    submitTextToImage,
    submitImageToVideo,
    downloadImage,
    reloadTask,
    setMode,
    setUploadedImage,
    // 轮询相关方法
    startPollingTask,
    stopPollingTask,
    stopAllPolling,
    checkAndStartPolling,
    checkConnection,
    // 添加 reset 方法
    reset: () => {
      tasks.value = []
      isGenerating.value = false
      currentBatchId.value = null
      batchCounter.value = 0
      currentMode.value = 'text-to-image'
      uploadedImageData.value = null
      // 清理轮询
      stopAllPolling()
    }
  }
})