<template>
  <div class="auth-image-container" :class="{ 'loading': isLoading, 'error': hasError }">
    <img 
      v-if="!hasError && imageData" 
      :src="imageData" 
      :alt="alt"
      @load="handleImageLoaded"
      @error="handleImageError"
      class="auth-image"
    />
    <div v-else-if="isLoading" class="image-placeholder loading">
      <i class="fas fa-spinner fa-spin"></i>
      <span>加载中...</span>
    </div>
    <div v-else class="image-placeholder error">
      <i class="fas fa-exclamation-circle"></i>
      <span>图片加载失败</span>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '@/store/auth'

export default {
  name: 'AuthImage',
  props: {
    src: {
      type: String,
      required: true
    },
    alt: {
      type: String,
      default: '图片'
    }
  },
  setup(props) {
    const authStore = useAuthStore()
    const imageData = ref(null)
    const isLoading = ref(true)
    const hasError = ref(false)

    const loadImage = async () => {
      if (!props.src) {
        hasError.value = true
        isLoading.value = false
        return
      }

      isLoading.value = true
      hasError.value = false

      try {
        // 使用fetch获取图片并添加认证头
        const response = await fetch(props.src, {
          headers: {
            'Authorization': `Bearer ${authStore.token}`
          }
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        // 获取图片数据并转换为blob
        const blob = await response.blob()
        
        // 创建blob URL
        imageData.value = URL.createObjectURL(blob)
      } catch (error) {
        console.error('加载图片失败:', error)
        hasError.value = true
      } finally {
        isLoading.value = false
      }
    }

    const handleImageLoaded = () => {
      isLoading.value = false
    }

    const handleImageError = () => {
      hasError.value = true
      isLoading.value = false
    }

    // 当src变化时重新加载图片
    watch(() => props.src, loadImage)

    // 组件挂载时加载图片
    onMounted(loadImage)

    // 组件卸载时释放blob URL
    onUnmounted(() => {
      if (imageData.value) {
        URL.revokeObjectURL(imageData.value)
      }
    })

    return {
      imageData,
      isLoading,
      hasError,
      handleImageLoaded,
      handleImageError
    }
  }
}
</script>

<style scoped>
.auth-image-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.auth-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 100px;
  background-color: var(--surface-2);
  color: var(--text-muted);
  font-size: 14px;
  padding: 20px;
}

.image-placeholder i {
  font-size: 24px;
  margin-bottom: 8px;
}

.image-placeholder.loading {
  color: var(--accent);
}

.image-placeholder.error {
  color: var(--error);
}
</style>
