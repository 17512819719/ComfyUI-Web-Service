<template>
  <div class="image-with-retry" :class="{ 'loading': isLoading, 'error': hasError }">
    <!-- 图片元素 -->
    <img
      v-show="!isLoading && !hasError"
      ref="imageRef"
      :src="imageSrc"
      :alt="alt"
      :loading="loading"
      :style="imageStyle"
      @load="handleLoad"
      @error="handleError"
    />
    
    <!-- 加载指示器 -->
    <div v-if="isLoading" class="loading-indicator">
      <div class="loading-spinner"></div>
      <span class="loading-text">
        {{ loadingText }}
      </span>
    </div>
    
    <!-- 错误状态 -->
    <div v-if="hasError" class="error-placeholder">
      <i class="fas fa-exclamation-circle error-icon"></i>
      <span class="error-text">{{ errorMessage }}</span>
      <button v-if="showRetryButton" class="btn-retry" @click="retry">
        <i class="fas fa-redo"></i>
        重试
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { imageCache, debounce } from '@/utils/performance'

export default {
  name: 'ImageWithRetry',
  props: {
    src: {
      type: String,
      required: true
    },
    alt: {
      type: String,
      default: '图片'
    },
    loading: {
      type: String,
      default: 'lazy'
    },
    maxRetries: {
      type: Number,
      default: 3
    },
    retryDelay: {
      type: Number,
      default: 1000
    },
    timeout: {
      type: Number,
      default: 30000
    },
    showRetryButton: {
      type: Boolean,
      default: true
    },
    authToken: {
      type: String,
      default: ''
    },
    lazy: {
      type: Boolean,
      default: true
    },
    placeholder: {
      type: String,
      default: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="1" height="1"%3E%3C/svg%3E'
    }
  },
  emits: ['load', 'error', 'retry', 'visible', 'auth-error'],
  setup(props, { emit }) {
    const imageRef = ref(null)
    const isLoading = ref(true)
    const hasError = ref(false)
    const currentRetry = ref(0)
    const imageSrc = ref('')
    const abortController = ref(null)
    const retryTimeout = ref(null)
    const isVisible = ref(false)
    const intersectionObserver = ref(null)

    // 计算属性
    const loadingText = computed(() => {
      if (currentRetry.value === 0) {
        return '加载中...'
      }
      return `加载中 (重试 ${currentRetry.value}/${props.maxRetries})...`
    })

    const errorMessage = computed(() => {
      if (currentRetry.value >= props.maxRetries) {
        return '加载失败'
      }
      return `加载失败，${Math.ceil(getRetryDelay() / 1000)}秒后重试...`
    })

    const imageStyle = computed(() => ({
      opacity: isLoading.value ? '0' : '1',
      transition: 'opacity 0.3s ease'
    }))

    // 计算重试延迟（指数退避）
    const getRetryDelay = () => {
      return Math.min(props.retryDelay * Math.pow(2, currentRetry.value), 5000)
    }

    // 加载图片
    const loadImage = async () => {
      try {
        // console.log(`[ImageWithRetry] 开始加载图片: ${props.src}`)
        // console.log(`[ImageWithRetry] 认证令牌: ${props.authToken ? '已提供' : '未提供'}`)

        // 检查缓存
        const cachedUrl = await imageCache.get(props.src, props.authToken)
        if (cachedUrl) {
          // console.log(`[ImageWithRetry] 使用缓存: ${cachedUrl}`)
          imageSrc.value = cachedUrl
          return cachedUrl
        }

        // 取消之前的请求
        if (abortController.value) {
          abortController.value.abort()
        }

        abortController.value = new AbortController()
        const signal = abortController.value.signal

        // 设置超时
        const timeoutId = setTimeout(() => {
          abortController.value.abort()
        }, props.timeout)

        // 使用 fetch 预加载图片
        const headers = {}
        if (props.authToken) {
          headers['Authorization'] = `Bearer ${props.authToken}`
        }

        // console.log(`[ImageWithRetry] 发送请求:`, { url: props.src, headers })

        const response = await fetch(props.src, {
          headers,
          signal
        })

        clearTimeout(timeoutId)

        // console.log(`[ImageWithRetry] 响应状态: ${response.status}`)

        if (!response.ok) {
          // 处理认证错误
          if (response.status === 401 || response.status === 403) {
            console.error(`[ImageWithRetry] 认证失败，状态码: ${response.status}`)
            // 触发认证错误事件，让父组件处理
            emit('auth-error', { status: response.status, url: props.src })
          }
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const blob = await response.blob()
        const objectUrl = URL.createObjectURL(blob)

        // console.log(`[ImageWithRetry] 创建对象URL: ${objectUrl}`)

        // 创建临时图片对象进行预加载
        const tempImg = new Image()

        return new Promise((resolve, reject) => {
          tempImg.onload = () => {
            // console.log(`[ImageWithRetry] 图片加载成功`)
            imageSrc.value = objectUrl
            resolve(objectUrl)
          }

          tempImg.onerror = () => {
            console.error(`[ImageWithRetry] 图片对象加载失败`)
            URL.revokeObjectURL(objectUrl)
            reject(new Error('Image loading failed'))
          }

          tempImg.src = objectUrl
        })
      } catch (error) {
        console.error(`[ImageWithRetry] 加载失败:`, error)
        if (error.name === 'AbortError') {
          throw new Error('Request timeout')
        }
        throw error
      }
    }

    // 处理加载成功
    const handleLoad = () => {
      isLoading.value = false
      hasError.value = false
      currentRetry.value = 0
      emit('load', imageRef.value)
    }

    // 处理加载错误
    const handleError = () => {
      console.error(`图片加载失败 (尝试 ${currentRetry.value + 1}/${props.maxRetries}):`, props.src)
      
      if (currentRetry.value < props.maxRetries) {
        // 自动重试
        const delay = getRetryDelay()
        retryTimeout.value = setTimeout(() => {
          currentRetry.value++
          startLoad()
        }, delay)
      } else {
        // 达到最大重试次数
        isLoading.value = false
        hasError.value = true
        emit('error', new Error('Maximum retries exceeded'))
      }
    }

    // 手动重试
    const retry = () => {
      currentRetry.value = 0
      hasError.value = false
      isLoading.value = true
      emit('retry')
      startLoad()
    }

    // 开始加载
    const startLoad = async () => {
      try {
        isLoading.value = true
        hasError.value = false
        await loadImage()
      } catch (error) {
        handleError()
      }
    }

    // 设置懒加载观察器
    const setupIntersectionObserver = () => {
      if (!props.lazy || !imageRef.value) return

      if ('IntersectionObserver' in window) {
        intersectionObserver.value = new IntersectionObserver(
          debounce((entries) => {
            entries.forEach(entry => {
              if (entry.isIntersecting && !isVisible.value) {
                isVisible.value = true
                emit('visible', true)
                startLoad()
                // 停止观察，因为已经开始加载
                intersectionObserver.value?.unobserve(imageRef.value)
              }
            })
          }, 100),
          {
            root: null,
            rootMargin: '50px 0px',
            threshold: 0.1
          }
        )

        intersectionObserver.value.observe(imageRef.value)
      } else {
        // 降级方案：立即加载
        isVisible.value = true
        startLoad()
      }
    }

    // 监听 src 变化
    watch(() => props.src, (newSrc, oldSrc) => {
      if (newSrc !== oldSrc && newSrc) {
        // 清理之前的 URL
        if (imageSrc.value && imageSrc.value.startsWith('blob:')) {
          URL.revokeObjectURL(imageSrc.value)
        }

        currentRetry.value = 0
        imageSrc.value = props.placeholder
        isVisible.value = false

        if (props.lazy) {
          // 懒加载模式：等待元素可见
          setupIntersectionObserver()
        } else {
          // 立即加载模式
          startLoad()
        }
      }
    }, { immediate: true })

    // 清理函数
    const cleanup = () => {
      if (abortController.value) {
        abortController.value.abort()
      }
      if (retryTimeout.value) {
        clearTimeout(retryTimeout.value)
      }
      if (intersectionObserver.value) {
        intersectionObserver.value.disconnect()
      }
      if (imageSrc.value && imageSrc.value.startsWith('blob:')) {
        URL.revokeObjectURL(imageSrc.value)
      }
    }

    onMounted(() => {
      if (props.src) {
        if (props.lazy) {
          // 设置占位图片
          imageSrc.value = props.placeholder
          // 等待下一个tick确保DOM已渲染
          nextTick(() => {
            setupIntersectionObserver()
          })
        } else {
          startLoad()
        }
      }
    })

    onUnmounted(() => {
      cleanup()
    })

    return {
      imageRef,
      isLoading,
      hasError,
      imageSrc,
      loadingText,
      errorMessage,
      imageStyle,
      handleLoad,
      handleError,
      retry
    }
  }
}
</script>

<style scoped>
.image-with-retry {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  border-radius: 8px;
  overflow: hidden;
}

.image-with-retry img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

.loading-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-1);
  border-top: 3px solid var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  font-size: 14px;
  text-align: center;
}

.error-placeholder {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary);
  text-align: center;
  padding: 20px;
}

.error-icon {
  font-size: 32px;
  color: var(--error);
}

.error-text {
  font-size: 14px;
  opacity: 0.8;
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

.btn-retry:active {
  transform: translateY(0);
}

.btn-retry i {
  font-size: 14px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
