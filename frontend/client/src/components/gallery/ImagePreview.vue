<template>
  <div 
    v-if="visible" 
    class="image-preview-modal" 
    :class="{ active: visible }"
    @click.self="close"
  >
    <div class="image-preview-content">
      <button class="image-preview-close" @click="close">
        <i class="fas fa-times"></i>
      </button>
      
      <div class="loading-indicator" v-if="loading">
        <div class="loading"></div>
        <span>加载中...</span>
      </div>

      <img 
        :src="imageUrl" 
        alt="预览图片"
        :style="{ opacity: loading ? 0 : 1 }"
        @load="handleImageLoad"
        @error="handleImageError"
      >

      <div v-if="prompt" class="image-prompt">
        {{ prompt }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useAuthStore } from '@/store/auth'

export default {
  name: 'ImagePreview',

  props: {
    visible: {
      type: Boolean,
      default: false
    },
    imageUrl: {
      type: String,
      default: ''
    },
    prompt: {
      type: String,
      default: ''
    }
  },

  emits: ['close', 'retry'],

  setup(props, { emit }) {
    const loading = ref(true)
    const authStore = useAuthStore()

    const close = () => {
      emit('close')
    }

    const handleImageLoad = () => {
      loading.value = false
    }

    const handleImageError = () => {
      loading.value = false
      emit('retry')
    }

    return {
      loading,
      close,
      handleImageLoad,
      handleImageError
    }
  }
}
</script>

<style scoped>
.image-preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
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
  transition: opacity 0.3s ease;
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
  transition: all 0.2s ease;
}

.image-preview-close:hover {
  color: var(--primary);
  transform: scale(1.1);
}

.loading-indicator {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  gap: 16px;
}

.loading {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.2);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.image-prompt {
  position: absolute;
  bottom: -40px;
  left: 0;
  right: 0;
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
  opacity: 0.8;
  max-width: 600px;
  margin: 0 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style> 