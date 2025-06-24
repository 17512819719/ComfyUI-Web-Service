from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from datetime import datetime
import uuid

class TaskStatus(str, Enum):
    """任务状态枚举"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class GenerationType(str, Enum):
    """生成类型枚举"""
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_VIDEO = "image_to_video"

class SamplerType(str, Enum):
    """采样器类型"""
    DPMPP_2M = "dpmpp_2m"
    UNI_PC = "uni_pc"
    EULER_A = "euler_a"
    DDIM = "ddim"

class SchedulerType(str, Enum):
    """调度器类型"""
    SGM_UNIFORM = "sgm_uniform"
    SIMPLE = "simple"
    NORMAL = "normal"

# 基础请求模型
class BaseGenerationRequest(BaseModel):
    """生成请求基础模型"""
    task_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    
    class Config:
        use_enum_values = True

# 文生图请求模型
class TextToImageRequest(BaseGenerationRequest):
    """文生图请求模型"""
    prompt: str = Field(..., description="正面提示词", min_length=1, max_length=2000)
    negative_prompt: str = Field("", description="负面提示词", max_length=1000)
    width: int = Field(512, description="图像宽度", ge=64, le=2048)
    height: int = Field(512, description="图像高度", ge=64, le=2048)
    steps: int = Field(20, description="采样步数", ge=1, le=100)
    cfg_scale: float = Field(7.0, description="CFG引导强度", ge=1.0, le=30.0)
    seed: int = Field(42, description="随机种子")
    batch_size: int = Field(1, description="批次数量", ge=1, le=12)
    sampler: SamplerType = Field(SamplerType.DPMPP_2M, description="采样器类型")
    scheduler: SchedulerType = Field(SchedulerType.SGM_UNIFORM, description="调度器类型")
    model_name: Optional[str] = Field(None, description="使用的模型名称")
    
    @field_validator('width', 'height')
    @classmethod
    def validate_dimensions(cls, v):
        """验证尺寸必须是64的倍数"""
        if v % 64 != 0:
            raise ValueError('宽度和高度必须是64的倍数')
        return v
    
    @field_validator('seed')
    @classmethod
    def validate_seed(cls, v):
        """验证种子值"""
        if v != -1 and (v < 0 or v > 2**32 - 1):
            raise ValueError('种子值必须在0到2^32-1之间，或-1表示随机')
        return v

# 图生视频请求模型
class ImageToVideoRequest(BaseGenerationRequest):
    """图生视频请求模型"""
    image_path: str = Field(..., description="输入图像路径")
    duration: float = Field(5.0, description="视频时长(秒)", ge=1.0, le=30.0)
    fps: int = Field(8, description="帧率", ge=1, le=60)
    motion_strength: float = Field(0.8, description="运动强度", ge=0.0, le=2.0)
    width: int = Field(512, description="视频宽度", ge=64, le=1024)
    height: int = Field(768, description="视频高度", ge=64, le=1024)
    frames: int = Field(65, description="总帧数", ge=1, le=300)
    cfg_scale: float = Field(6.0, description="CFG引导强度", ge=1.0, le=20.0)
    steps: int = Field(20, description="采样步数", ge=1, le=100)
    seed: int = Field(42, description="随机种子")
    sampler: SamplerType = Field(SamplerType.UNI_PC, description="采样器类型")
    scheduler: SchedulerType = Field(SchedulerType.SIMPLE, description="调度器类型")
    
    # 提示词（用于万相模型）
    prompt: Optional[str] = Field("", description="视频生成提示词", max_length=2000)
    negative_prompt: Optional[str] = Field("", description="负面提示词", max_length=1000)
    
    @field_validator('frames')
    @classmethod
    def calculate_frames(cls, v, info):
        """根据时长和帧率计算帧数"""
        if 'duration' in info.data and 'fps' in info.data:
            calculated_frames = int(info.data['duration'] * info.data['fps'])
            return max(calculated_frames, 1)
        return v

# 通用生成请求（用于API）
class GenerationRequest(BaseModel):
    """通用生成请求模型"""
    generation_type: GenerationType
    text_to_image: Optional[TextToImageRequest] = None
    image_to_video: Optional[ImageToVideoRequest] = None
    
    @field_validator('text_to_image', 'image_to_video')
    @classmethod
    def validate_request_data(cls, v, info):
        """验证请求数据的一致性"""
        generation_type = info.data.get('generation_type')
        field_name = info.field_name
        
        if generation_type == GenerationType.TEXT_TO_IMAGE and field_name == 'text_to_image':
            if v is None:
                raise ValueError('文生图请求缺少必要参数')
        elif generation_type == GenerationType.IMAGE_TO_VIDEO and field_name == 'image_to_video':
            if v is None:
                raise ValueError('图生视频请求缺少必要参数')
        
        return v

# 任务状态响应模型
class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: TaskStatus
    progress: int = Field(0, description="进度百分比", ge=0, le=100)
    message: Optional[str] = Field(None, description="状态消息")
    result_url: Optional[Union[str, List[str]]] = None
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    estimated_time: Optional[int] = Field(None, description="预估剩余时间(秒)")

# 任务创建响应模型
class TaskCreateResponse(BaseModel):
    """任务创建响应模型"""
    task_id: str
    status: TaskStatus
    message: str
    estimated_time: Optional[int] = Field(None, description="预估完成时间(秒)")

# 用户认证模型
class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)

class TokenResponse(BaseModel):
    """令牌响应模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = Field(None, description="过期时间(秒)")

# ComfyUI工作流节点模型
class ComfyUINode(BaseModel):
    """ComfyUI节点模型"""
    id: int
    type: str
    pos: List[float]
    size: List[float]
    flags: Dict[str, Any] = {}
    order: int
    mode: int
    inputs: List[Dict[str, Any]] = []
    outputs: List[Dict[str, Any]] = []
    properties: Dict[str, Any] = {}
    widgets_values: List[Any] = []
    title: Optional[str] = None
    color: Optional[str] = None
    bgcolor: Optional[str] = None

class ComfyUIWorkflow(BaseModel):
    """ComfyUI工作流模型"""
    last_node_id: int
    last_link_id: int
    nodes: List[ComfyUINode]
    links: List[List[Any]]
    groups: List[Dict[str, Any]] = []
    config: Dict[str, Any] = {}
    extra: Dict[str, Any] = {}
    version: float

# 任务详情模型（用于数据库存储）
class TaskDetail(BaseModel):
    """任务详情模型"""
    task_id: str
    user_id: str
    generation_type: GenerationType
    status: TaskStatus
    progress: int = 0
    request_data: Dict[str, Any]
    result_data: Optional[Dict[str, Any]] = None
    workflow_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    file_paths: Optional[List[str]] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# API响应基础模型
class BaseResponse(BaseModel):
    """API响应基础模型"""
    success: bool = True
    message: str = "操作成功"
    code: int = 200

class ErrorResponse(BaseResponse):
    """错误响应模型"""
    success: bool = False
    error_type: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# 文件上传响应模型
class FileUploadResponse(BaseResponse):
    """文件上传响应模型"""
    file_id: str
    file_path: str
    file_size: int
    file_type: str

# 系统状态模型
class SystemStatus(BaseModel):
    """系统状态模型"""
    queue_size: int = Field(0, description="队列中的任务数量")
    processing_tasks: int = Field(0, description="正在处理的任务数量")
    available_workers: int = Field(0, description="可用工作器数量")
    system_load: float = Field(0.0, description="系统负载")
    memory_usage: float = Field(0.0, description="内存使用率")
    gpu_usage: Optional[float] = Field(None, description="GPU使用率")
    uptime: int = Field(0, description="系统运行时间(秒)")

# 配置模型
class AppConfig(BaseModel):
    """应用配置模型"""
    max_queue_size: int = 100
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    supported_image_formats: List[str] = ["jpg", "jpeg", "png", "webp"]
    supported_video_formats: List[str] = ["mp4", "webm", "avi"]
    default_image_width: int = 512
    default_image_height: int = 512
    default_video_fps: int = 8
    max_video_duration: float = 30.0
    cleanup_interval: int = 3600  # 1小时
    result_retention_days: int = 7