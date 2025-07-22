<template>
  <div id="app">
    <router-view v-if="!isAuthenticated" />

    <!-- 主界面 -->
    <div v-else class="main-app">
      <!-- 左侧导航栏 -->
      <sidebar />

      <!-- 主内容区域 -->
      <div class="main-content">
        <!-- 顶部工具栏 -->
        <toolbar />

        <!-- 内容区域 -->
        <div class="content-area">
          <router-view />
        </div>

        <!-- 底部输入面板 -->
        <input-panel v-if="showInputPanel" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import Sidebar from '@/components/layout/Sidebar.vue'
import Toolbar from '@/components/layout/Toolbar.vue'
import InputPanel from '@/components/task/InputPanel.vue'

const route = useRoute()
const authStore = useAuthStore()
const isAuthenticated = computed(() => authStore.isAuthenticated)
const showInputPanel = computed(() => {
  // 只在主页和历史页面显示输入面板
  return ['Home', 'History'].includes(route.name)
})
</script>

<style>
.main-app {
  display: flex;
  min-height: 100vh;
}

.main-content {
  flex: 1;
  margin-left: 80px;
  display: flex;
  flex-direction: column;
}

.content-area {
  flex: 1;
  padding: 32px;
  width: 100%;
  display: flex;
  justify-content: center;
}

@media (max-width: 768px) {
  .main-content {
    margin-left: 70px;
  }

  .content-area {
    padding: 20px;
  }
}

@media (max-width: 480px) {
  .main-content {
    margin-left: 60px;
  }

  .content-area {
    padding: 16px;
  }
}
</style> 