<template>
  <el-card class="users-card">
    <div class="users-title">用户管理</div>
    <el-table :data="users" style="width: 100%;">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="role" label="角色" />
      <!-- 可添加更多列 -->
    </el-table>
  </el-card>
</template>

<script>
export default {
  name: 'Users',
  data() {
    return {
      users: []
    }
  },
  mounted() {
    // TODO: 拉取用户数据
  }
}
</script>

<style scoped>
.users-card {
  margin: 32px;
  padding: 24px;
}
.users-title {
  font-size: 1.3rem;
  font-weight: 600;
  margin-bottom: 16px;
}
</style> 