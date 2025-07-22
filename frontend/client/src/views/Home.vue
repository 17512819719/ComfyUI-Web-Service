<template>
  <div class="home">
    <!-- 左侧导航栏 -->
    <div class="sidebar">
      <div class="sidebar-logo">
        <i class="fas fa-magic"></i>
      </div>
      <nav class="sidebar-nav">
        <div class="nav-item active" data-tab="generate">
          <i class="fas fa-image"></i>
        </div>
        <div class="nav-item" data-tab="history">
          <i class="fas fa-history"></i>
        </div>
        <div class="nav-item" data-tab="settings">
          <i class="fas fa-cog"></i>
        </div>
      </nav>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content">
      <gallery-grid />
      <!-- 底部输入面板 -->
      <input-panel v-if="showInputPanel" />
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/store/auth'
import { useTaskStore } from '@/store/task'
import { useRouter } from 'vue-router'
import GalleryGrid from '@/components/gallery/GalleryGrid.vue'
import InputPanel from '@/components/task/InputPanel.vue'
import { performanceMonitor } from '@/utils/performance'

export default {
  name: 'Home',
  
  components: {
    GalleryGrid,
    InputPanel
  },

  setup() {
    const authStore = useAuthStore()
    const taskStore = useTaskStore()
    const router = useRouter()
    const isConnected = ref(true)
    const showInputPanel = ref(true)

    // 定时器引用
    let connectionInterval = null
    let refreshInterval = null

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
          if (error.message?.includes('401') || error.message?.includes('未授权')) {
            // 如果是认证错误，重定向到登录页面
            authStore.logout()
            router.push('/login')
          }
        }
      }
    }

    // 清理定时器
    const clearTimers = () => {
      if (connectionInterval) {
        clearInterval(connectionInterval)
        connectionInterval = null
      }
      if (refreshInterval) {
        clearInterval(refreshInterval)
        refreshInterval = null
      }
      // 停止所有任务轮询
      taskStore.stopAllPolling()
    }

    // 退出登录
    const handleLogout = () => {
      console.log('开始退出登录流程')

      // 第一步：立即清理所有定时器和轮询
      clearTimers()
      console.log('已清理定时器')

      // 第二步：清理性能监控
      performanceMonitor.disconnect()
      console.log('已清理性能监控')

      // 第三步：清除任务数据
      taskStore.reset()
      console.log('已清理任务数据')

      // 第四步：清除认证状态（这会清除token）
      authStore.logout()
      console.log('已清除认证状态')

      // 第五步：跳转到登录页
      router.push('/login')
      console.log('已跳转到登录页')
    }

    onMounted(() => {
      // 初始化检查连接状态
      checkConnection()
      // 定期检查连接状态
      connectionInterval = setInterval(checkConnection, 30000)
      // 加载任务列表
      refreshTasks()
      // 定期刷新任务列表（减少频率，因为现在有实时轮询）
      refreshInterval = setInterval(refreshTasks, 30000)

      // 组件卸载时清理定时器和轮询
      onUnmounted(() => {
        clearTimers()
      })
    })

    return {
      isConnected,
      showInputPanel,
      refreshTasks,
      handleLogout
    }
  }
}
</script>

<style scoped>
.home {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  width: 80px;
  height: 100vh;
  background: var(--surface-1);
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-1);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  z-index: 1000;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.1);
}

.sidebar-logo {
  width: 48px;
  height: 48px;
  background: var(--primary-gradient);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.sidebar-logo::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, transparent 50%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.sidebar-logo:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 32px rgba(99, 102, 241, 0.3);
}

.sidebar-logo:hover::before {
  opacity: 1;
}

.sidebar-logo i {
  color: white;
  font-size: 22px;
  z-index: 1;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}

.nav-item {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: var(--text-muted);
  position: relative;
  overflow: hidden;
}

.nav-item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--surface-2);
  border-radius: 14px;
  opacity: 0;
  transition: all 0.3s ease;
  transform: scale(0.8);
}

.nav-item:hover::before {
  opacity: 1;
  transform: scale(1);
}

.nav-item:hover, .nav-item.active {
  color: var(--accent);
  transform: translateY(-1px);
}

.nav-item.active::before {
  opacity: 1;
  transform: scale(1);
  background: rgba(99, 102, 241, 0.15);
}

.nav-item i {
  font-size: 20px;
  z-index: 1;
}

.main-content {
  margin-left: 80px;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  overflow-y: auto;
  min-width: 0;
}

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



@media (max-width: 768px) {
  .sidebar {
    width: 70px;
  }

  .main-content {
    margin-left: 70px;
  }

  .toolbar {
    padding: 0 20px;
  }

  .content-area {
    padding: 20px;
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: 60px;
  }

  .main-content {
    margin-left: 60px;
  }

  .toolbar {
    padding: 0 16px;
  }

  .content-area {
    padding: 16px;
  }
}
</style>