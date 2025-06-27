<script setup>
import { useRouter, useRoute } from 'vue-router'
const menu = [
  { path: '/', label: '仪表盘', icon: '📊' },
  { path: '/users', label: '用户管理', icon: '👤' },
  { path: '/tasks', label: '任务管理', icon: '📋' },
  { path: '/nodes', label: '节点管理', icon: '🖥️' },
]
</script>

<template>
  <div id="app">
    <router-view v-if="$route.path === '/login'" />
    <el-container v-else style="min-height: 100vh;">
      <el-aside width="180px" class="sidebar">
        <div class="logo-box">
          <svg class="logo-img" viewBox="0 0 32 32" fill="none"><circle cx="16" cy="16" r="16" fill="#409eff"/><path d="M10 22c0-4 4-8 6-8s6 4 6 8" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>
          <span class="logo-text">ComfyUI</span>
        </div>
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/dashboard">
            <i class="el-icon-data-analysis"></i> 仪表盘
          </el-menu-item>
          <el-menu-item index="/users">
            <i class="el-icon-user"></i> 用户管理
          </el-menu-item>
          <el-menu-item index="/tasks">
            <i class="el-icon-document"></i> 任务管理
          </el-menu-item>
          <el-menu-item index="/nodes">
            <i class="el-icon-s-platform"></i> 节点管理
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header class="header">
          <div class="header-title">ComfyUI 分布式服务管理后台</div>
          <div class="header-user">
            管理员
            <el-button class="logout-btn" type="primary" @click="logout">退出</el-button>
          </div>
        </el-header>
        <el-main style="background:#f5f7fa;">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script>
export default {
  name: 'App',
  methods: {
    logout() {
      localStorage.removeItem('token');
      this.$router.push('/login');
    }
  }
}
</script>

<style>
.logo-box {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 64px;
  margin-bottom: 8px;
  background: #22304a;
}
.logo-img {
  width: 32px;
  height: 32px;
  margin-right: 8px;
}
.logo-text {
  font-size: 1.3rem;
  font-weight: bold;
  color: #4fc08d;
  letter-spacing: 1px;
}
.sidebar {
  background: #2d3a4b !important;
  border-right: none;
  min-width: 200px;
  padding-top: 0;
  color: #fff;
  box-shadow: 2px 0 8px 0 rgba(0,0,0,0.04);
}
.sidebar .el-menu {
  background: transparent !important;
  border-right: none;
}
.sidebar .el-menu-item {
  font-size: 1rem;
  height: 48px;
  border-radius: 8px;
  margin: 4px 12px;
  color: #bfcbd9 !important;
  transition: background 0.2s, color 0.2s;
}
.sidebar .el-menu-item.is-active, .sidebar .el-menu-item:hover {
  background: #22304a !important;
  color: #4fc08d !important;
}
.el-header.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  box-shadow: 0 2px 8px 0 rgba(0,0,0,0.04);
  border-bottom: 1px solid #e4e7ed;
  padding: 0 32px;
}
.header-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #222;
}
.header-user {
  color: #4fc08d;
  font-weight: 500;
  display: flex;
  align-items: center;
}
.logout-btn {
  margin-left: 20px;
  font-size: 1.1rem;
  padding: 8px 28px;
  height: 40px;
  border-radius: 20px;
  font-weight: bold;
  background: linear-gradient(90deg, #409eff 0%, #4fc08d 100%);
  color: #fff;
  box-shadow: 0 2px 8px 0 rgba(79,192,141,0.08);
  border: none;
}
.logout-btn:hover {
  background: linear-gradient(90deg, #4fc08d 0%, #409eff 100%);
  color: #fff;
}
</style>

<style>
body {
  background: #232526;
  color: #eee;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
}
</style>
