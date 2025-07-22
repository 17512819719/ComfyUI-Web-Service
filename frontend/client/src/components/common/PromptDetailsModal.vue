<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-container" @click.stop>
        <div class="modal-content">
          <!-- 模态框头部 -->
          <div class="modal-header">
            <h3 class="modal-title">
              <i class="fas fa-info-circle"></i>
              提示词详情
            </h3>
            <button class="modal-close" @click="close">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <!-- 模态框内容 -->
          <div class="modal-body">
            <!-- 正向提示词 -->
            <div class="prompt-section">
              <div class="prompt-header">
                <h4>
                  <i class="fas fa-plus-circle positive-icon"></i>
                  正向提示词
                </h4>
                <button 
                  v-if="prompt" 
                  class="copy-btn" 
                  @click="copyToClipboard(prompt)"
                  title="复制到剪贴板"
                >
                  <i class="fas fa-copy"></i>
                </button>
              </div>
              <div class="prompt-content">
                <p v-if="prompt" class="prompt-text">{{ prompt }}</p>
                <p v-else class="prompt-empty">无</p>
              </div>
            </div>

            <!-- 反向提示词 -->
            <div class="prompt-section">
              <div class="prompt-header">
                <h4>
                  <i class="fas fa-minus-circle negative-icon"></i>
                  反向提示词
                </h4>
                <button 
                  v-if="negativePrompt" 
                  class="copy-btn" 
                  @click="copyToClipboard(negativePrompt)"
                  title="复制到剪贴板"
                >
                  <i class="fas fa-copy"></i>
                </button>
              </div>
              <div class="prompt-content">
                <p v-if="negativePrompt" class="prompt-text">{{ negativePrompt }}</p>
                <p v-else class="prompt-empty">无</p>
              </div>
            </div>
          </div>

          <!-- 模态框底部 -->
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="close">
              关闭
            </button>
            <button 
              v-if="prompt || negativePrompt" 
              class="btn btn-primary" 
              @click="copyAllPrompts"
            >
              <i class="fas fa-copy"></i>
              复制全部
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { ref, watch } from 'vue'

export default {
  name: 'PromptDetailsModal',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    prompt: {
      type: String,
      default: ''
    },
    negativePrompt: {
      type: String,
      default: ''
    }
  },
  emits: ['close', 'copy'],
  setup(props, { emit }) {
    // 复制到剪贴板
    const copyToClipboard = async (text) => {
      try {
        await navigator.clipboard.writeText(text)
        emit('copy', { type: 'single', text })
        showCopySuccess()
      } catch (error) {
        console.error('复制失败:', error)
        // 降级方案
        fallbackCopyToClipboard(text)
      }
    }

    // 复制全部提示词
    const copyAllPrompts = async () => {
      const allText = [
        props.prompt ? `正向提示词：\n${props.prompt}` : '',
        props.negativePrompt ? `反向提示词：\n${props.negativePrompt}` : ''
      ].filter(Boolean).join('\n\n')

      try {
        await navigator.clipboard.writeText(allText)
        emit('copy', { type: 'all', text: allText })
        showCopySuccess()
      } catch (error) {
        console.error('复制失败:', error)
        fallbackCopyToClipboard(allText)
      }
    }

    // 降级复制方案
    const fallbackCopyToClipboard = (text) => {
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      
      try {
        document.execCommand('copy')
        emit('copy', { type: 'fallback', text })
        showCopySuccess()
      } catch (error) {
        console.error('降级复制也失败:', error)
      } finally {
        document.body.removeChild(textArea)
      }
    }

    // 显示复制成功提示
    const showCopySuccess = () => {
      // 这里可以集成通知系统
      console.log('复制成功！')
    }

    // 关闭模态框
    const close = () => {
      emit('close')
    }

    // 处理遮罩层点击
    const handleOverlayClick = () => {
      close()
    }

    // 监听ESC键关闭
    const handleKeydown = (event) => {
      if (event.key === 'Escape' && props.visible) {
        close()
      }
    }

    // 监听visible变化，添加/移除键盘事件
    watch(() => props.visible, (newVisible) => {
      if (newVisible) {
        document.addEventListener('keydown', handleKeydown)
        // 防止背景滚动
        document.body.style.overflow = 'hidden'
      } else {
        document.removeEventListener('keydown', handleKeydown)
        // 恢复背景滚动
        document.body.style.overflow = ''
      }
    })

    return {
      copyToClipboard,
      copyAllPrompts,
      close,
      handleOverlayClick
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
  animation: fadeIn 0.3s ease;
}

.modal-container {
  max-width: 700px;
  width: 90%;
  max-height: 90vh;
  animation: slideIn 0.3s ease;
}

.modal-content {
  background: var(--surface-1);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  border: 1px solid var(--border-1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 0 24px;
  border-bottom: 1px solid var(--border-1);
  margin-bottom: 0;
  padding-bottom: 16px;
}

.modal-title {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-title i {
  color: var(--primary);
  font-size: 18px;
}

.modal-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.3s ease;
  font-size: 16px;
}

.modal-close:hover {
  background: var(--surface-2);
  color: var(--text-primary);
  transform: scale(1.1);
}

.modal-body {
  padding: 24px;
  max-height: 60vh;
  overflow-y: auto;
}

.prompt-section {
  margin-bottom: 24px;
}

.prompt-section:last-child {
  margin-bottom: 0;
}

.prompt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.prompt-header h4 {
  color: var(--text-secondary);
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.positive-icon {
  color: var(--success);
}

.negative-icon {
  color: var(--error);
}

.copy-btn {
  background: var(--surface-2);
  border: 1px solid var(--border-1);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 6px;
  transition: all 0.3s ease;
  font-size: 12px;
}

.copy-btn:hover {
  background: var(--surface-3);
  color: var(--text-primary);
  transform: translateY(-1px);
}

.prompt-content {
  background: var(--surface-2);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--border-1);
}

.prompt-text {
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  font-size: 14px;
}

.prompt-empty {
  color: var(--text-muted);
  font-style: italic;
  margin: 0;
  text-align: center;
  padding: 20px;
}

.modal-footer {
  padding: 16px 24px 24px 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid var(--border-1);
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary {
  background: var(--surface-2);
  border: 1px solid var(--border-1);
  color: var(--text-secondary);
}

.btn-secondary:hover {
  background: var(--surface-3);
  color: var(--text-primary);
}

.btn-primary {
  background: var(--primary-gradient);
  border: none;
  color: white;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { 
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* 滚动条样式 */
.modal-body::-webkit-scrollbar {
  width: 6px;
}

.modal-body::-webkit-scrollbar-track {
  background: var(--surface-3);
  border-radius: 3px;
}

.modal-body::-webkit-scrollbar-thumb {
  background: var(--border-2);
  border-radius: 3px;
}

.modal-body::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}
</style>
