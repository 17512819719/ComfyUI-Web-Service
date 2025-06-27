import json
import os
from typing import Dict, Any, Optional

class WorkflowManager:
    """工作流管理器，用于加载和管理ComfyUI JSON工作流文件"""
    
    def __init__(self, workflows_dir: str = "workflows"):
        if not os.path.isabs(workflows_dir):
            self.workflows_dir = os.path.join(os.path.dirname(__file__), '..', workflows_dir)
        else:
            self.workflows_dir = workflows_dir
        self.workflows_cache = {}
    
    def load_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """加载指定的工作流文件"""
        if workflow_name in self.workflows_cache:
            return json.loads(json.dumps(self.workflows_cache[workflow_name]))
        
        workflow_path = os.path.join(self.workflows_dir, workflow_name)
        if not workflow_path.endswith('.json'):
            workflow_path += '.json'
        
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
                self.workflows_cache[workflow_name] = workflow
                return json.loads(json.dumps(workflow))
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
        """用参数替换工作流中的模板变量"""
        import copy
        workflow = copy.deepcopy(workflow)
        def replace(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                        param_name = v[2:-2].strip()
                        if param_name in parameters:
                            obj[k] = parameters[param_name]
                    else:
                        replace(v)
            elif isinstance(obj, list):
                for item in obj:
                    replace(item)
        if 'workflow' in workflow:
            replace(workflow['workflow'])
        return workflow
    
    def create_workflow_from_template(self, template_name: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从模板创建工作流"""
        workflow = self.load_workflow(template_name)
        if workflow:
            return self.update_workflow_parameters(workflow, parameters)
        return None

# 全局工作流管理器实例
workflow_manager = WorkflowManager() 