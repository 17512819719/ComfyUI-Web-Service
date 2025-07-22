export const getStatusText = (status) => {
    const statusMap = {
        'queued': '排队中',
        'processing': '生成中',
        'completed': '已完成',
        'failed': '失败',
        'cancelled': '已取消'
    };
    return statusMap[status] || status;
};

export const getStatusClass = (status) => {
    const classMap = {
        'queued': 'status-queued',
        'processing': 'status-processing',
        'completed': 'status-completed',
        'failed': 'status-failed',
        'cancelled': 'status-cancelled'
    };
    return classMap[status] || '';
}; 