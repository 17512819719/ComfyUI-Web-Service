<template>
  <div class="history">
    <div class="history-header">
      <h2>生成历史</h2>
      <div class="history-actions">
        <button class="btn btn-secondary" @click="refreshTasks">
          <i class="fas fa-sync"></i>
          刷新
        </button>
      </div>
    </div>

    <gallery-grid />
  </div>
</template>

<script setup>
import GalleryGrid from '@/components/gallery/GalleryGrid.vue'
import { useTaskStore } from '@/store/task'

const taskStore = useTaskStore()

const refreshTasks = async () => {
  await taskStore.fetchTasks()
}
</script>

<style scoped>
.history {
  min-height: 100vh;
  width: 100%;
  max-width: 1200px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding: 0;
}

.history-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.history-actions {
  display: flex;
  gap: 12px;
}

@media (max-width: 768px) {
  .history-header {
    margin-bottom: 24px;
  }

  .history-header h2 {
    font-size: 20px;
  }
}
</style> 