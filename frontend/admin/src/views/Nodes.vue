<template>
  <el-card class="nodes-card">
    <div class="nodes-title">节点管理</div>
    <el-table :data="nodes" style="width: 100%;">
      <el-table-column prop="name" label="节点名称" />
      <el-table-column prop="status" label="状态" />
      <!-- 可添加更多列 -->
    </el-table>
  </el-card>
</template>

<script>
export default {
  name: 'Nodes',
  data() {
    return {
      nodes: []
    }
  },
  mounted() {
    // TODO: 拉取节点数据
  }
}
</script>

<style scoped>
.nodes-card {
  margin: 32px;
  padding: 24px;
}
.nodes-title {
  font-size: 1.3rem;
  font-weight: 600;
  margin-bottom: 16px;
}
</style> 