import json
import os
from typing import Dict, Any, Optional
import copy

class WorkflowManager:
    """工作流管理器，用于加载和管理ComfyUI JSON工作流文件"""
    
    def __init__(self, workflows_dir: str = "workflows"):
        self.workflows_dir = workflows_dir
        self.workflows_cache = {}
    
    def load_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """加载指定的工作流文件"""
        if workflow_name in self.workflows_cache:
            return copy.deepcopy(self.workflows_cache[workflow_name])
        
        workflow_path = os.path.join(self.workflows_dir, workflow_name)
        if not workflow_path.endswith('.json'):
            workflow_path += '.json'
        
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
                self.workflows_cache[workflow_name] = workflow
                return copy.deepcopy(workflow)
        except FileNotFoundError:
            print(f"工作流文件不存在: {workflow_path}")
            return None
        except json.JSONDecodeError as e:
            print(f"工作流文件格式错误: {workflow_path} - {e}")
            return None
        except Exception as e:
            print(f"加载工作流文件失败: {workflow_path} - {e}")
            return None
    
    def list_workflows(self) -> list:
        """列出所有可用的工作流文件"""
        workflows = []
        try:
            for file in os.listdir(self.workflows_dir):
                if file.endswith('.json'):
                    workflows.append(file[:-5])  # 移除.json后缀
        except FileNotFoundError:
            print(f"工作流目录不存在: {self.workflows_dir}")
        return workflows
    
    def update_workflow_parameters(self, workflow: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """更新工作流中的参数，并转换为ComfyUI API期望的格式"""
        workflow_copy = copy.deepcopy(workflow)
        
        # 定义参数映射规则
        param_mappings = {
            'prompt': {'node_types': ['CLIPTextEncode'], 'widget_index': 0},
            'negative_prompt': {'node_types': ['CLIPTextEncode'], 'widget_index': 0, 'negative': True},
            'width': {'node_types': ['EmptyLatentImage', 'EmptySD3LatentImage'], 'widget_index': 0},
            'height': {'node_types': ['EmptyLatentImage', 'EmptySD3LatentImage'], 'widget_index': 1},
            'batch_size': {'node_types': ['EmptyLatentImage', 'EmptySD3LatentImage'], 'widget_index': 2},
            'seed': {'node_types': ['KSampler'], 'widget_index': 0},
            'steps': {'node_types': ['KSampler'], 'widget_index': 2},
            'cfg_scale': {'node_types': ['KSampler'], 'widget_index': 3},
            'sampler_name': {'node_types': ['KSampler'], 'widget_index': 4},
            'scheduler': {'node_types': ['KSampler'], 'widget_index': 5},
            'denoise': {'node_types': ['KSampler'], 'widget_index': 6},
            'ckpt_name': {'node_types': ['CheckpointLoaderSimple'], 'widget_index': 0}
        }
        
        # 更新节点参数
        for node in workflow_copy.get('nodes', []):
            node_type = node.get('type', '')
            widgets_values = node.get('widgets_values', [])
            
            # 处理提示词
            if node_type == 'CLIPTextEncode':
                # 判断是正面还是负面提示词（通过位置或其他特征）
                is_negative = self._is_negative_prompt_node(node, workflow_copy)
                
                if is_negative and 'negative_prompt' in parameters:
                    if len(widgets_values) > 0:
                        widgets_values[0] = parameters['negative_prompt']
                elif not is_negative and 'prompt' in parameters:
                    if len(widgets_values) > 0:
                        widgets_values[0] = parameters['prompt']
            
            # 处理其他参数
            for param_name, mapping in param_mappings.items():
                if (node_type in mapping['node_types'] and 
                    param_name in parameters and 
                    param_name not in ['prompt', 'negative_prompt']):
                    
                    widget_index = mapping['widget_index']
                    if len(widgets_values) > widget_index:
                        widgets_values[widget_index] = parameters[param_name]
            
            # 更新节点的widgets_values
            node['widgets_values'] = widgets_values
        
        # 转换为ComfyUI API期望的格式
        return self._convert_to_api_format(workflow_copy, parameters)
    
    def _convert_to_api_format(self, workflow: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """将ComfyUI JSON工作流格式转换为API期望的格式"""
        api_workflow = {}
        
        # 定义不支持的节点类型（这些节点在API中不需要）
        unsupported_node_types = {
            'Note', 'mxSlider2D', 'PreviewImage'  # 这些是UI节点，API不需要
        }
        
        # 定义输出节点类型（这些节点会产生输出文件）
        output_node_types = {
            'SaveImage', 'VHS_VideoCombine', 'SaveVideo', 'SaveAudio'
        }
        
        has_output_node = False
        
        for node in workflow.get('nodes', []):
            node_id = str(node.get('id'))
            node_type = node.get('type')
            
            # 跳过不支持的节点类型
            if node_type in unsupported_node_types:
                print(f"[DEBUG] 跳过不支持的节点类型: {node_type} (ID: {node_id})")
                continue
            
            # 检查是否有输出节点
            if node_type in output_node_types:
                has_output_node = True
                print(f"[DEBUG] 找到输出节点: {node_type} (ID: {node_id})")
            
            if node_id and node_type:
                api_workflow[node_id] = {
                    "inputs": {},
                    "class_type": node_type
                }
                
                # 处理输入连接
                for input_info in node.get('inputs', []):
                    input_name = input_info.get('name')
                    link_id = input_info.get('link')
                    
                    if input_name and link_id is not None:
                        # 找到对应的输出节点
                        source_node_id, source_output_index = self._find_source_node(workflow, link_id)
                        if source_node_id is not None:
                            # 检查源节点是否在支持的节点中
                            source_node_type = self._get_node_type_by_id(workflow, source_node_id)
                            if source_node_type not in unsupported_node_types:
                                api_workflow[node_id]["inputs"][input_name] = [str(source_node_id), source_output_index]
                            else:
                                print(f"[DEBUG] 跳过来自不支持节点的连接: {source_node_type} -> {node_type}")
                
                # 处理widgets_values（直接参数）
                widgets_values = node.get('widgets_values', [])
                if widgets_values:
                    # 根据节点类型处理widgets_values
                    if node_type == 'CLIPTextEncode':
                        if len(widgets_values) > 0:
                            api_workflow[node_id]["inputs"]["text"] = widgets_values[0]
                    elif node_type in ['EmptyLatentImage', 'EmptySD3LatentImage']:
                        if len(widgets_values) >= 3:
                            api_workflow[node_id]["inputs"]["width"] = widgets_values[0]
                            api_workflow[node_id]["inputs"]["height"] = widgets_values[1]
                            api_workflow[node_id]["inputs"]["batch_size"] = widgets_values[2]
                    elif node_type == 'KSampler':
                        if len(widgets_values) >= 7:
                            api_workflow[node_id]["inputs"]["seed"] = widgets_values[0]
                            api_workflow[node_id]["inputs"]["steps"] = widgets_values[2]
                            api_workflow[node_id]["inputs"]["cfg"] = widgets_values[3]
                            api_workflow[node_id]["inputs"]["sampler_name"] = widgets_values[4]
                            api_workflow[node_id]["inputs"]["scheduler"] = widgets_values[5]
                            api_workflow[node_id]["inputs"]["denoise"] = widgets_values[6]
                    elif node_type == 'CheckpointLoaderSimple':
                        if len(widgets_values) > 0:
                            api_workflow[node_id]["inputs"]["ckpt_name"] = widgets_values[0]
                    elif node_type == 'ConditioningSetTimestepRange':
                        if len(widgets_values) >= 2:
                            api_workflow[node_id]["inputs"]["start"] = widgets_values[0]
                            api_workflow[node_id]["inputs"]["end"] = widgets_values[1]
                    elif node_type == 'ModelSamplingSD3':
                        if len(widgets_values) > 0:
                            api_workflow[node_id]["inputs"]["sampling"] = widgets_values[0]
                    elif node_type == 'SaveImage':
                        # 为SaveImage节点添加filename_prefix
                        task_id = parameters.get('task_id', self._extract_task_id_from_workflow(workflow))
                        if task_id:
                            api_workflow[node_id]["inputs"]["filename_prefix"] = f"ComfyUI_{task_id}"
        
        # 验证工作流是否有输出节点
        if not has_output_node:
            print(f"[WARNING] 工作流没有输出节点！这可能导致 'Prompt has no outputs' 错误")
            print(f"[WARNING] 请确保工作流包含以下节点之一: {output_node_types}")
        
        return api_workflow
    
    def _find_source_node(self, workflow: Dict[str, Any], link_id: int) -> tuple:
        """根据link_id找到源节点和输出索引"""
        for link in workflow.get('links', []):
            if link[0] == link_id:  # link[0]是link_id
                return link[1], link[2]  # link[1]是源节点ID，link[2]是输出索引
        return None, None
    
    def _extract_task_id_from_workflow(self, workflow: Dict[str, Any]) -> str:
        """从工作流中提取任务ID（如果存在）"""
        # 这里可以从参数中获取，暂时返回一个默认值
        import uuid
        return str(uuid.uuid4())
    
    def _is_negative_prompt_node(self, node: Dict[str, Any], workflow: Dict[str, Any]) -> bool:
        """判断CLIPTextEncode节点是否为负面提示词节点"""
        # 方法1: 通过节点位置判断（负面提示词通常在下方）
        if node.get('pos', [0, 0])[1] > 200:  # Y坐标大于200
            return True
        
        # 方法2: 通过节点颜色判断
        if node.get('color') == '#322' or node.get('bgcolor') == '#533':
            return True
        
        # 方法3: 通过连接关系判断
        node_id = node.get('id')
        if node_id:
            # 检查是否有连接到KSampler的negative输入
            for link in workflow.get('links', []):
                if (link[1] == node_id and  # 输出节点
                    link[3] in self._find_ksampler_nodes(workflow) and  # 输入到KSampler
                    link[4] == 2):  # negative输入（通常是索引2）
                    return True
        
        return False
    
    def _find_ksampler_nodes(self, workflow: Dict[str, Any]) -> list:
        """查找所有KSampler节点"""
        ksampler_ids = []
        for node in workflow.get('nodes', []):
            if node.get('type') == 'KSampler':
                ksampler_ids.append(node.get('id'))
        return ksampler_ids
    
    def create_workflow_from_template(self, template_name: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从模板创建工作流"""
        workflow = self.load_workflow(template_name)
        if workflow:
            return self.update_workflow_parameters(workflow, parameters)
        return None
    
    def _get_node_type_by_id(self, workflow: Dict[str, Any], node_id: int) -> str:
        """根据节点ID获取节点类型"""
        for node in workflow.get('nodes', []):
            if node.get('id') == node_id:
                return node.get('type', '')
        return ''

# 全局工作流管理器实例
workflow_manager = WorkflowManager() 