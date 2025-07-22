<template>
  <div class="toolbar">
    <div class="toolbar-title">ComfyUI Studio</div>
    <div class="status-indicator">
      <div class="status-dot" :class="{ disconnected: !isConnected }"></div>
      <span>{{ connectionStatus }}</span>
    </div>
    <div class="toolbar-actions">
      <button class="btn btn-secondary" @click="refreshTasks">
        <i class="fas fa-sync"></i>
        刷新任务
      </button>
      <button class="btn btn-secondary" @click="handleLogout">
        <i class="fas fa-sign-out-alt"></i>
        退出登录
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useTaskStore } from '@/store/task'
import { performanceMonitor } from '@/utils/performance'

const router = useRouter()
const authStore = useAuthStore()
const taskStore = useTaskStore()

const isConnected = ref(true)
const connectionStatus = computed(() => isConnected.value ? '已连接' : '连接断开')

// 检查连接状态
const checkConnection = async () => {
  try {
    const result = await taskStore.checkConnection()
    isConnected.value = result
  } catch (error) {
    // 只有在有token但连接失败时才记录错误
    if (authStore.token) {
      console.error('检查连接状态失败:', error)
    }
    isConnected.value = false
  }
}

// 刷新任务列表
const refreshTasks = async () => {
  // 检查是否有认证token
  if (!authStore.token) {
    console.log('无认证token，跳过刷新任务')
    return
  }

  try {
    await taskStore.fetchTasks()
  } catch (error) {
    // 只有在有token但请求失败时才记录错误
    if (authStore.token) {
      console.error('刷新任务失败:', error)
    }
  }
}

// 退出登录
const handleLogout = () => {
  console.log('Toolbar: 开始退出登录流程')

  // 第一步：立即清理定时器
  if (connectionTimer) {
    clearInterval(connectionTimer)
    connectionTimer = null
    console.log('Toolbar: 已清理连接检查定时器')
  }

  // 第二步：清理性能监控
  performanceMonitor.disconnect()
  console.log('Toolbar: 已清理性能监控')

  // 第三步：清除任务数据
  taskStore.reset()
  console.log('Toolbar: 已清理任务数据')

  // 第四步：清除认证状态
  authStore.logout()
  console.log('Toolbar: 已清除认证状态')

  // 第五步：跳转到登录页
  router.push('/login')
  console.log('Toolbar: 已跳转到登录页')
}

// 定期检查连接状态
let connectionTimer
onMounted(() => {
  checkConnection()
  connectionTimer = setInterval(checkConnection, 30000)
})

onUnmounted(() => {
  if (connectionTimer) {
    clearInterval(connectionTimer)
    connectionTimer = null
  }
})
</script>

<style scoped>
.toolbar {
  height: 72px;
  background: var(--surface-1);
  backdrop-filter: blur(24px);
  border-bottom: 1px solid var(--border-1);
  display: flex;
  align-items: center;
  padding: 0 32px;
  gap: 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.toolbar-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.toolbar-actions {
  margin-left: auto;
  display: flex;
  gap: 12px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
  background: var(--surface-2);
  padding: 8px 16px;
  border-radius: 12px;
  border: 1px solid var(--border-1);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
  animation: pulse 2s infinite;
}

.status-dot.disconnected {
  background: var(--error);
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.4);
  animation: none;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

@media (max-width: 768px) {
  .toolbar {
    padding: 0 20px;
    height: 64px;
  }

  .toolbar-title {
    font-size: 18px;
  }
}
</style>