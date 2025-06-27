<template>
  <div class="login-bg">
    <div class="login-card">
      <div class="login-title">ComfyUI 管理后台</div>
      <el-form :model="loginForm" @submit.native.prevent="onLogin">
        <el-form-item>
          <el-input v-model="loginForm.username" placeholder="用户名" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="loginForm.password" type="password" placeholder="密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width:100%;" :loading="loading" @click="onLogin">登录</el-button>
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" show-icon />
      </el-form>
    </div>
  </div>
</template>

<script>
import api from '../api'
export default {
  name: 'Login',
  data() {
    return {
      loginForm: {
        username: '',
        password: ''
      },
      loading: false,
      error: ''
    }
  },
  methods: {
    async onLogin() {
      this.loading = true
      this.error = ''
      try {
        const res = await api.post('/admin/login', new URLSearchParams(this.loginForm))
        localStorage.setItem('token', res.data.access_token)
        this.$router.push('/dashboard')
      } catch (e) {
        this.error = e.response?.data?.detail || '登录失败'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-bg {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f6f8fa;
}
.login-card {
  background: #fff;
  padding: 40px 32px;
  border-radius: 14px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.04);
  min-width: 320px;
}
.login-title {
  font-size: 2rem;
  font-weight: 700;
  color: #222;
  margin-bottom: 32px;
  text-align: center;
  letter-spacing: 2px;
}
</style> 