<template>
  <div>
    <!-- Toast 通知 -->
    <div v-if="toast.show" class="toast-notification" :class="toast.type">
      <i :class="toast.icon"></i>
      <span>{{ toast.message }}</span>
      <button @click="hideToast" class="toast-close">
        <i class="fas fa-times"></i>
      </button>
    </div>
<!-- 
    <div v-if="showHintBar" class="input-hint-bar" @mouseenter="handleExpand" @click="handleExpand">
      <span><i class="fas fa-chevron-up"></i> 展开输入栏</span>
    </div> -->
    <div class="input-panel" :class="{ 'auto-hidden': isAutoHidden, 'fully-hidden': isFullyHidden, 'collapsed': collapsed }" ref="inputPanelRef">
      <div v-if="collapsed" class="input-collapsed-bar" @mouseenter="handleExpand" @click="handleExpand">
        <textarea class="prompt-input collapsed" placeholder="输入你的创意提示词..." readonly></textarea>
      </div>
      <div v-else class="input-container">
        <div class="input-hint">向上滑动显示输入栏</div>
        <form @submit.prevent="handleSubmit">
          <!-- 模式选择 -->
          <div class="mode-select-container">
            <div class="mode-select-group">
              <label class="mode-select-label">创作类型</label>
              <select class="mode-select" v-model="mode" @focus="handleFocus" @blur="handleBlur">
                <option value="text-to-image">📷 图片生成</option>
                <option value="image-to-video">🎬 视频生成</option>
              </select>
            </div>
          </div>

          <!-- 图片上传区域 -->
          <div v-if="mode === 'image-to-video'" class="image-upload-container">
            <div v-if="!uploadedImage" class="image-upload-area" @click="triggerUpload" @dragover.prevent="handleDragOver" @dragleave.prevent="handleDragLeave" @drop.prevent="handleDrop">
              <div class="upload-icon">
                <i class="fas fa-cloud-upload-alt"></i>
              </div>
              <div class="upload-text">点击或拖拽上传图片</div>
              <div class="upload-hint">支持 JPG、PNG、WebP 格式，最大 10MB</div>
            </div>
            <div v-else class="uploaded-image-preview">
              <AuthImage :src="uploadedImage.url" alt="预览图片" />
              <div class="image-preview-overlay">
                <button class="preview-btn" @click="removeUploadedImage">
                  <i class="fas fa-times"></i>
                </button>
              </div>
            </div>
            <input type="file" ref="fileInput" @change="handleFileSelect" accept="image/*" style="display: none">
          </div>

          <!-- 参数控制面板 -->
          <div v-if="mode === 'text-to-image'" class="controls-panel">
            <div class="control-group">
              <label class="control-label">工作流类型</label>
              <select class="control-select" v-model="workflow" @focus="handleFocus" @blur="handleBlur">
                <option value="sd_basic">SD Basic - 基础文生图 (512x512)</option>
                <option value="sdxl_basic">SDXL Basic - 高分辨率文生图 (832x1480)</option>
              </select>
            </div>
            <div class="control-group">
              <label class="control-label">模型选择</label>
              <select class="control-select" v-model="model" @focus="handleFocus" @blur="handleBlur">
                <option v-for="model in availableModels" :key="model.path" :value="model.path">
                  {{ model.description }}
                </option>
              </select>
            </div>
            <div class="control-group">
              <label class="control-label">宽度</label>
              <select class="control-select" v-model="width" @focus="handleFocus" @blur="handleBlur">
                <option value="512">512</option>
                <option value="768">768</option>
                <option value="832">832</option>
                <option value="1024">1024</option>
                <option value="1216">1216</option>
                <option value="1344">1344</option>
              </select>
            </div>
            <div class="control-group">
              <label class="control-label">高度</label>
              <select class="control-select" v-model="height" @focus="handleFocus" @blur="handleBlur">
                <option value="512">512</option>
                <option value="768">768</option>
                <option value="832">832</option>
                <option value="1024">1024</option>
                <option value="1216">1216</option>
                <option value="1480">1480</option>
              </select>
            </div>
            <div class="control-group">
              <label class="control-label">随机种子</label>
              <div style="display: flex; gap: 8px;">
                <input type="number" class="control-input" v-model="seed" placeholder="-1 (随机)" @focus="handleFocus" @blur="handleBlur">
                <button type="button" @click="generateRandomSeed" class="btn-icon">
                  <i class="fas fa-dice"></i>
                </button>
              </div>
            </div>
          </div>

          <!-- 提示词输入 -->
          <div class="prompt-input-group">
            <textarea
              class="prompt-input"
              v-model="prompt"
              :placeholder="mode === 'text-to-image' ? '输入你的创意提示词... (Ctrl+Enter 快速生成)' : '描述你希望视频中发生的动作或场景变化...'"
              rows="3"
              required
              @keydown.ctrl.enter="handleSubmit"
              @focus="handleFocus"
              @blur="handleBlur"
            ></textarea>
          </div>

          <!-- 负面提示词 -->
          <div class="prompt-input-group">
            <textarea
              class="prompt-input"
              v-model="negativePrompt"
              placeholder="负面提示词 (可选) - 描述你不想在图片中看到的内容"
              rows="1"
              @focus="handleFocus"
              @blur="handleBlur"
            ></textarea>
            <button type="submit" class="generate-btn" :disabled="isGenerating || !isFormValid">
              <span v-if="isGenerating" class="loading-spinner"></span>
              <i v-else :class="mode === 'text-to-image' ? 'fas fa-magic' : 'fas fa-video'"></i>
              {{ isGenerating ? '生成中...' : (mode === 'text-to-image' ? '生成图片' : '生成视频') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '@/store/task'
import { useAuthStore } from '@/store/auth'
import AuthImage from '@/components/common/AuthImage.vue'

// 工具函数：防抖
const debounce = (func, wait) => {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// 工具函数：节流
const throttle = (func, limit) => {
  let inThrottle
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args)
      inThrottle = true
      setTimeout(() => inThrottle = false, limit)
    }
  }
}

export default {
  name: 'InputPanel',
  components: {
    AuthImage
  },
  setup() {
    const taskStore = useTaskStore()
    const authStore = useAuthStore()
    const fileInput = ref(null)

    // 面板状态 - 简化状态管理
    const panelState = ref('normal') // 'normal', 'collapsed', 'hidden'
    const inputPanelRef = ref(null)
    const showHintBar = ref(false)
    const isUserInteracting = ref(false)

    // Toast 通知系统
    const toast = ref({
      show: false,
      message: '',
      type: 'info', // 'success', 'error', 'warning', 'info'
      icon: 'fas fa-info-circle'
    })

    // 定时器管理
    const timers = {
      scroll: null,
      interaction: null,
      blur: null,
      toast: null
    }

    let lastScrollY = 0
    let scrollDirection = 'up'

    // 清理定时器的工具函数
    const clearTimer = (timerName) => {
      if (timers[timerName]) {
        clearTimeout(timers[timerName])
        timers[timerName] = null
      }
    }

    const clearAllTimers = () => {
      Object.keys(timers).forEach(clearTimer)
    }

    // 面板状态管理 - 优化版本
    const panelController = {
      // 面板状态常量
      STATES: {
        NORMAL: 'normal',
        COLLAPSED: 'collapsed',
        HIDDEN: 'hidden'
      },

      // 显示面板
      show(immediate = false) {
        panelState.value = this.STATES.NORMAL
        showHintBar.value = false
        clearTimer('scroll')

        if (immediate) {
          clearTimer('interaction')
        }
      },

      // 隐藏面板
      hide(force = false) {
        if (force || !isUserInteracting.value) {
          panelState.value = this.STATES.COLLAPSED
          this.scheduleHintBar()
        }
      },

      // 完全隐藏面板
      fullHide() {
        panelState.value = this.STATES.HIDDEN
        showHintBar.value = false
      },

      // 切换面板状态
      toggle() {
        if (panelState.value === this.STATES.NORMAL) {
          this.hide(true)
        } else {
          this.show(true)
        }
      },

      // 检查面板状态
      isNormal() {
        return panelState.value === this.STATES.NORMAL
      },

      isCollapsed() {
        return panelState.value === this.STATES.COLLAPSED
      },

      isHidden() {
        return panelState.value === this.STATES.HIDDEN
      },

      // 延迟显示提示条
      scheduleHintBar(delay = 1500) {
        clearTimer('scroll')
        timers.scroll = setTimeout(() => {
          if (this.isCollapsed() && !isUserInteracting.value) {
            showHintBar.value = true
          }
        }, delay)
      }
    }

    // 简化的面板控制函数
    const showInputPanel = () => panelController.show()
    const hideInputPanel = () => panelController.hide()

    // 焦点处理 - 重构版本
    const handleFocus = () => {
      interactionManager.startInteraction()
      clearTimer('blur')
    }

    const handleBlur = () => {
      clearTimer('blur')
      timers.blur = setTimeout(() => {
        if (!interactionManager.hasActiveFocus()) {
          interactionManager.endInteraction()
          showHintBar.value = false
        }
      }, interactionManager.CONFIG.BLUR_DELAY)
    }

    // 滚动行为管理器
    const scrollManager = {
      // 滚动阈值配置
      THRESHOLDS: {
        NEAR_BOTTOM: 200,
        HINT_DELAY: 1500
      },

      // 检查是否接近底部
      isNearBottom(scrollY = window.scrollY) {
        const windowHeight = window.innerHeight
        const documentHeight = document.documentElement.scrollHeight
        return scrollY + windowHeight > documentHeight - this.THRESHOLDS.NEAR_BOTTOM
      },

      // 处理向下滚动
      handleScrollDown() {
        if (!isUserInteracting.value && panelController.isNormal()) {
          panelController.hide()
        }
      },

      // 处理向上滚动
      handleScrollUp(currentScrollY) {
        if (!isUserInteracting.value && panelController.isCollapsed()) {
          if (this.isNearBottom(currentScrollY)) {
            panelController.show()
          }
        }
      }
    }

    // 智能滚动处理 - 重构版本
    const handleScroll = throttle(() => {
      const currentScrollY = window.scrollY
      const newDirection = currentScrollY > lastScrollY ? 'down' : 'up'

      // 只在滚动方向改变时处理
      if (newDirection !== scrollDirection) {
        scrollDirection = newDirection

        if (scrollDirection === 'down') {
          scrollManager.handleScrollDown()
        } else {
          scrollManager.handleScrollUp(currentScrollY)
        }
      }

      lastScrollY = currentScrollY

      // 延迟显示提示条
      if (panelController.isCollapsed()) {
        panelController.scheduleHintBar()
      }
    }, 100)

    // 鼠标交互管理器
    const mouseManager = {
      // 鼠标位置阈值配置
      THRESHOLDS: {
        SHOW_DISTANCE: 80,      // 距离底部多少像素时显示面板
        HIDE_DISTANCE: 150,     // 距离底部多少像素时隐藏面板
        PANEL_MARGIN: 20,       // 面板上方的边距
        SAFE_ZONE: 200          // 安全区域高度
      },

      // 计算鼠标距离底部的距离
      getDistanceFromBottom(clientY) {
        return window.innerHeight - clientY
      },

      // 检查鼠标是否在面板区域内
      isMouseInPanelArea(clientY) {
        if (!inputPanelRef.value) return false
        const inputRect = inputPanelRef.value.getBoundingClientRect()
        return clientY >= inputRect.top - this.THRESHOLDS.PANEL_MARGIN
      },

      // 检查是否应该显示面板
      shouldShowPanel(clientY) {
        const distance = this.getDistanceFromBottom(clientY)
        return distance < this.THRESHOLDS.SHOW_DISTANCE && panelController.isCollapsed()
      },

      // 检查是否应该隐藏面板
      shouldHidePanel(clientY) {
        const distance = this.getDistanceFromBottom(clientY)
        const isInSafeZone = clientY < window.innerHeight - this.THRESHOLDS.SAFE_ZONE
        const isAwayFromPanel = !this.isMouseInPanelArea(clientY)

        return distance > this.THRESHOLDS.HIDE_DISTANCE &&
               panelController.isNormal() &&
               isInSafeZone &&
               isAwayFromPanel
      }
    }

    // 鼠标移动处理 - 重构版本
    const handleMouseMove = throttle((e) => {
      if (isUserInteracting.value || !inputPanelRef.value) return

      const { clientY } = e

      if (mouseManager.shouldShowPanel(clientY)) {
        panelController.show()
      } else if (mouseManager.shouldHidePanel(clientY)) {
        panelController.hide()
      }
    }, 50)

    // 用户交互管理器
    const interactionManager = {
      // 交互配置
      CONFIG: {
        INTERACTION_TIMEOUT: 1000,  // 交互状态保持时间
        BLUR_DELAY: 100            // 失焦检查延迟
      },

      // 开始交互
      startInteraction() {
        isUserInteracting.value = true
        panelController.show(true)
        this.scheduleInteractionEnd()
      },

      // 结束交互
      endInteraction() {
        isUserInteracting.value = false
      },

      // 延迟结束交互
      scheduleInteractionEnd() {
        clearTimer('interaction')
        timers.interaction = setTimeout(() => {
          this.endInteraction()
        }, this.CONFIG.INTERACTION_TIMEOUT)
      },

      // 检查是否有输入框处于焦点状态
      hasActiveFocus() {
        const activeElement = document.activeElement
        return activeElement &&
               ['TEXTAREA', 'INPUT', 'SELECT'].includes(activeElement.tagName) &&
               inputPanelRef.value?.contains(activeElement)
      }
    }

    // 展开面板处理 - 重构版本
    const handleExpand = () => {
      interactionManager.startInteraction()
    }

    // 监听视频提示词设置事件
    const handleSetVideoPrompt = (event) => {
      if (mode.value === 'image-to-video') {
        prompt.value = event.detail.prompt
      }
    }

    // 挂载和卸载事件监听 - 优化版本
    onMounted(() => {
      window.addEventListener('scroll', handleScroll, { passive: true })
      document.addEventListener('mousemove', handleMouseMove, { passive: true })
      window.addEventListener('setVideoPrompt', handleSetVideoPrompt)

      // 初始化随机种子
      generateRandomSeed()
    })

    onUnmounted(() => {
      window.removeEventListener('scroll', handleScroll)
      document.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('setVideoPrompt', handleSetVideoPrompt)
      clearAllTimers()
    })

    // 生成参数
    const mode = ref('text-to-image')
    const workflow = ref('sd_basic')
    const model = ref('')
    const width = ref(1024)
    const height = ref(1024)
    const seed = ref(-1)
    const prompt = ref('')
    const negativePrompt = ref('')

    // 计算属性
    const isGenerating = computed(() => taskStore.isGenerating)
    const uploadedImage = computed(() => taskStore.uploadedImageData)

    // 表单验证
    const isFormValid = computed(() => {
      const hasPrompt = prompt.value.trim().length > 0
      const hasImageForVideo = mode.value !== 'image-to-video' || uploadedImage.value
      return hasPrompt && hasImageForVideo
    })

    // 可用模型列表
    const availableModels = computed(() => {
      const models = {
        sd_basic: [
          { path: 'SD\\majicmixRealistic_v7.safetensors', description: 'MajicMix - 写实 + 二次元混合模型' },
          { path: 'SD\\realisticVisionV60B1_v51HyperVAE.safetensors', description: '⭐Realistic Vision - 超写实人像模型⭐' },
          { path: 'SD\\onlyrealistic_v30BakedVAE.safetensors', description: 'Onlyrealistic - 写实风格' }
        ],
        sdxl_basic: [
          { path: 'SDXL\\sd_xl_base_1.0.safetensors', description: 'SDXL Base - 官方基础模型' },
          { path: 'SDXL\\juggernautXL_juggXIByRundiffusion_2.safetensors', description: '⭐JuggernautXL - 多风格混合⭐' },
          { path: 'SDXL\\Wanxiang_XLSuper_RealisticV8.4_V8.4.safetensors', description: 'Wanxiang_Super_Realistic - 超写实风格' }
        ]
      }
      return models[workflow.value] || []
    })

    // 监听工作流变化，自动选择默认模型
    watch(workflow, () => {
      if (availableModels.value.length > 0) {
        model.value = availableModels.value[0].path
      }
    }, { immediate: true })

    // 监听模式变化，重置相关状态
    watch(mode, (newMode) => {
      if (newMode === 'text-to-image') {
        taskStore.setUploadedImage(null)
      }
      taskStore.setMode(newMode)
    })

    // 生成随机种子
    const generateRandomSeed = () => {
      seed.value = Math.floor(Math.random() * 1000000)
    }

    // 处理文件选择
    const handleFileSelect = (event) => {
      const file = event.target.files[0]
      if (file) {
        handleFileUpload(file)
      }
    }

    // 处理文件拖拽
    const handleDragOver = (event) => {
      event.target.classList.add('dragover')
    }

    const handleDragLeave = (event) => {
      event.target.classList.remove('dragover')
    }

    const handleDrop = (event) => {
      event.target.classList.remove('dragover')
      const file = event.dataTransfer.files[0]
      if (file) {
        handleFileUpload(file)
      }
    }

    // 触发文件选择
    const triggerUpload = () => {
      fileInput.value.click()
    }

    // Toast 通知函数
    const showToast = (message, type = 'info', duration = 3000) => {
      const iconMap = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
      }

      toast.value = {
        show: true,
        message,
        type,
        icon: iconMap[type] || iconMap.info
      }

      clearTimer('toast')
      timers.toast = setTimeout(() => {
        hideToast()
      }, duration)
    }

    const hideToast = () => {
      toast.value.show = false
      clearTimer('toast')
    }

    // 错误提示函数 - 使用toast替代alert
    const showError = (message) => {
      console.error(message)
      showToast(message, 'error')
    }

    const showSuccess = (message) => {
      showToast(message, 'success')
    }

    // 处理文件上传 - 优化版本
    const handleFileUpload = async (file) => {
      // 验证文件类型
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
      if (!allowedTypes.includes(file.type)) {
        showError('请上传 JPG、PNG 或 WebP 格式的图片')
        return
      }

      // 验证文件大小 (10MB)
      const maxSize = 10 * 1024 * 1024
      if (file.size > maxSize) {
        showError('文件大小不能超过 10MB')
        return
      }

      try {
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch(`${authStore.apiBase}/v2/upload/image`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authStore.token}`
          },
          body: formData
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`)
        }

        const result = await response.json()
        console.log('上传响应:', result) // 调试信息

        if (result.success) {
          // 构建完整的图片访问URL
          const imageUrl = `${authStore.apiBase}/v2/uploads/${result.relative_path}`

          console.log('图片URL:', imageUrl) // 调试信息

          taskStore.setUploadedImage({
            filename: result.filename,
            relative_path: result.relative_path,
            full_path: result.full_path,
            url: imageUrl
          })
          showSuccess('图片上传成功')

          // 确保面板保持展开状态
          panelController.show(true)          
          
        } else {
          throw new Error(result.message || '上传失败')
        }
      } catch (error) {
        console.error('上传失败:', error)
        showError(`上传失败：${error.message}`)
      }
    }

    // 移除已上传的图片
    const removeUploadedImage = () => {
      taskStore.setUploadedImage(null)
    }

    // 安全的数值转换函数
    const safeParseInt = (value, defaultValue = 0) => {
      const parsed = parseInt(value, 10)
      return isNaN(parsed) ? defaultValue : parsed
    }

    // 提交表单 - 优化版本
    const handleSubmit = async () => {
      // 基本验证
      if (!prompt.value.trim()) {
        showError('请输入提示词')
        return
      }

      if (mode.value === 'image-to-video' && !uploadedImage.value) {
        showError('请先上传图片')
        return
      }

      try {
        if (mode.value === 'text-to-image') {
          const widthValue = safeParseInt(width.value, 1024)
          const heightValue = safeParseInt(height.value, 1024)
          const seedValue = safeParseInt(seed.value, -1)

          await taskStore.submitTextToImage({
            prompt: prompt.value.trim(),
            negative_prompt: negativePrompt.value.trim(),
            width: widthValue,
            height: heightValue,
            workflow_name: workflow.value,
            checkpoint: model.value,
            seed: seedValue
          })
        } else {
          await taskStore.submitImageToVideo({
            prompt: prompt.value.trim(),
            negative_prompt: negativePrompt.value.trim()
          })
        }

        // 成功后显示成功消息，但不重置表单
        // resetForm() - 移除重置表单，保留提示词
        showSuccess(mode.value === 'text-to-image' ? '图片生成任务已提交' : '视频生成任务已提交')

        // 确保面板保持展开状态
        panelController.show(true)
      } catch (error) {
        console.error('提交失败:', error)
        showError(`提交失败：${error.message}`)
      }
    }

    // 重置表单函数
    const resetForm = () => {
      prompt.value = ''
      negativePrompt.value = ''
      // 生成新的随机种子
      generateRandomSeed()
    }

    // 计算属性：基于新的状态管理
    const isAutoHidden = computed(() => panelState.value === 'collapsed')
    const isFullyHidden = computed(() => panelState.value === 'hidden')
    const collapsed = computed(() => panelState.value === 'collapsed')

    return {
      // DOM 引用
      fileInput,
      inputPanelRef,

      // 状态
      isAutoHidden,
      isFullyHidden,
      collapsed,
      // showHintBar,
      toast,

      // 表单数据
      mode,
      workflow,
      model,
      width,
      height,
      seed,
      prompt,
      negativePrompt,

      // 计算属性
      isGenerating,
      uploadedImage,
      availableModels,
      isFormValid,

      // 方法
      generateRandomSeed,
      handleFileSelect,
      handleDragOver,
      handleDragLeave,
      handleDrop,
      triggerUpload,
      removeUploadedImage,
      handleExpand,
      handleFocus,
      handleBlur,
      handleSubmit,
      resetForm,
      hideToast
    }
  }
}
</script>

<style scoped>
/* Toast 通知样式 */
.toast-notification {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  background: var(--surface-1);
  border: 1px solid var(--border-1);
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(16px);
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 300px;
  max-width: 500px;
  animation: slideInRight 0.3s ease-out;
  transition: all 0.3s ease;
}

.toast-notification.success {
  border-color: #10b981;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, var(--surface-1) 100%);
}

.toast-notification.error {
  border-color: #ef4444;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, var(--surface-1) 100%);
}

.toast-notification.warning {
  border-color: #f59e0b;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, var(--surface-1) 100%);
}

.toast-notification.info {
  border-color: var(--accent);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, var(--surface-1) 100%);
}

.toast-notification i {
  font-size: 18px;
  flex-shrink: 0;
}

.toast-notification.success i {
  color: #10b981;
}

.toast-notification.error i {
  color: #ef4444;
}

.toast-notification.warning i {
  color: #f59e0b;
}

.toast-notification.info i {
  color: var(--accent);
}

.toast-notification span {
  flex: 1;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
}

.toast-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.toast-close:hover {
  background: var(--surface-2);
  color: var(--text-primary);
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.input-panel {
  background: var(--surface-1);
  backdrop-filter: blur(32px);
  border-top: 1px solid var(--border-1);
  padding: 32px;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.2);
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  transform: translateY(0);
}

.input-panel.auto-hidden {
  transform: translateY(calc(100% - 8px));
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
}

.input-panel.auto-hidden:hover {
  transform: translateY(calc(100% - 20px));
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.15);
}

.input-panel.fully-hidden {
  transform: translateY(100%);
  pointer-events: none;
}

.input-panel.collapsed {
  height: 56px;
  min-height: 56px;
  max-height: 56px;
  padding: 0 32px;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.12);
  background: var(--surface-1);
  border-top: 1px solid var(--border-1);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.input-collapsed-bar {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.prompt-input.collapsed {
  width: 100%;
  min-height: 40px;
  max-height: 40px;
  border-radius: 12px;
  background: var(--surface-2);
  border: 1px solid var(--border-1);
  color: var(--text-primary);
  font-size: 15px;
  padding: 8px 16px;
  resize: none;
  pointer-events: none;
  opacity: 0.7;
}

.input-hint {
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--primary);
  color: white;
  padding: 4px 12px;
  border-radius: 8px 8px 0 0;
  font-size: 12px;
  font-weight: 500;
  opacity: 0;
  transition: all 0.5s ease;
  pointer-events: none;
}

.input-panel.auto-hidden .input-hint {
  opacity: 1;
}

.input-container {
  max-width: 1400px;
  margin: 0 auto;
}

.mode-select-container {
  margin-bottom: 20px;
}

.mode-select-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mode-select-label {
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  min-width: 80px;
}

.mode-select {
  flex: 1;
  max-width: 200px;
  padding: 12px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border-1);
  border-radius: 12px;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 12px center;
  background-repeat: no-repeat;
  background-size: 16px;
  padding-right: 40px;
}

.mode-select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
  background: var(--surface-3);
}

.mode-select:hover {
  border-color: var(--accent);
  background: var(--surface-3);
}

.image-upload-container {
  margin-bottom: 20px;
}

.image-upload-area {
  border: 2px dashed var(--border-1);
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  background: var(--surface-2);
  transition: all 0.3s ease;
  cursor: pointer;
}

.image-upload-area:hover,
.image-upload-area.dragover {
  border-color: var(--accent);
  background: var(--surface-3);
}

.upload-icon {
  font-size: 48px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.upload-text {
  color: var(--text-secondary);
  font-size: 16px;
  margin-bottom: 8px;
}

.upload-hint {
  color: var(--text-muted);
  font-size: 14px;
}

.uploaded-image-preview {
  position: relative;
  max-width: 300px;
  margin: 0 auto;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.uploaded-image-preview img {
  width: 100%;
  height: auto;
  display: block;
}

.image-preview-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 8px;
}

.preview-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.preview-btn:hover {
  background: rgba(0, 0, 0, 0.9);
  transform: scale(1.1);
}

.controls-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
  padding: 24px;
  background: var(--surface-2);
  border-radius: 20px;
  border: 1px solid var(--border-1);
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.control-input,
.control-select {
  background: var(--surface-1);
  border: 1px solid var(--border-1);
  border-radius: 12px;
  padding: 12px 16px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.control-input:focus,
.control-select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  background: var(--surface-3);
}

.control-select {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 12px center;
  background-repeat: no-repeat;
  background-size: 16px;
  padding-right: 40px;
}

.btn-icon {
  background: var(--surface-3);
  border: 1px solid var(--border-1);
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 12px;
}

.btn-icon:hover {
  background: var(--surface-2);
  transform: translateY(-1px);
}

.prompt-input-group {
  margin-bottom: 20px;
}

.prompt-input {
  width: 100%;
  background: var(--surface-2);
  border: 1px solid var(--border-1);
  border-radius: 16px;
  padding: 16px 20px;
  color: var(--text-primary);
  font-size: 15px;
  font-family: inherit;
  resize: none;
  min-height: 56px;
  max-height: 120px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  line-height: 1.5;
}

.prompt-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
  background: var(--surface-3);
}

.prompt-input::placeholder {
  color: var(--text-muted);
}

.generate-btn {
  padding: 16px 32px;
  background: var(--primary-gradient);
  border: none;
  border-radius: 16px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 140px;
  justify-content: center;
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
}

.generate-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, transparent 50%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.generate-btn:hover::before {
  opacity: 1;
}

.generate-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 40px rgba(99, 102, 241, 0.5);
}

.generate-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.input-hint-bar {
  position: fixed;
  left: 50%;
  bottom: 120px; /* 调整位置，避免与输入面板重叠 */
  transform: translateX(-50%);
  z-index: 9999;
  background: var(--primary-gradient);
  color: #fff;
  padding: 10px 32px;
  border-radius: 20px;
  box-shadow: 0 4px 24px rgba(99,102,241,0.18);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); /* 放慢动画速度 */
  opacity: 0.95;
}
.input-hint-bar i {
  font-size: 18px;
}

@media (max-width: 768px) {
  .input-panel {
    padding: 20px;
  }

  .controls-panel {
    grid-template-columns: 1fr;
    gap: 16px;
    padding: 16px;
  }

  .prompt-input-group {
    margin-bottom: 16px;
  }

  .generate-btn {
    width: 100%;
  }
}
</style>