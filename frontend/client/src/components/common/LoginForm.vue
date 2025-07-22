<template>
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
      <button type="submit" class="btn btn-primary" :disabled="loading">
        <span v-if="loading" class="loading"></span>
        {{ loading ? '登录中...' : '登录' }}
      </button>
    </form>

    <button class="btn btn-secondary" @click="showSettings = true">
      <i class="fas fa-cog"></i>
      设置服务器
    </button>

    <!-- 设置弹窗 -->
    <settings-modal v-model:visible="showSettings" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/store/auth'
import { useRouter } from 'vue-router'
import SettingsModal from './SettingsModal.vue'

const authStore = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const loading = ref(false)
const showSettings = ref(false)

const handleLogin = async () => {
  try {
    loading.value = true
    await authStore.login(username.value, password.value)
    router.push('/')
  } catch (error) {
    console.error('登录失败:', error)
    alert(error.message || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-form {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
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
  display: block;
  margin-top: 8px;
  font-size: 12px;
}

button[type="submit"] {
  width: 100%;
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.btn-secondary {
  width: 100%;
  margin-top: 16px;
  padding: 12px;
}
</style> 