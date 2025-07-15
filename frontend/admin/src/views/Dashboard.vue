<template>
  <div class="dashboard-panel">
    <!-- 系统状态卡片 -->
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">总节点数</div>
          <div class="stat-value">{{ systemStats.total_nodes || 0 }}</div>
          <div class="stat-sub">在线: {{ systemStats.online_nodes || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">活跃任务</div>
          <div class="stat-value">{{ systemStats.running_tasks || 0 }}</div>
          <div class="stat-sub">总计: {{ systemStats.total_tasks || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">已完成任务</div>
          <div class="stat-value">{{ systemStats.completed_tasks || 0 }}</div>
          <div class="stat-sub">失败: {{ systemStats.failed_tasks || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">系统负载</div>
          <el-progress
            type="circle"
            :percentage="Math.round((systemStats.system_load?.cpu || 0) * 100)"
            :color="getLoadColor((systemStats.system_load?.cpu || 0) * 100)"
            :width="60" />
          <div class="stat-sub">CPU负载</div>
        </el-card>
      </el-col>
    </el-row>
    <!-- 详细信息区域 -->
    <el-row :gutter="20" style="margin-top:24px;">
      <el-col :span="16">
        <el-card>
          <div class="card-header">
            <div class="stat-label">最近任务</div>
            <el-button @click="refreshData" :loading="loading" size="small" type="text">
              <i class="el-icon-refresh"></i> 刷新
            </el-button>
          </div>
          <el-table :data="recentTasks" size="small" style="margin-top:8px;" v-loading="loading">
            <el-table-column prop="task_id" label="任务ID" width="120">
              <template slot-scope="scope">
                <span>{{ scope.row.task_id.substring(0, 8) }}...</span>
              </template>
            </el-table-column>
            <el-table-column prop="task_type" label="类型" width="80">
              <template slot-scope="scope">
                <el-tag size="mini">{{ getTaskTypeLabel(scope.row.task_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template slot-scope="scope">
                <el-tag :type="getStatusType(scope.row.status)" size="mini">
                  {{ getStatusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度" width="100">
              <template slot-scope="scope">
                <el-progress :percentage="scope.row.progress" :show-text="false" :stroke-width="6"></el-progress>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="140">
              <template slot-scope="scope">
                {{ formatTime(scope.row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="card-header">
            <div class="stat-label">节点状态</div>
            <el-tag :type="allNodesOnline ? 'success' : 'warning'" size="small">
              {{ allNodesOnline ? '全部在线' : '部分离线' }}
            </el-tag>
          </div>
          <el-table :data="nodeStatus" size="small" style="margin-top:8px;" v-loading="loading">
            <el-table-column prop="name" label="节点" />
            <el-table-column prop="status" label="状态" width="80">
              <template slot-scope="scope">
                <el-tag :type="scope.row.status === 'online' ? 'success' : 'danger'" size="mini">
                  {{ scope.row.status === 'online' ? '在线' : '离线' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'Dashboard',
  data() {
    return {
      loading: false,
      systemStats: {
        total_nodes: 0,
        online_nodes: 0,
        total_tasks: 0,
        running_tasks: 0,
        completed_tasks: 0,
        failed_tasks: 0,
        system_load: {
          cpu: 0,
          memory: 0
        }
      },
      nodeStatus: [],
      recentTasks: []
    }
  },
  computed: {
    allNodesOnline() {
      return this.nodeStatus.length > 0 && this.nodeStatus.every(node => node.status === 'online')
    }
  },
  mounted() {
    this.loadDashboardData()
    // 设置定时刷新
    this.refreshInterval = setInterval(() => {
      this.loadDashboardData(false) // 静默刷新
    }, 10000)
  },
  beforeDestroy() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  },
  methods: {
    async loadDashboardData(showLoading = true) {
      if (showLoading) this.loading = true

      try {
        // 并行加载多个数据
        const [statsResponse, nodesResponse, tasksResponse] = await Promise.all([
          api.get('/admin/system/status').catch(() => ({ data: {} })),
          api.get('/admin/nodes').catch(() => ({ data: [] })),
          api.get('/admin/tasks', { params: { limit: 10, offset: 0 } }).catch(() => ({ data: { tasks: [] } }))
        ])

        // 更新系统统计
        this.systemStats = {
          ...this.systemStats,
          ...statsResponse.data
        }

        // 更新节点状态
        this.nodeStatus = (nodesResponse.data || []).map(node => ({
          name: node.name || `Node-${node.id}`,
          status: node.status || 'offline'
        }))

        // 更新最近任务
        this.recentTasks = tasksResponse.data.tasks || []

      } catch (error) {
        console.error('加载仪表板数据失败:', error)
        if (showLoading) {
          this.$message.error('加载数据失败: ' + (error.response?.data?.detail || error.message))
        }
      } finally {
        this.loading = false
      }
    },

    refreshData() {
      this.loadDashboardData(true)
    },

    getLoadColor(percentage) {
      if (percentage < 50) return '#67c23a'
      if (percentage < 80) return '#e6a23c'
      return '#f56c6c'
    },

    getTaskTypeLabel(type) {
      const labels = {
        'text_to_image': '文生图'
      }
      return labels[type] || type
    },

    getStatusLabel(status) {
      const labels = {
        'queued': '队列中',
        'processing': '处理中',
        'completed': '已完成',
        'failed': '失败',
        'cancelled': '已取消'
      }
      return labels[status] || status
    },

    getStatusType(status) {
      const types = {
        'queued': 'info',
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'cancelled': 'info'
      }
      return types[status] || 'info'
    },

    formatTime(timeStr) {
      if (!timeStr) return '-'
      const date = new Date(timeStr)
      const now = new Date()
      const diff = now - date

      if (diff < 60000) return '刚刚'
      if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
      return date.toLocaleDateString('zh-CN')
    }
  }
}
</script>

<style scoped>
.dashboard-panel {
  padding: 32px 16px;
}

.stat-card {
  text-align: center;
  padding: 20px;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  margin-bottom: 4px;
}

.stat-sub {
  font-size: 12px;
  color: #999;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
</style>