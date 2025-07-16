<template>
  <el-card class="tasks-card">
    <div class="tasks-header">
      <div class="tasks-title">任务管理</div>
      <el-button @click="refreshTasks" :loading="loading" type="primary" size="small">
        <i class="el-icon-refresh"></i> 刷新
      </el-button>
    </div>

    <!-- 筛选器 -->
    <div class="tasks-filters">
      <el-select v-model="filters.status" placeholder="状态筛选" clearable @change="loadTasks">
        <el-option label="队列中" value="queued"></el-option>
        <el-option label="处理中" value="processing"></el-option>
        <el-option label="已完成" value="completed"></el-option>
        <el-option label="失败" value="failed"></el-option>
        <el-option label="已取消" value="cancelled"></el-option>
      </el-select>

      <el-select v-model="filters.task_type" placeholder="任务类型" clearable @change="loadTasks">
        <el-option label="文生图" value="text_to_image"></el-option>
      </el-select>
    </div>

    <!-- 任务表格 -->
    <el-table :data="tasks" style="width: 100%;" v-loading="loading">
      <el-table-column prop="task_id" label="任务ID" width="280">
        <template slot-scope="scope">
          <el-tooltip :content="scope.row.task_id" placement="top">
            <span>{{ scope.row.task_id.substring(0, 8) }}...</span>
          </el-tooltip>
        </template>
      </el-table-column>

      <el-table-column prop="task_type" label="类型" width="100">
        <template slot-scope="scope">
          <el-tag size="small">{{ getTaskTypeLabel(scope.row.task_type) }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="100">
        <template slot-scope="scope">
          <el-tag :type="getStatusType(scope.row.status)" size="small">
            {{ getStatusLabel(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="prompt" label="提示词" min-width="200">
        <template slot-scope="scope">
          <div style="max-width: 200px;">
            <div v-if="scope.row.prompt" style="font-size: 12px; color: #606266; margin-bottom: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              <strong>正向:</strong> {{ scope.row.prompt }}
            </div>
            <div v-if="scope.row.negative_prompt" style="font-size: 12px; color: #909399; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              <strong>反向:</strong> {{ scope.row.negative_prompt }}
            </div>
            <div v-if="!scope.row.prompt && !scope.row.negative_prompt" style="font-size: 12px; color: #C0C4CC;">
              无提示词
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="progress" label="进度" width="120">
        <template slot-scope="scope">
          <el-progress :percentage="scope.row.progress" :status="getProgressStatus(scope.row.status)"></el-progress>
        </template>
      </el-table-column>

      <el-table-column prop="message" label="消息" min-width="200" show-overflow-tooltip></el-table-column>

      <el-table-column prop="created_at" label="创建时间" width="160">
        <template slot-scope="scope">
          {{ formatTime(scope.row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="120">
        <template slot-scope="scope">
          <el-button
            v-if="scope.row.status === 'completed' && scope.row.result_data"
            @click="viewResult(scope.row)"
            type="text"
            size="small">
            查看结果
          </el-button>
          <el-button
            v-if="['queued', 'processing'].includes(scope.row.status)"
            @click="cancelTask(scope.row.task_id)"
            type="text"
            size="small">
            取消
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 结果查看对话框 -->
    <el-dialog
      title="任务结果"
      :visible.sync="resultDialog.visible"
      width="80%"
      class="result-dialog"
      @close="closeResultDialog">
      <div v-if="resultDialog.task" class="result-content">
        <!-- 任务信息 -->
        <div class="task-info">
          <div class="info-item">
            <span class="label">任务ID:</span>
            <span class="value">{{ resultDialog.task.task_id }}</span>
          </div>
          <div class="info-item">
            <span class="label">创建时间:</span>
            <span class="value">{{ formatTime(resultDialog.task.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="label">完成时间:</span>
            <span class="value">{{ formatTime(resultDialog.task.updated_at) }}</span>
          </div>
        </div>

        <!-- 提示词信息 -->
        <div class="prompt-info" v-if="resultDialog.task.prompt || resultDialog.task.negative_prompt">
          <div v-if="resultDialog.task.prompt" class="info-item">
            <span class="label">正向提示词:</span>
            <span class="value">{{ resultDialog.task.prompt }}</span>
          </div>
          <div v-if="resultDialog.task.negative_prompt" class="info-item">
            <span class="label">反向提示词:</span>
            <span class="value">{{ resultDialog.task.negative_prompt }}</span>
          </div>
        </div>

        <!-- 结果图片 -->
        <div class="result-images" v-if="resultDialog.task.result_data && resultDialog.task.result_data.files">
          <div class="image-grid">
            <div v-for="(file, index) in resultDialog.task.result_data.files" :key="index" class="image-item">
              <img :src="getImageUrl(file)" :alt="'结果图片 ' + (index + 1)" @click="previewImage(file)" />
              <div class="image-actions">
                <el-button type="text" size="small" @click="downloadImage(file, index)">
                  <i class="el-icon-download"></i> 下载
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 图片预览 -->
    <el-image-viewer
      v-if="previewVisible"
      :url-list="previewUrls"
      :initial-index="previewIndex"
      @close="closePreview"
    />

    <!-- 分页 -->
    <div class="tasks-pagination">
      <el-pagination
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        :current-page="pagination.page"
        :page-sizes="[10, 20, 50, 100]"
        :page-size="pagination.size"
        layout="total, sizes, prev, pager, next, jumper"
        :total="pagination.total">
      </el-pagination>
    </div>
  </el-card>
</template>

<script>
import api from '../api'

export default {
  name: 'Tasks',
  data() {
    return {
      tasks: [],
      loading: false,
      filters: {
        status: '',
        task_type: ''
      },
      pagination: {
        page: 1,
        size: 20,
        total: 0
      },
      resultDialog: {
        visible: false,
        task: null
      },
      previewVisible: false,
      previewUrls: [],
      previewIndex: 0
    }
  },
  mounted() {
    this.loadTasks()
    // 设置定时刷新
    this.refreshInterval = setInterval(() => {
      this.loadTasks(false) // 静默刷新
    }, 5000)
  },
  beforeDestroy() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  },
  methods: {
    async loadTasks(showLoading = true) {
      if (showLoading) this.loading = true

      try {
        const params = {
          limit: this.pagination.size,
          offset: (this.pagination.page - 1) * this.pagination.size
        }

        if (this.filters.status) params.status = this.filters.status
        if (this.filters.task_type) params.task_type = this.filters.task_type

        const response = await api.get('/admin/tasks', { params })

        this.tasks = response.data.tasks || []
        this.pagination.total = response.data.total || 0

      } catch (error) {
        console.error('加载任务列表失败:', error)
        this.$message.error('加载任务列表失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loading = false
      }
    },

    refreshTasks() {
      this.loadTasks(true)
    },

    handleSizeChange(size) {
      this.pagination.size = size
      this.pagination.page = 1
      this.loadTasks()
    },

    handleCurrentChange(page) {
      this.pagination.page = page
      this.loadTasks()
    },

    async cancelTask(taskId) {
      try {
        await this.$confirm('确定要取消这个任务吗？', '确认', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })

        await api.post(`/admin/tasks/${taskId}/cancel`)
        this.$message.success('任务已取消')
        this.loadTasks()

      } catch (error) {
        if (error !== 'cancel') {
          console.error('取消任务失败:', error)
          this.$message.error('取消任务失败: ' + (error.response?.data?.detail || error.message))
        }
      }
    },

    viewResult(task) {
      this.resultDialog.task = task
      this.resultDialog.visible = true

      // 准备预览URL列表
      if (task.result_data && task.result_data.files) {
        this.previewUrls = task.result_data.files.map(file => this.getImageUrl(file))
      }
    },

    closeResultDialog() {
      this.resultDialog.visible = false
      this.resultDialog.task = null
    },

    getImageUrl(file) {
      // 如果是完整URL，直接返回
      if (file.startsWith('http://') || file.startsWith('https://')) {
        return file
      }
      
      // 如果是相对路径，拼接baseURL
      const baseURL = api.defaults.baseURL
      if (file.startsWith('/')) {
        return baseURL + file
      }
      
      // 否则假设是输出目录的文件
      return `${baseURL}/outputs/${file}`
    },

    previewImage(file) {
      const index = this.resultDialog.task.result_data.files.indexOf(file)
      this.previewIndex = Math.max(0, index)
      this.previewVisible = true
    },

    closePreview() {
      this.previewVisible = false
    },

    async downloadImage(file, index) {
      try {
        const taskId = this.resultDialog.task.task_id
        const response = await api.get(`/api/v2/tasks/${taskId}/download?index=${index}`, {
          responseType: 'blob'
        })
        
        // 创建下载链接
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', file.split('/').pop()) // 使用原始文件名
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
      } catch (error) {
        console.error('下载失败:', error)
        this.$message.error('下载失败: ' + (error.response?.data?.detail || error.message))
      }
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

    getProgressStatus(status) {
      if (status === 'completed') return 'success'
      if (status === 'failed') return 'exception'
      return null
    },

    formatTime(timeStr) {
      if (!timeStr) return '-'
      return new Date(timeStr).toLocaleString('zh-CN')
    }
  }
}
</script>

<style scoped>
.tasks-card {
  margin: 32px;
  padding: 24px;
}

.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.tasks-title {
  font-size: 1.3rem;
  font-weight: 600;
}

.tasks-filters {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.tasks-filters .el-select {
  width: 150px;
}

.tasks-pagination {
  margin-top: 20px;
  text-align: right;
}

.result-dialog {
  .result-content {
    padding: 20px;
  }

  .task-info {
    margin-bottom: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 8px;
  }

  .prompt-info {
    margin-bottom: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 8px;
  }

  .info-item {
    margin-bottom: 10px;
    display: flex;
    align-items: flex-start;

    .label {
      font-weight: bold;
      color: #606266;
      width: 100px;
      flex-shrink: 0;
    }

    .value {
      color: #333;
      word-break: break-all;
    }
  }

  .result-images {
    margin-top: 20px;
  }

  .image-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
    margin-top: 20px;
  }

  .image-item {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);

    img {
      width: 100%;
      height: 200px;
      object-fit: cover;
      cursor: pointer;
      transition: transform 0.3s;

      &:hover {
        transform: scale(1.05);
      }
    }

    .image-actions {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 8px;
      background: rgba(0,0,0,0.5);
      display: flex;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.3s;

      .el-button {
        color: white;
        &:hover {
          color: #409EFF;
        }
      }
    }

    &:hover .image-actions {
      opacity: 1;
    }
  }
}
</style>