<template>
  <div class="login-container">
    <div class="login-form">
      <div class="login-header">
        <div class="login-logo">
          <i class="fas fa-magic"></i>
        </div>
        <h2>ComfyUI Studio</h2>
        <p>登录以开始创作</p>
      </div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input 
            type="text" 
            v-model="username" 
            required
            placeholder="请输入用户名"
          >
        </div>

        <div class="form-group">
          <label>密码</label>
          <input 
            type="password" 
            v-model="password" 
            required
            placeholder="请输入密码"
          >
        </div>

        <button type="submit" class="btn btn-primary" :disabled="isLoading">
          <span v-if="isLoading" class="loading"></span>
          {{ isLoading ? '登录中...' : '登录' }}
        </button>
      </form>

      <button class="btn btn-secondary" @click="showSettings = true">
        <i class="fas fa-cog"></i>
        设置服务器
      </button>
    </div>

    <!-- 设置弹窗 -->
    <div v-if="showSettings" class="modal-overlay" @click="showSettings = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>服务器设置</h3>
          <button class="modal-close" @click="showSettings = false">
            <i class="fas fa-times"></i>
          </button>
        </div>

        <div class="form-group">
          <label>服务器地址</label>
          <input 
            type="text" 
            v-model="apiServer"
            placeholder="如：http://192.168.1.100:8000"
          >
          <small>请输入后端API服务器的地址和端口，通常为 http://本机IP:8000</small>
        </div>

        <button class="btn btn-primary" @click="saveSettings">
          保存设置
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useAuthStore } from '@/store/auth'
import { useRouter } from 'vue-router'

export default {
  name: 'Login',
  
  setup() {
    const authStore = useAuthStore()
    const router = useRouter()
    
    const username = ref('')
    const password = ref('')
    const apiServer = ref(authStore.apiServer)
    const showSettings = ref(false)
    const isLoading = ref(false)

    const handleLogin = async () => {
      if (isLoading.value) return
      
      isLoading.value = true
      try {
        await authStore.login(username.value, password.value)
        router.push('/')
      } catch (error) {
        alert(error.message)
      } finally {
        isLoading.value = false
      }
    }

    const saveSettings = () => {
      if (!apiServer.value) {
        alert('请填写服务器地址')
        return
      }
      authStore.setApiServer(apiServer.value)
      showSettings.value = false
      alert('服务器地址已保存！')
    }

    return {
      username,
      password,
      apiServer,
      showSettings,
      isLoading,
      handleLogin,
      saveSettings
    }
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-form {
  background: var(--surface-1);
  backdrop-filter: blur(24px);
  border-radius: 24px;
  padding: 40px;
  max-width: 420px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-1);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-logo {
  font-size: 48px;
  margin-bottom: 16px;
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-header h2 {
  color: var(--text-primary);
  font-weight: 700;
  font-size: 24px;
}

.login-header p {
  color: var(--text-muted);
  font-size: 14px;
  margin-top: 8px;
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
  padding: 14px 16px;
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
}

.form-group small {
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 8px;
  display: block;
}

.btn {
  width: 100%;
  margin-bottom: 16px;
}

.btn-primary {
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
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
}

.modal-content {
  background: var(--surface-1);
  border-radius: 20px;
  padding: 32px;
  max-width: 400px;
  margin: 0 auto;
  border: 1px solid var(--border-1);
  position: relative;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.modal-header h3 {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 600;
}

.modal-close {
  color: var(--text-muted);
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 8px;
  transition: color 0.2s ease;
}

.modal-close:hover {
  color: var(--text-primary);
}
</style> 