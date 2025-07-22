<template>
  <div class="batch-container" :data-batch-id="batch.id">
    <!-- 批次头部 -->
    <div class="batch-header">
      <div class="batch-info">
        <div class="batch-meta">
          <span>{{ formatDate(batch.created_at) }}</span>
          <span v-if="firstTask">{{ firstTask.width }}x{{ firstTask.height }}</span>
          <span :class="['batch-status', `status-${batch.status}`]">
            {{ getStatusText(batch.status) }}
          </span>
          <button 
            class="btn btn-text" 
            @click="showPromptDetails(batch.prompt, firstTask?.negative_prompt)"
          >
            <i class="fas fa-info-circle"></i>
          </button>
        </div>
      </div>

      <!-- 下载按钮 -->
      <div v-if="batch.status === 'completed'" class="batch-actions">
        <button class="btn btn-secondary" @click="downloadAllImages">
          <i class="fas fa-download"></i>
          全部下载
        </button>
      </div>
    </div>

    <!-- 进度条 -->
    <div v-if="['processing', 'queued'].includes(batch.status)" class="batch-progress">
      <div class="progress-info">
        <div class="progress-status">
          <i :class="batch.status === 'processing' ? 'fas fa-spinner fa-spin' : 'fas fa-clock'"></i>
          <span>{{ batch.status === 'processing' ? '正在生成...' : '等待中...' }}</span>
        </div>
        <div class="progress-percentage">
          {{ batch.status === 'processing' ? `${Math.round(batch.progress)}%` : '排队中' }}
        </div>
      </div>
      <div class="progress-bar">
        <div 
          class="progress-fill" 
          :style="{ width: batch.status === 'processing' ? `${batch.progress}%` : '0%' }"
        ></div>
      </div>
    </div>

    <!-- 图片网格 -->
    <div class="batch-images">
      <template v-if="batch.status === 'completed' && batch.tasks.length">
        <div 
          v-for="(task, index) in batch.tasks" 
          :key="task.id"
          class="batch-image-item"
          :data-task-id="task.id"
          :data-image-index="index"
        >
          <div 
            class="batch-image-container" 
            @click="showImagePreview(getDownloadUrl(task.id, index))"
          >
            <div class="loading-indicator">
              <div class="loading"></div>
              <span>加载中...</span>
            </div>
            <img 
              :src="getDownloadUrl(task.id, index)"
              :alt="`生成结果 ${index + 1}`"
              loading="lazy"
              @load="handleImageLoad"
              @error="handleImageError"
            >
            <div class="batch-image-index">#{{ index + 1 }}</div>
            <div class="batch-image-actions">
              <button 
                class="batch-image-action"
                @click.stop="downloadImage(task.id, index)"
              >
                <i class="fas fa-download"></i>
              </button>
              <button 
                class="batch-image-action"
                @click.stop="handleImageToVideo(task.id, index)"
              >
                <i class="fas fa-film"></i>
              </button>
            </div>
          </div>
        </div>
      </template>
      <template v-else>
        <div 
          v-for="index in 4" 
          :key="index"
          class="batch-image-item"
        >
          <div class="batch-image-container">
            <div class="loading-placeholder">
              <i class="fas fa-image"></i>
              <span>等待生成...</span>
            </div>
            <div class="batch-image-index">#{{ index }}</div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'
import { useAuthStore } from '@/store/auth'
import { formatDate } from '@/utils/date'
import { showSuccess, showError } from '@/utils/notification'
import JSZip from 'jszip'

export default {
  name: 'BatchContainer',

  props: {
    batch: {
      type: Object,
      required: true
    }
  },

  emits: ['retry'],

  setup(props) {
    const authStore = useAuthStore()
    const firstTask = computed(() => props.batch.tasks[0])

    // 获取下载URL
    const getDownloadUrl = (taskId, index) => {
      return `${authStore.apiBase}/v2/tasks/${taskId}/download?index=${index}`
    }

    // 获取状态文本
    const getStatusText = (status) => {
      const statusMap = {
        'queued': '排队中',
        'processing': '生成中',
        'completed': '已完成',
        'failed': '失败',
        'cancelled': '已取消'
      }
      return statusMap[status] || status
    }

    // 显示提示词详情
    const showPromptDetails = (prompt, negativePrompt) => {
      const modal = document.createElement('div')
      modal.className = 'modal'
      modal.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <h3>提示词详情</h3>
            <button class="modal-close">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="modal-body">
            <div class="prompt-section">
              <h4>正向提示词</h4>
              <p>${prompt || '无'}</p>
            </div>
            <div class="prompt-section">
              <h4>反向提示词</h4>
              <p>${negativePrompt || '无'}</p>
            </div>
          </div>
        </div>
      `
      document.body.appendChild(modal)

      // 关闭按钮事件
      const closeBtn = modal.querySelector('.modal-close')
      closeBtn.onclick = () => modal.remove()

      // 点击背景关闭
      modal.onclick = (e) => {
        if (e.target === modal) modal.remove()
      }
    }

    // 下载单张图片
    const downloadImage = async (taskId, index) => {
      try {
        const response = await fetch(getDownloadUrl(taskId, index), {
          headers: {
            'Authorization': `Bearer ${authStore.token}`
          }
        })

        if (!response.ok) throw new Error('下载失败')

        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `image_${taskId}_${index}.png`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        showSuccess('图片下载完成')
      } catch (error) {
        console.error('下载图片失败:', error)
        showError('下载失败: ' + error.message)
      }
    }

    // 下载所有图片
    const downloadAllImages = async () => {
      try {
        const zip = new JSZip()
        const promises = props.batch.tasks.map(async (task, index) => {
          const response = await fetch(getDownloadUrl(task.id, index), {
            headers: {
              'Authorization': `Bearer ${authStore.token}`
            }
          })
          const blob = await response.blob()
          zip.file(`image_${task.id}_${index}.png`, blob)
        })

        await Promise.all(promises)
        const zipBlob = await zip.generateAsync({ type: 'blob' })
        const url = window.URL.createObjectURL(zipBlob)
        const a = document.createElement('a')
        a.href = url
        a.download = `images_${props.batch.id}.zip`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        showSuccess('所有图片已打包下载')
      } catch (error) {
        console.error('下载所有图片失败:', error)
        showError('下载失败: ' + error.message)
      }
    }

    // 处理图片加载
    const handleImageLoad = (event) => {
      const img = event.target
      const container = img.closest('.batch-image-container')
      const loadingIndicator = container.querySelector('.loading-indicator')
      
      img.style.opacity = '1'
      if (loadingIndicator) {
        loadingIndicator.style.opacity = '0'
        setTimeout(() => loadingIndicator.remove(), 300)
      }
    }

    // 处理图片加载错误
    const handleImageError = (event) => {
      const img = event.target
      const container = img.closest('.batch-image-container')
      const loadingIndicator = container.querySelector('.loading-indicator')
      
      if (loadingIndicator) {
        loadingIndicator.innerHTML = `
          <i class="fas fa-exclamation-circle"></i>
          <span>加载失败</span>
          <button class="btn-retry" onclick="this.closest('.batch-image-container').querySelector('img').src = this.closest('.batch-image-container').querySelector('img').src">
            <i class="fas fa-redo"></i> 重试
          </button>
        `
      }
    }

    // 处理图生视频
    const handleImageToVideo = (taskId, index) => {
      // 触发父组件的事件处理
      emit('image-to-video', { taskId, index })
    }

    return {
      firstTask,
      formatDate,
      getDownloadUrl,
      getStatusText,
      showPromptDetails,
      downloadImage,
      downloadAllImages,
      handleImageLoad,
      handleImageError,
      handleImageToVideo
    }
  }
}
</script>

<style scoped>
.batch-container {
  background: var(--surface-1);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 24px;
  border: 1px solid var(--border-1);
}

.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-1);
}

.batch-info {
  flex: 1;
}

.batch-meta {
  font-size: 13px;
  color: var(--text-muted);
  display: flex;
  gap: 16px;
  align-items: center;
}

.batch-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-completed { background: rgba(16, 185, 129, 0.2); color: var(--success); }
.status-processing { background: rgba(99, 102, 241, 0.2); color: var(--accent); }
.status-queued { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
.status-failed { background: rgba(239, 68, 68, 0.2); color: var(--error); }

.batch-progress {
  padding: 12px 16px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border-1);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.progress-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background: var(--surface-3);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.batch-images {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  padding: 16px;
}

.batch-image-item {
  position: relative;
}

.batch-image-container {
  position: relative;
  width: 100%;
  padding-bottom: 100%;
  background: var(--surface-2);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
}

.batch-image-container img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.loading-indicator,
.loading-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  color: var(--text-secondary);
  transition: opacity 0.3s ease;
}

.loading-placeholder i {
  font-size: 32px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.batch-image-index {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  z-index: 2;
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

.btn-retry {
  margin-top: 12px;
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

.btn-retry i {
  font-size: 14px;
}

@media (max-width: 768px) {
  .batch-container {
    padding: 16px;
  }

  .batch-images {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    padding: 12px;
  }
}
</style>

<!-- 在 template 中的 batch-image-container 内添加图片预览遮罩 -->
<div class="batch-image-overlay"></div>

<!-- 在 script 中补充图片预览功能 -->
<script setup>

// 图片预览功能
const showImagePreview = (imageUrl) => {
  const modal = document.createElement('div')
  modal.className = 'image-preview-modal'
  modal.innerHTML = `
    <div class="image-preview-content">
      <img src="${imageUrl}" alt="预览图片">
      <button class="image-preview-close">
        <i class="fas fa-times"></i>
      </button>
    </div>
  `
  document.body.appendChild(modal)

  // 添加激活类以显示模态框
  setTimeout(() => modal.classList.add('active'), 10)

  // 关闭按钮事件
  const closeBtn = modal.querySelector('.image-preview-close')
  closeBtn.onclick = () => {
    modal.classList.remove('active')
    setTimeout(() => modal.remove(), 300)
  }

  // 点击背景关闭
  modal.onclick = (e) => {
    if (e.target === modal) {
      modal.classList.remove('active')
      setTimeout(() => modal.remove(), 300)
    }
  }
}

// 图片加载状态处理优化
const handleImageLoad = (event) => {
  const container = event.target.closest('.batch-image-container')
  const loadingIndicator = container.querySelector('.loading-indicator')
  const img = event.target
  
  // 淡入显示图片
  img.style.opacity = '0'
  setTimeout(() => {
    loadingIndicator.style.opacity = '0'
    img.style.opacity = '1'
    setTimeout(() => {
      loadingIndicator.style.display = 'none'
    }, 300)
  }, 100)
}
</script>