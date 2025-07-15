"""
负载均衡器
实现智能任务分发算法，支持多种负载均衡策略
"""
import random
import logging
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from enum import Enum

from .base import ComfyUINode, TaskType, NodeStatus
from .config_manager import get_config_manager

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    WEIGHTED = "weighted"
    RANDOM = "random"
    PRIORITY_BASED = "priority_based"


class BaseLoadBalancer(ABC):
    """负载均衡器基类"""
    
    @abstractmethod
    def select_node(self, available_nodes: List[ComfyUINode], task_type: Optional[TaskType] = None) -> Optional[ComfyUINode]:
        """选择节点"""
        pass


class RoundRobinBalancer(BaseLoadBalancer):
    """轮询负载均衡器"""
    
    def __init__(self):
        self._current_index = 0
    
    def select_node(self, available_nodes: List[ComfyUINode], task_type: Optional[TaskType] = None) -> Optional[ComfyUINode]:
        if not available_nodes:
            return None
        
        # 轮询选择
        node = available_nodes[self._current_index % len(available_nodes)]
        self._current_index += 1
        
        logger.debug(f"轮询选择节点: {node.node_id}")
        return node


class LeastLoadedBalancer(BaseLoadBalancer):
    """最少负载均衡器"""
    
    def select_node(self, available_nodes: List[ComfyUINode], task_type: Optional[TaskType] = None) -> Optional[ComfyUINode]:
        if not available_nodes:
            return None
        
        # 选择负载最低的节点
        node = min(available_nodes, key=lambda n: n.load_percentage)
        
        logger.debug(f"最少负载选择节点: {node.node_id} (负载: {node.load_percentage:.1f}%)")
        return node


class WeightedBalancer(BaseLoadBalancer):
    """加权负载均衡器"""
    
    def select_node(self, available_nodes: List[ComfyUINode], task_type: Optional[TaskType] = None) -> Optional[ComfyUINode]:
        if not available_nodes:
            return None
        
        # 根据节点权重和当前负载计算选择概率
        weights = []
        for node in available_nodes:
            # 获取节点优先级作为权重
            priority = node.metadata.get('priority', 1)
            # 负载越低，权重越高
            load_factor = max(0.1, 1.0 - (node.load_percentage / 100))
            weight = priority * load_factor
            weights.append(weight)
        
        # 加权随机选择
        total_weight = sum(weights)
        if total_weight == 0:
            return available_nodes[0]
        
        rand_val = random.uniform(0, total_weight)
        current_weight = 0
        
        for i, weight in enumerate(weights):
            current_weight += weight
            if rand_val <= current_weight:
                node = available_nodes[i]
                logger.debug(f"加权选择节点: {node.node_id} (权重: {weight:.2f})")
                return node
        
        return available_nodes[-1]


class RandomBalancer(BaseLoadBalancer):
    """随机负载均衡器"""
    
    def select_node(self, available_nodes: List[ComfyUINode], task_type: Optional[TaskType] = None) -> Optional[ComfyUINode]:
        if not available_nodes:
            return None
        
        node = random.choice(available_nodes)
        logger.debug(f"随机选择节点: {node.node_id}")
        return node


class PriorityBasedBalancer(BaseLoadBalancer):
    """基于优先级的负载均衡器"""
    
    def select_node(self, available_nodes: List[ComfyUINode], task_type: Optional[TaskType] = None) -> Optional[ComfyUINode]:
        if not available_nodes:
            return None
        
        # 按优先级分组
        priority_groups = {}
        for node in available_nodes:
            priority = node.metadata.get('priority', 1)
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(node)
        
        # 选择最高优先级组
        highest_priority = max(priority_groups.keys())
        high_priority_nodes = priority_groups[highest_priority]
        
        # 在最高优先级组中选择负载最低的节点
        node = min(high_priority_nodes, key=lambda n: n.load_percentage)
        
        logger.debug(f"优先级选择节点: {node.node_id} (优先级: {highest_priority}, 负载: {node.load_percentage:.1f}%)")
        return node


class SmartLoadBalancer:
    """智能负载均衡器"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self._balancers = {
            LoadBalancingStrategy.ROUND_ROBIN: RoundRobinBalancer(),
            LoadBalancingStrategy.LEAST_LOADED: LeastLoadedBalancer(),
            LoadBalancingStrategy.WEIGHTED: WeightedBalancer(),
            LoadBalancingStrategy.RANDOM: RandomBalancer(),
            LoadBalancingStrategy.PRIORITY_BASED: PriorityBasedBalancer(),
        }
        self._current_strategy = None
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        lb_config = self.config_manager.get_load_balancing_config()
        strategy_name = lb_config.get('strategy', 'least_loaded')
        
        try:
            self._current_strategy = LoadBalancingStrategy(strategy_name)
        except ValueError:
            logger.warning(f"未知的负载均衡策略: {strategy_name}, 使用默认策略: least_loaded")
            self._current_strategy = LoadBalancingStrategy.LEAST_LOADED
        
        logger.info(f"负载均衡策略: {self._current_strategy.value}")
    
    def select_node(self, available_nodes: List[ComfyUINode], task_type: Optional[TaskType] = None) -> Optional[ComfyUINode]:
        """选择最佳节点"""
        if not available_nodes:
            logger.warning("没有可用节点")
            return None
        
        # 过滤可用节点
        suitable_nodes = self._filter_suitable_nodes(available_nodes, task_type)
        if not suitable_nodes:
            logger.warning(f"没有适合任务类型 {task_type} 的节点")
            return None
        
        # 使用当前策略选择节点
        balancer = self._balancers[self._current_strategy]
        selected_node = balancer.select_node(suitable_nodes, task_type)
        
        if selected_node:
            logger.info(f"选择节点: {selected_node.node_id} (策略: {self._current_strategy.value})")
        
        return selected_node
    
    def _filter_suitable_nodes(self, nodes: List[ComfyUINode], task_type: Optional[TaskType]) -> List[ComfyUINode]:
        """过滤适合的节点"""
        suitable_nodes = []
        
        for node in nodes:
            # 检查节点状态
            if node.status != NodeStatus.ONLINE:
                continue
            
            # 检查节点是否有可用容量
            if not node.is_available:
                continue
            
            # 检查任务类型兼容性
            if task_type and node.capabilities:
                if task_type.value not in node.capabilities:
                    continue
            
            suitable_nodes.append(node)
        
        return suitable_nodes
    
    def get_current_strategy(self) -> LoadBalancingStrategy:
        """获取当前策略"""
        return self._current_strategy
    
    def set_strategy(self, strategy: LoadBalancingStrategy):
        """设置负载均衡策略"""
        if strategy in self._balancers:
            self._current_strategy = strategy
            logger.info(f"负载均衡策略已更改为: {strategy.value}")
        else:
            raise ValueError(f"不支持的负载均衡策略: {strategy}")
    
    def get_node_score(self, node: ComfyUINode, task_type: Optional[TaskType] = None) -> float:
        """计算节点评分（用于调试和监控）"""
        if node.status != NodeStatus.ONLINE:
            return 0.0
        
        # 基础评分
        score = 100.0
        
        # 负载因子 (负载越低评分越高)
        load_factor = 1.0 - (node.load_percentage / 100)
        score *= load_factor
        
        # 优先级因子
        priority = node.metadata.get('priority', 1)
        score *= priority
        
        # 任务类型兼容性
        if task_type and node.capabilities:
            if task_type.value not in node.capabilities:
                score = 0.0
        
        return score


# 全局负载均衡器实例
_load_balancer = None


def get_load_balancer() -> SmartLoadBalancer:
    """获取负载均衡器实例"""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = SmartLoadBalancer()
    return _load_balancer
