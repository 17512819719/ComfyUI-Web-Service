<template>
  <div class="gallery-grid">
    <!-- 空状态显示 -->
    <div v-if="tasks.length === 0" class="gallery-empty">
      <i class="fas fa-image"></i>
      <h3>还没有生成任何图片</h3>
      <p>在下方输入提示词开始创作吧！</p>
    </div>

    <!-- 批次列表 -->
    <template v-else>
      <div v-for="batch in batches" :key="batch.id" class="batch-container" :data-batch-id="batch.id">
        <!-- 批次标题栏 -->
        <div class="batch-header">
          <div class="batch-info">
            <div class="batch-meta">
              <span class="batch-date">{{ formatDate(batch.created_at) }}</span>
              <span class="batch-resolution">{{ getBatchResolution(batch) }}</span>
              <span class="batch-status" :class="'status-' + batch.status">
                {{ getStatusText(batch.status) }}
              </span>
              <span v-if="batch.status === 'processing'" class="batch-progress-text">
                {{ Math.round(batch.progress || 0) }}%
              </span>
            </div>
          </div>

          <!-- 批次操作按钮 -->
          <div class="batch-actions">
            <!-- 重新生成按钮 -->
            <button
              v-if="batch.status === 'completed' || batch.status === 'failed'"
              class="btn btn-secondary reload-btn"
              @click="reloadBatch(batch)"
              :disabled="isReloading"
              title="重新生成"
            >
              <i class="fas fa-redo" v-if="!isReloading"></i>
              <i class="fas fa-spinner fa-spin" v-else></i>
              重新生成
            </button>

            <!-- 批量下载按钮 -->
            <button
              v-if="batch.status === 'completed' && batch.resultUrls && batch.resultUrls.length > 0"
              class="btn btn-primary batch-download-btn"
              @click="downloadAllImages(batch)"
              :disabled="isDownloading"
            >
              <i class="fas fa-download" v-if="!isDownloading"></i>
              <i class="fas fa-spinner fa-spin" v-else></i>
              {{ isDownloading ? '下载中...' : '全部下载' }}
            </button>
          </div>
        </div>

        <!-- 进度条（仅在处理中时显示） -->
        <div v-if="batch.status === 'processing' || batch.status === 'queued'" class="batch-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: batch.status === 'processing' ? (batch.progress || 0) + '%' : '0%' }"></div>
          </div>
        </div>

        <!-- 下载进度条 -->
        <div v-if="downloadProgress.show" class="download-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: downloadProgress.percentage + '%' }"></div>
          </div>
          <span class="progress-text">
            {{ downloadProgress.text }}
          </span>
        </div>

        <!-- 图片网格 -->
        <div class="batch-images">
          <template v-if="batch.status === 'completed' && batch.resultUrls">
            <div v-for="(url, index) in batch.resultUrls" :key="index" class="batch-image-item">
              <div class="batch-image-container" @click="showImagePreview(url)">
                <ImageWithRetry
                  :src="url"
                  :alt="'生成结果 ' + (index + 1)"
                  :auth-token="authStore.token"
                  :max-retries="3"
                  :retry-delay="1000"
                  :lazy="false"
                  loading="eager"
                  @load="handleImageLoad"
                  @error="handleImageError"
                  @retry="handleImageRetry"
                  @auth-error="handleAuthError"
                />
                <!-- 图片编号 -->
                <div class="batch-image-index">#{{ index + 1 }}</div>
                <!-- 悬停操作按钮 -->
                <div class="batch-image-actions">
                  <button class="batch-image-action" @click.stop="downloadImage(batch.id, index)" title="下载图片">
                    <i class="fas fa-download"></i>
                  </button>
                  <button class="batch-image-action" @click.stop="handleImageToVideo(batch.id, index)" title="图生视频">
                    <i class="fas fa-film"></i>
                  </button>
                </div>
              </div>
            </div>
          </template>
          <template v-else>
            <!-- 占位符：显示4个空位 -->
            <div v-for="index in 4" :key="index" class="batch-image-item">
              <div class="batch-image-container">
                <div class="loading-placeholder">
                  <template v-if="batch.status === 'processing'">
                    <div class="spinner"></div>
                    <span>生成中...</span>
                  </template>
                  <template v-else-if="batch.status === 'queued'">
                    <i class="fas fa-clock"></i>
                    <span>等待中...</span>
                  </template>
                  <template v-else>
                    <i class="fas fa-image"></i>
                    <span>等待生成...</span>
                  </template>
                </div>
                <!-- 占位符也显示编号 -->
                <div class="batch-image-index">#{{ index }}</div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </template>

    <!-- 图片预览模态框 -->
    <div v-if="previewUrl" class="image-preview-modal" :class="{ active: previewUrl }" @click="closePreview">
      <div class="image-preview-content" @click.stop>
        <button class="image-preview-close" @click="closePreview">
          <i class="fas fa-times"></i>
        </button>
        <ImageWithRetry
          :src="previewUrl"
          alt="预览图片"
          :auth-token="authStore.token"
          :max-retries="3"
          :retry-delay="1000"
          :lazy="false"
          loading="eager"
          @load="handlePreviewLoad"
          @error="handlePreviewError"
          @retry="handlePreviewRetry"
          @auth-error="handleAuthError"
        />
      </div>
    </div>

    <!-- 提示词详情模态框 -->
    <PromptDetailsModal
      :visible="promptModalVisible"
      :prompt="promptModalData.prompt"
      :negative-prompt="promptModalData.negativePrompt"
      @close="closePromptModal"
      @copy="handlePromptCopy"
    />
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/store/task'
import { useAuthStore } from '@/store/auth'
import { formatDate } from '@/utils/date'
import { downloadFilesAsZip } from '@/utils/file'
import { debounce, throttle } from '@/utils/performance'
import { switchToVideoMode } from '@/services/imageToVideo'
import ImageWithRetry from '@/components/common/ImageWithRetry.vue'
import PromptDetailsModal from '@/components/common/PromptDetailsModal.vue'
import VirtualScroller from '@/components/common/VirtualScroller.vue'

export default {
  name: 'GalleryGrid',
  components: {
    ImageWithRetry,
    PromptDetailsModal,
    VirtualScroller
  },

  setup() {
    const taskStore = useTaskStore()
    const authStore = useAuthStore()
    const router = useRouter()
    const previewUrl = ref(null)

    // 批量下载相关状态
    const isDownloading = ref(false)
    const downloadProgress = ref({
      show: false,
      percentage: 0,
      text: ''
    })

    // 重新加载相关状态
    const isReloading = ref(false)

    // 提示词详情模态框状态
    const promptModalVisible = ref(false)
    const promptModalData = ref({
      prompt: '',
      negativePrompt: ''
    })

    // 虚拟滚动配置
    const virtualScrollEnabled = ref(true)
    const virtualScrollConfig = ref({
      itemHeight: 400, // 每个批次的高度
      containerHeight: 800, // 容器高度
      overscan: 3 // 预渲染项目数
    })

    // 计算属性：获取任务列表并按批次分组
    const tasks = computed(() => taskStore.tasks)
    const batches = computed(() => {
      const tasksByBatch = {}
      tasks.value.forEach(task => {
        const batchId = task.batch_id || `single_${task.id}`
        if (!tasksByBatch[batchId]) {
          tasksByBatch[batchId] = {
            id: batchId,
            ...task,
            tasks: []
          }
        }
        tasksByBatch[batchId].tasks.push(task)
      })
      return Object.values(tasksByBatch).sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    })

    // 状态文本映射
    const getStatusText = (status) => {
      const statusMap = {
        'queued': '排队中',
        'processing': '生成中',
        'completed': '已完成',
        'failed': '失败'
      }
      return statusMap[status] || status
    }

    // 获取批次分辨率
    const getBatchResolution = (batch) => {
      if (batch.width && batch.height) {
        return `${batch.width}×${batch.height}`
      }
      // 从任务参数中获取分辨率
      if (batch.tasks && batch.tasks.length > 0) {
        const task = batch.tasks[0]
        if (task.width && task.height) {
          return `${task.width}×${task.height}`
        }
        // 从参数中解析
        if (task.parameters) {
          const params = typeof task.parameters === 'string' ? JSON.parse(task.parameters) : task.parameters
          if (params.width && params.height) {
            return `${params.width}×${params.height}`
          }
        }
      }
      return '1024×1024' // 默认分辨率
    }

    // 显示提示词详情
    const showPromptDetails = (prompt, negativePrompt) => {
      promptModalData.value = {
        prompt: prompt || '',
        negativePrompt: negativePrompt || ''
      }
      promptModalVisible.value = true
    }

    // 关闭提示词详情模态框
    const closePromptModal = () => {
      promptModalVisible.value = false
    }

    // 处理复制事件
    const handlePromptCopy = (data) => {
      console.log('复制成功:', data.type, data.text)
      // 这里可以添加成功提示
    }

    // 图片预览
    const showImagePreview = (url) => {
      previewUrl.value = url
    }

    const closePreview = () => {
      previewUrl.value = null
    }

    // 下载图片
    const downloadImage = async (taskId, index) => {
      try {
        await taskStore.downloadImage(taskId, index)
      } catch (error) {
        console.error('下载失败:', error)
        alert('下载失败：' + error.message)
      }
    }

    // 处理图生视频
    const handleImageToVideo = async (taskId, index) => {
      try {
        // 显示加载状态
        const loadingToast = showLoadingToast('正在切换到图生视频模式...')

        // 获取原始任务的提示词
        const task = tasks.value.find(t => t.id === taskId)
        const originalPrompt = task?.prompt || ''

        // 使用图生视频服务切换模式
        await switchToVideoMode(taskId, index, originalPrompt)

        // 隐藏加载状态
        hideLoadingToast(loadingToast)

        // 显示成功提示
        showSuccessToast('已切换到图生视频模式，可以开始生成视频！')

      } catch (error) {
        console.error('切换到图生视频模式失败:', error)
        showErrorToast(error.message || '切换失败，请重试')
      }
    }

    // 图片加载处理函数
    const handleImageLoad = (img) => {
      // console.log('图片加载成功:', img.src)
    }

    const handleImageError = (error) => {
      // console.error('图片加载失败:', error)
    }

    const handleImageRetry = () => {
      // console.log('重试加载图片')
    }

    const handleAuthError = (error) => {
      // console.error('图片认证失败:', error)
      // 清除认证状态并跳转到登录页
      authStore.logout()
      router.push('/login')
    }

    // 虚拟滚动处理函数
    const handleVirtualScroll = throttle((data) => {
      console.log('虚拟滚动:', data.scrollTop, '可见项:', data.isScrolling ? '滚动中' : '静止')
    }, 100)

    const handleVisibleChange = debounce((data) => {
      console.log('可见范围变化:', data.startIndex, '-', data.endIndex)
    }, 200)

    // 提示消息函数
    const showLoadingToast = (message) => {
      // 创建加载提示
      const toast = document.createElement('div')
      toast.className = 'toast toast-loading'
      toast.innerHTML = `
        <i class="fas fa-spinner fa-spin"></i>
        <span>${message}</span>
      `
      document.body.appendChild(toast)

      // 添加显示动画
      setTimeout(() => toast.classList.add('show'), 10)

      return toast
    }

    const hideLoadingToast = (toast) => {
      if (toast && toast.parentNode) {
        toast.classList.remove('show')
        setTimeout(() => {
          if (toast.parentNode) {
            toast.parentNode.removeChild(toast)
          }
        }, 300)
      }
    }

    const showSuccessToast = (message) => {
      const toast = document.createElement('div')
      toast.className = 'toast toast-success'
      toast.innerHTML = `
        <i class="fas fa-check-circle"></i>
        <span>${message}</span>
      `
      document.body.appendChild(toast)

      setTimeout(() => toast.classList.add('show'), 10)
      setTimeout(() => {
        toast.classList.remove('show')
        setTimeout(() => {
          if (toast.parentNode) {
            toast.parentNode.removeChild(toast)
          }
        }, 300)
      }, 3000)
    }

    const showErrorToast = (message) => {
      const toast = document.createElement('div')
      toast.className = 'toast toast-error'
      toast.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <span>${message}</span>
      `
      document.body.appendChild(toast)

      setTimeout(() => toast.classList.add('show'), 10)
      setTimeout(() => {
        toast.classList.remove('show')
        setTimeout(() => {
          if (toast.parentNode) {
            toast.parentNode.removeChild(toast)
          }
        }, 300)
      }, 5000)
    }

    const handlePreviewLoad = (img) => {
      console.log('预览图片加载成功:', img.src)
    }

    const handlePreviewError = (error) => {
      console.error('预览图片加载失败:', error)
    }

    const handlePreviewRetry = () => {
      console.log('重试加载预览图片')
    }

    // 批量下载所有图片
    const downloadAllImages = async (batch) => {
      if (!batch.resultUrls || batch.resultUrls.length === 0) {
        console.error('没有可下载的图片')
        return
      }

      try {
        isDownloading.value = true
        downloadProgress.value = {
          show: true,
          percentage: 0,
          text: '准备下载...'
        }

        // 准备文件列表
        const files = batch.resultUrls.map((url, index) => ({
          url: url,
          filename: `image_${batch.id}_${index + 1}.png`
        }))

        // 使用工具函数下载
        await downloadFilesAsZip(files, `images_${batch.id}.zip`, {
          headers: {
            'Authorization': `Bearer ${authStore.token}`
          },
          onProgress: ({ completed, total, percentage }) => {
            downloadProgress.value = {
              show: true,
              percentage: percentage,
              text: `下载中... ${completed}/${total}`
            }
          }
        })

        // 下载完成
        downloadProgress.value = {
          show: true,
          percentage: 100,
          text: '下载完成！'
        }

        // 2秒后隐藏进度条
        setTimeout(() => {
          downloadProgress.value.show = false
        }, 2000)

        console.log('批量下载完成')
      } catch (error) {
        console.error('批量下载失败:', error)
        downloadProgress.value = {
          show: true,
          percentage: 0,
          text: '下载失败: ' + error.message
        }

        // 3秒后隐藏错误信息
        setTimeout(() => {
          downloadProgress.value.show = false
        }, 3000)
      } finally {
        isDownloading.value = false
      }
    }

    // 重新加载批次
    const reloadBatch = async (batch) => {
      // 尝试获取任务ID，支持多种字段名
      const taskId = batch.task_id || batch.id || (batch.tasks && batch.tasks[0] && (batch.tasks[0].task_id || batch.tasks[0].id))

      if (!taskId) {
        console.error('批次缺少task_id，批次数据:', batch)
        alert('无法重新加载：缺少任务ID')
        return
      }

      try {
        isReloading.value = true
        console.log('重新加载任务:', taskId)

        await taskStore.reloadTask(taskId)

        // 显示成功消息
        console.log('任务重新加载成功')

      } catch (error) {
        console.error('重新加载任务失败:', error)
        // 这里可以添加错误提示
        alert('重新加载失败: ' + error.message)
      } finally {
        isReloading.value = false
      }
    }

    return {
      tasks,
      batches,
      previewUrl,
      authStore,
      isDownloading,
      downloadProgress,
      isReloading,
      promptModalVisible,
      promptModalData,
      virtualScrollEnabled,
      virtualScrollConfig,
      formatDate,
      getStatusText,
      getBatchResolution,
      showPromptDetails,
      closePromptModal,
      handlePromptCopy,
      showImagePreview,
      closePreview,
      downloadImage,
      downloadAllImages,
      reloadBatch,
      handleImageToVideo,
      handleImageLoad,
      handleImageError,
      handleImageRetry,
      handleAuthError,
      handlePreviewLoad,
      handlePreviewError,
      handlePreviewRetry,
      handleVirtualScroll,
      handleVisibleChange
    }
  }
}
</script>

<style scoped>
.gallery-grid {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 0;
}

.gallery-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
  background: var(--surface-1);
  border-radius: 24px;
  border: 1px solid var(--border-1);
}

.gallery-empty i {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.gallery-empty h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.gallery-empty p {
  font-size: 14px;
  opacity: 0.8;
}

.batch-container {
  width: 100%;
  margin: 0 0 32px 0;
  background: var(--surface-1);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 0;
  border: 1px solid var(--border-1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.batch-container:hover {
  transform: translateY(-4px);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.4);
  border-color: var(--border-2);
}

.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border-1);
}

.batch-info {
  flex: 1;
}

.batch-meta {
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  gap: 16px;
  align-items: center;
}

.batch-date {
  font-weight: 600;
  color: var(--text-primary);
}

.batch-resolution {
  color: var(--text-muted);
}

.batch-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.batch-status.status-completed {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.batch-status.status-processing {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.batch-status.status-queued {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.batch-status.status-failed {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.batch-progress-text {
  color: var(--primary);
  font-weight: 600;
}

.batch-progress {
  padding: 0;
  background: transparent;
  border: none;
}

.progress-bar {
  width: 100%;
  height: 3px;
  background: var(--surface-3);
  border-radius: 0;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 0;
  transition: width 0.3s ease;
}

.batch-images {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  padding: 24px;
  width: 100%;
}

.batch-image-item {
  position: relative;
  aspect-ratio: 1;
  min-height: 280px;
}

.batch-image-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: var(--surface-2);
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid var(--border-1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.batch-image-container:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
  border-color: var(--primary);
}

.batch-image-container img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.batch-image-container:hover img {
  transform: scale(1.05);
}

.batch-image-index {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  z-index: 2;
  min-width: 24px;
  text-align: center;
}

.batch-image-actions {
  position: absolute;
  bottom: 8px;
  right: 8px;
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 2;
}

.batch-image-container:hover .batch-image-actions {
  opacity: 1;
}

.batch-image-action {
  background: rgba(0, 0, 0, 0.7);
  border: none;
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.batch-image-action:hover {
  background: var(--primary);
  transform: scale(1.1);
}

.loading-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  gap: 8px;
}

.loading-placeholder i {
  font-size: 32px;
  opacity: 0.5;
}

.loading-placeholder .spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--surface-3);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--surface-2);
  color: var(--error);
}

.error-placeholder i {
  font-size: 24px;
}

.error-placeholder span {
  font-size: 14px;
}

.btn-retry {
  margin-top: 8px;
  padding: 8px 16px;
  background: var(--surface-3);
  border: 1px solid var(--border-1);
  border-radius: 8px;
  color: var(--text-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  transition: all 0.2s ease;
}

.btn-retry:hover {
  background: var(--surface-2);
  transform: translateY(-1px);
}

.batch-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  justify-content: flex-end;
}

.batch-download-btn {
  background: var(--primary);
  border: none;
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.batch-download-btn:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-1px);
}

.batch-download-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.reload-btn {
  background: var(--secondary);
  border: none;
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-right: 8px;
}

.reload-btn:hover:not(:disabled) {
  background: var(--secondary-hover);
  transform: translateY(-1px);
}

.reload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.download-progress {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--surface-2);
  border-radius: 12px;
  border: 1px solid var(--border-1);
}

.download-progress .progress-bar {
  width: 100%;
  height: 6px;
  background: var(--surface-3);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.download-progress .progress-fill {
  height: 100%;
  background: var(--primary-gradient);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.download-progress .progress-text {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* 虚拟滚动优化 */
.virtual-batch-item {
  contain: layout style paint;
  will-change: transform;
}

.virtual-batch-item .batch-image-item {
  contain: layout style paint;
}

/* 懒加载图片样式 */
.lazy-image {
  opacity: 0;
  transition: opacity 0.3s ease;
}

.lazy-loading {
  opacity: 0.5;
  background: var(--surface-2);
}

.lazy-loaded {
  opacity: 1;
}

.lazy-error {
  opacity: 0.3;
  background: var(--surface-3);
}

/* 性能优化：减少重绘 */
.batch-image-container {
  transform: translateZ(0);
  backface-visibility: hidden;
}

.batch-image-actions {
  transform: translateZ(0);
}

/* 滚动性能优化 */
.gallery-grid {
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
}

/* 减少动画在滚动时的性能影响 */
.gallery-grid.scrolling .batch-image-container {
  pointer-events: none;
}

.gallery-grid.scrolling .batch-image-actions {
  opacity: 0;
  transition: none;
}

/* Toast 消息样式 */
:global(.toast) {
  position: fixed;
  top: 20px;
  right: 20px;
  background: var(--surface-1);
  border: 1px solid var(--border-1);
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  z-index: 10000;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 300px;
  transform: translateX(100%);
  opacity: 0;
  transition: all 0.3s ease;
}

:global(.toast.show) {
  transform: translateX(0);
  opacity: 1;
}

:global(.toast-loading) {
  background: var(--surface-2);
  border-color: var(--primary);
}

:global(.toast-loading i) {
  color: var(--primary);
}

:global(.toast-success) {
  background: var(--surface-2);
  border-color: var(--success);
}

:global(.toast-success i) {
  color: var(--success);
}

:global(.toast-error) {
  background: var(--surface-2);
  border-color: var(--error);
}

:global(.toast-error i) {
  color: var(--error);
}

:global(.toast span) {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  cursor: pointer;
}

.modal-content {
  max-width: 90vw;
  max-height: 90vh;
  background: var(--surface-1);
  border-radius: 12px;
  padding: 20px;
  position: relative;
  cursor: default;
}

.modal-content img {
  max-width: 100%;
  max-height: 80vh;
  border-radius: 8px;
}

.modal-close {
  position: absolute;
  top: 12px;
  right: 12px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 24px;
  padding: 4px;
  transition: color 0.2s ease;
}

.modal-close:hover {
  color: var(--text-primary);
}

.modal-header {
  margin-bottom: 20px;
}

.modal-header h3 {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 600;
}

/* 图片预览模态框 */
.image-preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
}

.image-preview-modal.active {
  opacity: 1;
  visibility: visible;
}

.image-preview-content {
  max-width: 90%;
  max-height: 90vh;
  position: relative;
}

.image-preview-content img {
  max-width: 100%;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.image-preview-close {
  position: absolute;
  top: -40px;
  right: 0;
  color: white;
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 8px;
  transition: color 0.3s ease;
}

.image-preview-close:hover {
  color: var(--primary);
}

.prompt-section {
  margin-bottom: 20px;
}

.prompt-section h4 {
  color: var(--text-secondary);
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
}

.prompt-section p {
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 响应式设计 */
@media (min-width: 1400px) {
  .batch-images {
    grid-template-columns: repeat(4, 1fr);
    gap: 32px;
    padding: 32px;
  }
}

@media (max-width: 1399px) and (min-width: 1000px) {
  .batch-images {
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
    padding: 24px;
  }
}

@media (max-width: 999px) and (min-width: 768px) {
  .batch-images {
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    padding: 20px;
  }

  .batch-image-item {
    min-height: 220px;
  }
}

@media (max-width: 767px) {
  .batch-images {
    grid-template-columns: repeat(2, 1fr);
    gap: 18px;
    padding: 18px;
  }

  .batch-image-item {
    min-height: 180px;
  }

  .batch-header {
    padding: 16px 20px;
  }

  .batch-meta {
    font-size: 12px;
    gap: 10px;
    flex-wrap: wrap;
  }

  .batch-download-btn,
  .reload-btn {
    padding: 6px 12px;
    font-size: 12px;
  }
}


</style> 