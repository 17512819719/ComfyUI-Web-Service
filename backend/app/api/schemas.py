"""
API数据模型和验证模式
"""
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class TaskTypeEnum(str, Enum):
    """任务类型枚举"""
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_VIDEO = "image_to_video"


class TaskStatusEnum(str, Enum):
    """任务状态枚举"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseTaskRequest(BaseModel):
    """基础任务请求"""
    workflow_name: Optional[str] = Field(None, description="工作流名称")
    priority: int = Field(1, ge=1, le=10, description="任务优先级")
    
    class Config:
        extra = "allow"  # 允许额外字段


class TextToImageRequest(BaseTaskRequest):
    """文生图请求"""
    prompt: str = Field(..., min_length=1, max_length=2000, description="正面提示词")
    negative_prompt: Optional[str] = Field("", max_length=2000, description="负面提示词")
    width: Optional[int] = Field(512, ge=64, le=2048, description="图像宽度")
    height: Optional[int] = Field(512, ge=64, le=2048, description="图像高度")
    # steps: Optional[int] = Field(20, ge=1, le=100, description="采样步数")
    # cfg_scale: Optional[float] = Field(7.0, ge=1.0, le=20.0, description="CFG引导强度")
    # sampler: Optional[str] = Field("euler", description="采样器")
    # scheduler: Optional[str] = Field("normal", description="调度器")
    # batch_size: Optional[int] = Field(1, ge=1, le=8, description="批量大小")
    # batch_size: Optional[int] = Field(None, description="批量大小")
    seed: Optional[int] = Field(-1, ge=-1, le=2147483647, description="随机种子")

    # 模型和工作流参数
    checkpoint: Optional[str] = Field(None, description="模型检查点文件")
    workflow_name: Optional[str] = Field("sd_basic", description="工作流名称")

    # 预设参数
    # resolution_preset: Optional[str] = Field(None, description="分辨率预设")
    # quality_preset: Optional[str] = Field(None, description="质量预设")
    
    @validator('width', 'height')
    def validate_dimensions(cls, v):
        if v % 64 != 0:
            raise ValueError('尺寸必须是64的倍数')
        return v


class ImageToVideoRequest(BaseTaskRequest):
    """图生视频请求"""
    prompt: str = Field(..., min_length=1, max_length=2000, description="正面提示词")
    negative_prompt: Optional[str] = Field("", max_length=2000, description="负面提示词")
    image: str = Field(..., description="输入图片路径或base64编码")

    # 工作流参数
    workflow_name: Optional[str] = Field("Wan2.1 i2v", description="工作流名称")

    class Config:
        extra = "allow"  # 允许额外字段


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatusEnum = Field(..., description="任务状态")
    message: str = Field("", description="状态消息")
    progress: float = Field(0.0, ge=0.0, le=100.0, description="进度百分比")
    result_data: Optional[Dict[str, Any]] = Field(None, description="结果数据")
    error_message: Optional[str] = Field(None, description="错误消息")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    estimated_time: Optional[float] = Field(None, description="预估处理时间（秒）")


class TaskSubmissionResponse(BaseModel):
    """任务提交响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatusEnum = Field(..., description="任务状态")
    message: str = Field(..., description="提交消息")
    estimated_time: Optional[float] = Field(None, description="预估处理时间（秒）")


class WorkflowInfo(BaseModel):
    """工作流信息"""
    name: str = Field(..., description="工作流名称")
    version: str = Field(..., description="版本")
    description: str = Field(..., description="描述")
    task_type: TaskTypeEnum = Field(..., description="任务类型")
    default_params: Dict[str, Any] = Field(..., description="默认参数")
    param_rules: Dict[str, Any] = Field(..., description="参数规则")


class WorkflowListResponse(BaseModel):
    """工作流列表响应"""
    workflows: Dict[str, List[WorkflowInfo]] = Field(..., description="按任务类型分组的工作流")
    total_count: int = Field(..., description="总数量")


class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    task_types: Dict[str, Dict[str, Any]] = Field(..., description="任务类型配置")
    supported_formats: Dict[str, List[str]] = Field(..., description="支持的文件格式")
    limits: Dict[str, Any] = Field(..., description="系统限制")
    presets: Dict[str, Dict[str, Any]] = Field(..., description="预设配置")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    timestamp: str = Field(..., description="检查时间")
    services: Dict[str, str] = Field(..., description="各服务状态")
    queue_info: Dict[str, Any] = Field(..., description="队列信息")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: str = Field(..., description="错误时间")


class BatchTaskRequest(BaseModel):
    """批量任务请求"""
    tasks: List[TextToImageRequest] = Field(..., description="任务列表")
    batch_name: Optional[str] = Field(None, description="批次名称")
    priority: int = Field(1, ge=1, le=10, description="批次优先级")


class BatchTaskResponse(BaseModel):
    """批量任务响应"""
    batch_id: str = Field(..., description="批次ID")
    task_ids: List[str] = Field(..., description="任务ID列表")
    total_tasks: int = Field(..., description="总任务数")
    message: str = Field(..., description="提交消息")


class TaskStatistics(BaseModel):
    """任务统计"""
    total_tasks: int = Field(..., description="总任务数")
    queued_tasks: int = Field(..., description="队列中的任务数")
    processing_tasks: int = Field(..., description="处理中的任务数")
    completed_tasks: int = Field(..., description="已完成的任务数")
    failed_tasks: int = Field(..., description="失败的任务数")
    average_processing_time: float = Field(..., description="平均处理时间")


class QueueInfo(BaseModel):
    """队列信息"""
    queue_name: str = Field(..., description="队列名称")
    active_tasks: int = Field(..., description="活跃任务数")
    scheduled_tasks: int = Field(..., description="计划任务数")
    reserved_tasks: int = Field(..., description="保留任务数")


class WorkerInfo(BaseModel):
    """工作节点信息"""
    worker_name: str = Field(..., description="工作节点名称")
    status: str = Field(..., description="状态")
    active_tasks: int = Field(..., description="活跃任务数")
    processed_tasks: int = Field(..., description="已处理任务数")
    load_average: List[float] = Field(..., description="负载平均值")


class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    system_status: str = Field(..., description="系统状态")
    task_statistics: TaskStatistics = Field(..., description="任务统计")
    queue_info: List[QueueInfo] = Field(..., description="队列信息")
    worker_info: List[WorkerInfo] = Field(..., description="工作节点信息")
    timestamp: str = Field(..., description="状态时间")


# 参数预设定义
RESOLUTION_PRESETS = {
    'square_512': {'width': 512, 'height': 512},
    'square_768': {'width': 768, 'height': 768},
    'square_1024': {'width': 1024, 'height': 1024},
    'portrait_512': {'width': 512, 'height': 768},
    'portrait_768': {'width': 768, 'height': 1024},
    'landscape_512': {'width': 768, 'height': 512},
    'landscape_768': {'width': 1024, 'height': 768},
    'sdxl_square': {'width': 1024, 'height': 1024},
    'sdxl_portrait': {'width': 832, 'height': 1216},
    'sdxl_landscape': {'width': 1216, 'height': 832}
}

QUALITY_PRESETS = {
    'draft': {'steps': 10, 'cfg_scale': 5.0},
    'normal': {'steps': 20, 'cfg_scale': 7.0},
    'high': {'steps': 30, 'cfg_scale': 8.0},
    'ultra': {'steps': 50, 'cfg_scale': 9.0}
}

MOTION_PRESETS = {
    'subtle': 0.3,
    'moderate': 0.6,
    'strong': 0.9,
    'extreme': 1.0
}

LENGTH_PRESETS = {
    'short': 2.0,
    'medium': 5.0,
    'long': 8.0,
    'extended': 10.0
}

FPS_PRESETS = {
    'smooth': 24,
    'standard': 16,
    'basic': 12,
    'minimal': 8
}


# 节点管理相关数据模型
class NodeStatusEnum(str, Enum):
    """节点状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class NodeInfo(BaseModel):
    """节点信息"""
    node_id: str = Field(..., description="节点ID")
    host: str = Field(..., description="节点主机地址")
    port: int = Field(..., description="节点端口")
    status: NodeStatusEnum = Field(..., description="节点状态")
    current_load: int = Field(0, description="当前负载")
    max_concurrent: int = Field(4, description="最大并发数")
    load_percentage: float = Field(0.0, description="负载百分比")
    capabilities: List[str] = Field(default_factory=list, description="支持的任务类型")
    last_heartbeat: str = Field(..., description="最后心跳时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="节点元数据")


class NodeRegistrationRequest(BaseModel):
    """节点注册请求"""
    node_id: str = Field(..., description="节点ID")
    host: str = Field(..., description="节点主机地址")
    port: int = Field(..., ge=1, le=65535, description="节点端口")
    max_concurrent: int = Field(4, ge=1, le=16, description="最大并发数")
    capabilities: List[str] = Field(default_factory=list, description="支持的任务类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="节点元数据")


class ClusterStatsResponse(BaseModel):
    """集群统计响应"""
    total_nodes: int = Field(..., description="总节点数")
    online_nodes: int = Field(..., description="在线节点数")
    offline_nodes: int = Field(..., description="离线节点数")
    total_capacity: int = Field(..., description="总容量")
    current_load: int = Field(..., description="当前负载")
    load_percentage: float = Field(..., description="负载百分比")
    available_slots: int = Field(..., description="可用槽位")


class NodesListResponse(BaseModel):
    """节点列表响应"""
    nodes: List[NodeInfo] = Field(..., description="节点列表")
    cluster_stats: ClusterStatsResponse = Field(..., description="集群统计")


class LoadBalancingConfigResponse(BaseModel):
    """负载均衡配置响应"""
    strategy: str = Field(..., description="负载均衡策略")
    enable_failover: bool = Field(..., description="是否启用故障转移")
    max_retries: int = Field(..., description="最大重试次数")


class NodeOperationResponse(BaseModel):
    """节点操作响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    node_id: Optional[str] = Field(None, description="节点ID")
