/**
 * 图生视频服务
 * 处理图片到视频的转换功能
 */

import { useAuthStore } from '@/store/auth'
import { useTaskStore } from '@/store/task'

// 图生视频状态管理
export class ImageToVideoService {
  constructor() {
    this.isProcessing = false
    this.currentTask = null
    this.retryCount = 0
    this.maxRetries = 3
  }

  /**
   * 从现有图片切换到视频模式
   * @param {string} taskId - 任务ID
   * @param {number} imageIndex - 图片索引
   * @param {string} originalPrompt - 原始提示词
   * @returns {Promise<boolean>} 是否成功切换
   */
  async switchToVideoMode(taskId, imageIndex, originalPrompt = '') {
    if (this.isProcessing) {
      throw new Error('正在处理其他图生视频任务，请稍候')
    }

    try {
      this.isProcessing = true
      const authStore = useAuthStore()
      const taskStore = useTaskStore()

      // 1. 获取原始图片
      console.log('正在获取原始图片...', { taskId, imageIndex })
      const imageBlob = await this.downloadImage(taskId, imageIndex)
      
      // 2. 上传图片到服务器
      console.log('正在上传图片到服务器...')
      const uploadResult = await this.uploadImageForVideo(imageBlob, taskId, imageIndex)
      
      // 3. 切换到图生视频模式
      console.log('切换到图生视频模式...')
      taskStore.setMode('image-to-video')
      
      // 4. 设置上传的图片数据
      taskStore.setUploadedImage({
        filename: uploadResult.filename,
        relative_path: uploadResult.relative_path,
        full_path: uploadResult.full_path,
        url: uploadResult.relative_path,
        source: {
          taskId,
          imageIndex,
          originalPrompt
        }
      })

      // 5. 如果有原始提示词，设置到输入框
      if (originalPrompt) {
        this.setPromptForVideo(originalPrompt)
      }

      // 6. 滚动到输入区域
      this.scrollToInputArea()

      console.log('图生视频模式切换成功')
      return true

    } catch (error) {
      console.error('切换到图生视频模式失败:', error)
      throw new Error(`切换失败: ${error.message}`)
    } finally {
      this.isProcessing = false
    }
  }

  /**
   * 从URL切换到视频模式
   * @param {string} imageUrl - 图片URL
   * @param {string} prompt - 提示词
   * @returns {Promise<boolean>} 是否成功切换
   */
  async switchToVideoModeFromUrl(imageUrl, prompt = '') {
    if (this.isProcessing) {
      throw new Error('正在处理其他图生视频任务，请稍候')
    }

    try {
      this.isProcessing = true
      const taskStore = useTaskStore()

      // 1. 下载图片
      console.log('正在下载图片...', imageUrl)
      const imageBlob = await this.downloadImageFromUrl(imageUrl)
      
      // 2. 上传图片到服务器
      console.log('正在上传图片到服务器...')
      const uploadResult = await this.uploadImageForVideo(imageBlob, 'url', 0)
      
      // 3. 切换到图生视频模式
      console.log('切换到图生视频模式...')
      taskStore.setMode('image-to-video')
      
      // 4. 设置上传的图片数据
      taskStore.setUploadedImage({
        filename: uploadResult.filename,
        relative_path: uploadResult.relative_path,
        full_path: uploadResult.full_path,
        url: uploadResult.relative_path,
        source: {
          imageUrl,
          originalPrompt: prompt
        }
      })

      // 5. 设置提示词
      if (prompt) {
        this.setPromptForVideo(prompt)
      }

      // 6. 滚动到输入区域
      this.scrollToInputArea()

      console.log('从URL切换到图生视频模式成功')
      return true

    } catch (error) {
      console.error('从URL切换到图生视频模式失败:', error)
      throw new Error(`切换失败: ${error.message}`)
    } finally {
      this.isProcessing = false
    }
  }

  /**
   * 下载图片
   * @param {string} taskId - 任务ID
   * @param {number} imageIndex - 图片索引
   * @returns {Promise<Blob>} 图片Blob
   */
  async downloadImage(taskId, imageIndex) {
    const authStore = useAuthStore()
    
    const response = await fetch(`${authStore.apiBase}/v2/tasks/${taskId}/download?index=${imageIndex}`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })

    if (!response.ok) {
      throw new Error(`获取原始图片失败: HTTP ${response.status}`)
    }

    return await response.blob()
  }

  /**
   * 从URL下载图片
   * @param {string} imageUrl - 图片URL
   * @returns {Promise<Blob>} 图片Blob
   */
  async downloadImageFromUrl(imageUrl) {
    const authStore = useAuthStore()
    
    const response = await fetch(imageUrl, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })

    if (!response.ok) {
      throw new Error(`下载图片失败: HTTP ${response.status}`)
    }

    return await response.blob()
  }

  /**
   * 上传图片用于视频生成
   * @param {Blob} imageBlob - 图片Blob
   * @param {string} sourceId - 来源ID
   * @param {number} sourceIndex - 来源索引
   * @returns {Promise<Object>} 上传结果
   */
  async uploadImageForVideo(imageBlob, sourceId, sourceIndex) {
    const authStore = useAuthStore()
    
    // 创建文件对象
    const file = new File([imageBlob], `source_${sourceId}_${sourceIndex}.png`, { 
      type: 'image/png' 
    })

    // 创建FormData
    const formData = new FormData()
    formData.append('file', file)

    // 上传到服务器
    const response = await fetch(`${authStore.apiBase}/v2/upload/image`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      },
      body: formData
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `上传图片失败: HTTP ${response.status}`)
    }

    return await response.json()
  }

  /**
   * 设置视频生成的提示词
   * @param {string} originalPrompt - 原始提示词
   */
  setPromptForVideo(originalPrompt) {
    // 发射事件到全局事件总线或直接操作DOM
    const event = new CustomEvent('setVideoPrompt', {
      detail: {
        prompt: this.generateVideoPrompt(originalPrompt)
      }
    })
    window.dispatchEvent(event)
  }

  /**
   * 生成适合视频的提示词
   * @param {string} originalPrompt - 原始提示词
   * @returns {string} 视频提示词
   */
  generateVideoPrompt(originalPrompt) {
    if (!originalPrompt) {
      return '描述你希望视频中发生的动作或场景变化...'
    }

    // 为视频生成添加动作相关的提示
    const videoKeywords = [
      'smooth motion',
      'gentle movement',
      'natural animation',
      'flowing',
      'dynamic'
    ]

    // 如果原始提示词中没有动作相关词汇，添加一些
    const hasMotionKeywords = videoKeywords.some(keyword => 
      originalPrompt.toLowerCase().includes(keyword.toLowerCase())
    )

    if (!hasMotionKeywords) {
      return `${originalPrompt}, smooth motion, natural animation`
    }

    return originalPrompt
  }

  /**
   * 滚动到输入区域
   */
  scrollToInputArea() {
    setTimeout(() => {
      const inputPanel = document.querySelector('.input-panel')
      if (inputPanel) {
        inputPanel.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start' 
        })
      }
    }, 100)
  }

  /**
   * 验证图片是否适合视频生成
   * @param {Blob} imageBlob - 图片Blob
   * @returns {Promise<boolean>} 是否有效
   */
  async validateImageForVideo(imageBlob) {
    return new Promise((resolve) => {
      const img = new Image()
      
      img.onload = () => {
        // 检查图片尺寸
        const minSize = 256
        const maxSize = 2048
        
        if (img.width < minSize || img.height < minSize) {
          throw new Error(`图片尺寸过小，最小尺寸为 ${minSize}x${minSize}`)
        }
        
        if (img.width > maxSize || img.height > maxSize) {
          throw new Error(`图片尺寸过大，最大尺寸为 ${maxSize}x${maxSize}`)
        }
        
        resolve(true)
      }
      
      img.onerror = () => {
        throw new Error('图片格式无效')
      }
      
      img.src = URL.createObjectURL(imageBlob)
    })
  }

  /**
   * 重置服务状态
   */
  reset() {
    this.isProcessing = false
    this.currentTask = null
    this.retryCount = 0
  }

  /**
   * 获取处理状态
   * @returns {boolean} 是否正在处理
   */
  getProcessingStatus() {
    return this.isProcessing
  }
}

// 创建全局实例
export const imageToVideoService = new ImageToVideoService()

// 导出便捷函数
export const switchToVideoMode = (taskId, imageIndex, originalPrompt) => {
  return imageToVideoService.switchToVideoMode(taskId, imageIndex, originalPrompt)
}

export const switchToVideoModeFromUrl = (imageUrl, prompt) => {
  return imageToVideoService.switchToVideoModeFromUrl(imageUrl, prompt)
}

export default imageToVideoService
