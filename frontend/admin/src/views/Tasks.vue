<template>
  <el-card class="tasks-card">
    <div class="tasks-title">任务管理</div>
    <el-table :data="tasks" style="width: 100%;">
      <el-table-column prop="id" label="任务ID" />
      <el-table-column prop="status" label="状态" />
      <!-- 可添加更多列 -->
    </el-table>
  </el-card>
</template>

<script>
export default {
  name: 'Tasks',
  data() {
    return {
      tasks: []
    }
  },
  mounted() {
    // TODO: 拉取任务数据
  }
}
</script>

<style scoped>
.tasks-card {
  margin: 32px;
  padding: 24px;
}
.tasks-title {
  font-size: 1.3rem;
  font-weight: 600;
  margin-bottom: 16px;
}
</style> 