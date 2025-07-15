<template>
  <div class="nodes-container">
    <!-- 集群统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stats-card">
          <div class="stats-content">
            <div class="stats-number">{{ clusterStats.total_nodes }}</div>
            <div class="stats-label">总节点数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stats-card">
          <div class="stats-content">
            <div class="stats-number online">{{ clusterStats.online_nodes }}</div>
            <div class="stats-label">在线节点</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stats-card">
          <div class="stats-content">
            <div class="stats-number">{{ clusterStats.current_load }}</div>
            <div class="stats-label">当前负载</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stats-card">
          <div class="stats-content">
            <div class="stats-number">{{ clusterStats.load_percentage.toFixed(1) }}%</div>
            <div class="stats-label">负载率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 节点列表 -->
    <el-card class="nodes-card">
      <template #header>
        <div class="card-header">
          <span class="nodes-title">节点管理</span>
          <el-button type="primary" @click="refreshNodes" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="nodes" style="width: 100%;" v-loading="loading">
        <el-table-column prop="node_id" label="节点ID" width="180" />
        <el-table-column label="地址" width="200">
          <template #default="scope">
            {{ scope.row.host }}:{{ scope.row.port }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="负载" width="150">
          <template #default="scope">
            <el-progress
              :percentage="scope.row.load_percentage"
              :color="getLoadColor(scope.row.load_percentage)"
              :show-text="false"
            />
            <span class="load-text">{{ scope.row.current_load }}/{{ scope.row.max_concurrent }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="capabilities" label="支持任务" width="150">
          <template #default="scope">
            <el-tag v-for="cap in scope.row.capabilities" :key="cap" size="small" class="capability-tag">
              {{ cap }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后心跳" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.last_heartbeat) }}
          </template>
        </el-table-column>
        <el-table-column label="元数据" min-width="200">
          <template #default="scope">
            <div v-if="scope.row.metadata">
              <div v-if="scope.row.metadata.gpu_model">GPU: {{ scope.row.metadata.gpu_model }}</div>
              <div v-if="scope.row.metadata.location">位置: {{ scope.row.metadata.location }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button
              size="small"
              @click="checkHealth(scope.row.node_id)"
              :loading="healthChecking[scope.row.node_id]"
            >
              健康检查
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { Refresh } from '@element-plus/icons-vue'
import api from '../api'

export default {
  name: 'Nodes',
  components: {
    Refresh
  },
  data() {
    return {
      nodes: [],
      clusterStats: {
        total_nodes: 0,
        online_nodes: 0,
        offline_nodes: 0,
        total_capacity: 0,
        current_load: 0,
        load_percentage: 0,
        available_slots: 0
      },
      loading: false,
      healthChecking: {}
    }
  },
  mounted() {
    this.loadNodes()
    // 定时刷新节点状态
    this.timer = setInterval(() => {
      this.loadNodes()
    }, 30000) // 30秒刷新一次
  },
  beforeUnmount() {
    if (this.timer) {
      clearInterval(this.timer)
    }
  },
  methods: {
    async loadNodes() {
      try {
        this.loading = true
        const response = await api.get('/api/nodes')
        this.nodes = response.data.nodes
        this.clusterStats = response.data.cluster_stats
      } catch (error) {
        console.error('加载节点数据失败:', error)
        this.$message.error('加载节点数据失败')
      } finally {
        this.loading = false
      }
    },
    async refreshNodes() {
      await this.loadNodes()
      this.$message.success('节点数据已刷新')
    },
    async checkHealth(nodeId) {
      try {
        this.$set(this.healthChecking, nodeId, true)
        const response = await api.get(`/api/nodes/${nodeId}/health`)
        if (response.data.success) {
          this.$message.success(`节点 ${nodeId} 健康检查通过`)
        } else {
          this.$message.warning(`节点 ${nodeId} 健康检查失败`)
        }
        // 刷新节点状态
        await this.loadNodes()
      } catch (error) {
        console.error('健康检查失败:', error)
        this.$message.error('健康检查失败')
      } finally {
        this.$set(this.healthChecking, nodeId, false)
      }
    },
    getStatusType(status) {
      const statusMap = {
        'online': 'success',
        'offline': 'danger',
        'busy': 'warning',
        'error': 'danger',
        'maintenance': 'info'
      }
      return statusMap[status] || 'info'
    },
    getStatusText(status) {
      const statusMap = {
        'online': '在线',
        'offline': '离线',
        'busy': '繁忙',
        'error': '错误',
        'maintenance': '维护中'
      }
      return statusMap[status] || status
    },
    getLoadColor(percentage) {
      if (percentage < 50) return '#67c23a'
      if (percentage < 80) return '#e6a23c'
      return '#f56c6c'
    },
    formatTime(timeStr) {
      return new Date(timeStr).toLocaleString('zh-CN')
    }
  }
}
</script>

<style scoped>
.nodes-container {
  padding: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stats-card {
  text-align: center;
}

.stats-content {
  padding: 10px;
}

.stats-number {
  font-size: 2rem;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 5px;
}

.stats-number.online {
  color: #67c23a;
}

.stats-label {
  font-size: 0.9rem;
  color: #909399;
}

.nodes-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nodes-title {
  font-size: 1.3rem;
  font-weight: 600;
}

.load-text {
  margin-left: 10px;
  font-size: 0.8rem;
  color: #909399;
}

.capability-tag {
  margin-right: 5px;
  margin-bottom: 2px;
}

.el-progress {
  width: 80px;
  display: inline-block;
}
</style>