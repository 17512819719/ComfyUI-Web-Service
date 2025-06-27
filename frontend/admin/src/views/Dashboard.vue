<template>
  <div class="dashboard-panel">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">节点数</div>
          <div class="stat-value">4</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">活跃任务</div>
          <div class="stat-value">12</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">CPU使用率</div>
          <el-progress type="circle" :percentage="17" color="#4fc08d" :width="60" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">内存使用率</div>
          <el-progress type="circle" :percentage="51" color="#409eff" :width="60" />
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="20" style="margin-top:24px;">
      <el-col :span="16">
        <el-card>
          <div class="stat-label">任务流量趋势</div>
          <div id="chart" style="height:220px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="stat-label">节点状态</div>
          <el-table :data="nodeStatus" size="small" style="margin-top:8px;">
            <el-table-column prop="name" label="节点" />
            <el-table-column prop="status" label="状态" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
export default {
  name: 'Dashboard',
  data() {
    return {
      nodeStatus: [
        { name: 'Node-1', status: '在线' },
        { name: 'Node-2', status: '离线' },
        { name: 'Node-3', status: '在线' },
        { name: 'Node-4', status: '在线' }
      ]
    }
  },
  mounted() {
    // 示例折线图（可用 ECharts 或 Chart.js）
    if (window.echarts) {
      const chart = window.echarts.init(document.getElementById('chart'));
      chart.setOption({
        xAxis: { type: 'category', data: ['12:00','12:05','12:10','12:15','12:20','12:25'] },
        yAxis: { type: 'value' },
        series: [{
          data: [120, 132, 101, 134, 90, 230],
          type: 'line',
          smooth: true,
          areaStyle: { color: '#e6f7f1' },
          lineStyle: { color: '#4fc08d' }
        }],
        grid: { left: 30, right: 20, top: 30, bottom: 30 },
        tooltip: { trigger: 'axis' }
      });
    }
  }
}
</script>

<style scoped>
.dashboard-panel {
  padding: 32px 16px;
}
</style> 