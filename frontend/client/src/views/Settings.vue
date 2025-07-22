<template>
  <div class="settings">
    <div class="settings-header">
      <h2>设置</h2>
    </div>

    <div class="settings-content">
      <div class="settings-section">
        <h3>服务器设置</h3>
        <div class="form-group">
          <label>API 服务器地址</label>
          <input 
            type="text" 
            v-model="apiServer" 
            placeholder="如：http://192.168.1.100:8000"
          >
          <small>请输入后端 API 服务器的地址和端口，通常为 http://本机IP:8000</small>
        </div>
        <button class="btn btn-primary" @click="saveApiServer">
          保存设置
        </button>
      </div>

      <div class="settings-section">
        <h3>账户设置</h3>
        <div class="form-group">
          <label>当前用户</label>
          <input 
            type="text" 
            :value="currentUser" 
            disabled
          >
        </div>
        <button class="btn btn-secondary" @click="handleLogout">
          <i class="fas fa-sign-out-alt"></i>
          退出登录
        </button>
      </div>

      <div class="settings-section">
        <h3>关于</h3>
        <div class="about-info">
          <p>ComfyUI Web Service</p>
          <p>Version: 1.0.0</p>
          <p>
            <a href="https://github.com/yourusername/ComfyUI-Web-Service" target="_blank">
              <i class="fab fa-github"></i>
              GitHub
            </a>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '@/store/auth'
import { useRouter } from 'vue-router'
import { showSuccess } from '@/utils/notification'

const authStore = useAuthStore()
const router = useRouter()

const apiServer = ref(authStore.apiServer)
const currentUser = computed(() => '当前用户')

const saveApiServer = () => {
  if (!apiServer.value) {
    alert('请填写服务器地址')
    return
  }
  authStore.setApiServer(apiServer.value)
  showSuccess('服务器设置已保存')
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.settings {
  min-height: 100vh;
}

.settings-header {
  margin-bottom: 32px;
}

.settings-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.settings-content {
  max-width: 600px;
}

.settings-section {
  background: var(--surface-1);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid var(--border-1);
}

.settings-section h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border-1);
  border-radius: 12px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  background: var(--surface-3);
}

.form-group input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-group small {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.about-info {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.about-info p {
  margin-bottom: 8px;
}

.about-info a {
  color: var(--accent);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: color 0.2s ease;
}

.about-info a:hover {
  color: var(--accent-hover);
}

@media (max-width: 768px) {
  .settings-header {
    margin-bottom: 24px;
  }

  .settings-header h2 {
    font-size: 20px;
  }

  .settings-section {
    padding: 20px;
  }
}
</style> 