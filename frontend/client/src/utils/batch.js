/**
 * 生成批次ID
 * @returns {string} 批次ID
 */
export const generateBatchId = () => {
  return `batch_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
};

/**
 * 按批次分组任务
 * @param {Array} tasks 任务列表
 * @returns {Object} 分组后的任务
 */
export const groupTasksByBatch = (tasks) => {
  const batches = {};
  
  tasks.forEach(task => {
    const batchId = task.batch_id || `single_${task.id}`;
    if (!batches[batchId]) {
      batches[batchId] = {
        id: batchId,
        tasks: [],
        created_at: task.created_at,
        status: 'completed'
      };
    }
    batches[batchId].tasks.push(task);
    
    // 更新批次状态
    if (task.status === 'processing' || task.status === 'queued') {
      batches[batchId].status = 'processing';
    } else if (task.status === 'failed' && batches[batchId].status !== 'processing') {
      batches[batchId].status = 'failed';
    }
  });
  
  // 转换为数组并按时间倒序排序
  return Object.values(batches).sort((a, b) => 
    new Date(b.created_at) - new Date(a.created_at)
  );
};

/**
 * 获取批次状态
 * @param {Array} tasks 批次中的任务列表
 * @returns {string} 状态
 */
export const getBatchStatus = (tasks) => {
  if (!tasks || tasks.length === 0) return 'unknown';
  
  if (tasks.some(t => t.status === 'processing' || t.status === 'queued')) {
    return 'processing';
  }
  
  if (tasks.every(t => t.status === 'completed')) {
    return 'completed';
  }
  
  if (tasks.some(t => t.status === 'failed')) {
    return 'failed';
  }
  
  return 'unknown';
};

/**
 * 获取批次进度
 * @param {Array} tasks 批次中的任务列表
 * @returns {number} 进度百分比
 */
export const getBatchProgress = (tasks) => {
  if (!tasks || tasks.length === 0) return 0;
  
  const processingTask = tasks.find(t => t.status === 'processing');
  if (processingTask) {
    return processingTask.progress || 0;
  }
  
  const completedCount = tasks.filter(t => t.status === 'completed').length;
  return (completedCount / tasks.length) * 100;
};

/**
 * 获取批次中的主任务（第一个任务）
 * @param {Array} tasks 批次中的任务列表
 * @returns {Object|null} 主任务
 */
export const getBatchMainTask = (tasks) => {
  if (!tasks || tasks.length === 0) return null;
  return tasks[0];
};

/**
 * 检查批次是否需要轮询状态
 * @param {string} status 批次状态
 * @returns {boolean} 是否需要轮询
 */
export const shouldPollBatchStatus = (status) => {
  return status === 'processing' || status === 'queued';
}; 