"""
文生图任务处理器
"""
from typing import Dict, Any, List
import logging
from ..core.base import (
    TaskType, TaskRequest, WorkflowConfig, BaseTaskProcessor,
    ValidationError
)
from ..core.task_manager import register_task_processor

logger = logging.getLogger(__name__)


@register_task_processor(TaskType.TEXT_TO_IMAGE)
class TextToImageProcessor(BaseTaskProcessor):
    """文生图任务处理器"""
    
    def get_supported_task_type(self) -> TaskType:
        """获取支持的任务类型"""
        return TaskType.TEXT_TO_IMAGE
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证文生图参数"""
        required_params = ['prompt']
        errors = []
        
        # 检查必需参数
        for param in required_params:
            if param not in params or not params[param]:
                errors.append(f"缺少必需参数: {param}")
        
        # 验证提示词长度
        if 'prompt' in params:
            prompt = params['prompt']
            if len(prompt) > 2000:
                errors.append("提示词长度不能超过2000字符")
            if len(prompt.strip()) == 0:
                errors.append("提示词不能为空")
        
        # 验证负面提示词
        if 'negative_prompt' in params:
            negative_prompt = params['negative_prompt']
            if len(negative_prompt) > 2000:
                errors.append("负面提示词长度不能超过2000字符")
        
        # 验证尺寸参数
        if 'width' in params:
            width = params['width']
            if not isinstance(width, int) or width < 64 or width > 2048:
                errors.append("宽度必须是64-2048之间的整数")
            if width % 64 != 0:
                errors.append("宽度必须是64的倍数")
        
        if 'height' in params:
            height = params['height']
            if not isinstance(height, int) or height < 64 or height > 2048:
                errors.append("高度必须是64-2048之间的整数")
            if height % 64 != 0:
                errors.append("高度必须是64的倍数")
        
        # 验证采样参数
        if 'steps' in params:
            steps = params['steps']
            if not isinstance(steps, int) or steps < 1 or steps > 100:
                errors.append("采样步数必须是1-100之间的整数")
        
        if 'cfg_scale' in params:
            cfg_scale = params['cfg_scale']
            if not isinstance(cfg_scale, (int, float)) or cfg_scale < 1.0 or cfg_scale > 20.0:
                errors.append("CFG Scale必须是1.0-20.0之间的数值")
        
        if 'batch_size' in params:
            batch_size = params['batch_size']
            if not isinstance(batch_size, int) or batch_size < 1 or batch_size > 8:
                errors.append("批量大小必须是1-8之间的整数")
        
        if 'seed' in params:
            seed = params['seed']
            if not isinstance(seed, int) or (seed < -1 or seed > 2147483647):
                errors.append("种子必须是-1到2147483647之间的整数")
        
        if errors:
            raise ValidationError("; ".join(errors))
        
        return True
    
    def process_params(self, request: TaskRequest, config: WorkflowConfig) -> Dict[str, Any]:
        """处理文生图参数 - 使用新的工作流参数处理器"""
        from ..core.workflow_parameter_processor import get_workflow_parameter_processor
        from ..core.config_manager import get_config_manager

        config_manager = get_config_manager()
        workflow_processor = get_workflow_parameter_processor(config_manager)

        # 提取前端参数
        frontend_params = self._extract_frontend_params(request)

        # 使用新的参数处理器生成完整工作流
        workflow_name = request.workflow_name or "sd_basic"  # 默认使用sd_basic

        try:
            # 生成完整的工作流数据（已注入参数）
            complete_workflow = workflow_processor.process_workflow_request(
                workflow_name, frontend_params
            )

            logger.info(f"文生图工作流生成完成: {request.task_id}, 工作流: {workflow_name}")
            return complete_workflow

        except Exception as e:
            logger.error(f"文生图参数处理失败 {request.task_id}: {e}")
            raise ValidationError(f"参数处理失败: {e}")

    def _extract_frontend_params(self, request: TaskRequest) -> Dict[str, Any]:
        """从请求中提取前端参数"""
        # 从request.parameters中提取所有参数
        params = request.parameters.copy()

        # 移除非业务参数
        non_business_params = ['task_id', 'user_id', 'task_type', 'workflow_name']
        for param in non_business_params:
            params.pop(param, None)

        logger.debug(f"提取的前端参数: {list(params.keys())}")
        return params
    
    def _apply_text_to_image_specific_processing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """应用文生图特有的参数处理"""
        result = params.copy()
        
        # 处理随机种子
        if result.get('seed', -1) == -1:
            import random
            result['seed'] = random.randint(0, 2147483647)
        
        # 确保必要的默认值
        result.setdefault('negative_prompt', '')
        result.setdefault('sampler', 'euler')
        result.setdefault('scheduler', 'normal')
        result.setdefault('batch_size', 1)
        
        # 处理分辨率预设
        if 'resolution_preset' in result:
            preset = result['resolution_preset']
            resolution_presets = {
                'square_512': (512, 512),
                'square_768': (768, 768),
                'square_1024': (1024, 1024),
                'portrait_512': (512, 768),
                'portrait_768': (768, 1024),
                'landscape_512': (768, 512),
                'landscape_768': (1024, 768),
                'sdxl_square': (1024, 1024),
                'sdxl_portrait': (832, 1216),
                'sdxl_landscape': (1216, 832)
            }
            
            if preset in resolution_presets:
                result['width'], result['height'] = resolution_presets[preset]
                del result['resolution_preset']
        
        # 处理质量预设
        if 'quality_preset' in result:
            preset = result['quality_preset']
            quality_presets = {
                'draft': {'steps': 10, 'cfg_scale': 5.0},
                'normal': {'steps': 20, 'cfg_scale': 7.0},
                'high': {'steps': 30, 'cfg_scale': 8.0},
                'ultra': {'steps': 50, 'cfg_scale': 9.0}
            }
            
            if preset in quality_presets:
                result.update(quality_presets[preset])
                del result['quality_preset']
        
        return result
    
    def get_required_parameters(self) -> List[str]:
        """获取必需参数列表"""
        return ['prompt']
    
    def get_optional_parameters(self) -> List[str]:
        """获取可选参数列表"""
        return [
            'negative_prompt', 'width', 'height', 'steps', 'cfg_scale',
            'sampler', 'scheduler', 'batch_size', 'seed', 'resolution_preset',
            'quality_preset'
        ]
    
    def get_parameter_descriptions(self) -> Dict[str, str]:
        """获取参数描述"""
        return {
            'prompt': '正面提示词，描述想要生成的图像内容',
            'negative_prompt': '负面提示词，描述不想要的内容',
            'width': '图像宽度，必须是64的倍数',
            'height': '图像高度，必须是64的倍数',
            'steps': '采样步数，影响图像质量和生成时间',
            'cfg_scale': 'CFG引导强度，控制对提示词的遵循程度',
            'sampler': '采样器类型',
            'scheduler': '调度器类型',
            'batch_size': '批量生成数量',
            'seed': '随机种子，-1表示随机',
            'resolution_preset': '分辨率预设',
            'quality_preset': '质量预设'
        }
    
    def estimate_processing_time(self, params: Dict[str, Any]) -> float:
        """估算处理时间（秒）"""
        base_time = 30  # 基础时间
        
        # 根据分辨率调整
        width = params.get('width', 512)
        height = params.get('height', 512)
        resolution_factor = (width * height) / (512 * 512)
        
        # 根据步数调整
        steps = params.get('steps', 20)
        steps_factor = steps / 20
        
        # 根据批量大小调整
        batch_size = params.get('batch_size', 1)
        
        estimated_time = base_time * resolution_factor * steps_factor * batch_size
        return min(estimated_time, 600)  # 最大10分钟
