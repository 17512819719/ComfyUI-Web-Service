"""
ComfyUI节点管理器
负责节点注册、发现、健康检查和负载均衡
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import json

from .base import (
    BaseNodeManager, ComfyUINode, NodeStatus, TaskType, 
    NodeManagementError
)
from .config_manager import get_config_manager

logger = logging.getLogger(__name__)


class ComfyUINodeManager(BaseNodeManager):
    """ComfyUI节点管理器实现"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self._nodes: Dict[str, ComfyUINode] = {}
        self._node_tasks: Dict[str, Set[str]] = defaultdict(set)  # 节点任务映射
        self._health_check_interval = 30  # 健康检查间隔(秒)
        self._heartbeat_timeout = 60  # 心跳超时时间(秒)
        self._running = False
        self._health_check_task = None
        
    async def start(self):
        """启动节点管理器"""
        if self._running:
            return
            
        self._running = True
        # 启动健康检查任务
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        # 加载配置中的静态节点
        await self._load_static_nodes()
        
        logger.info("节点管理器已启动")
    
    async def stop(self):
        """停止节点管理器"""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("节点管理器已停止")
    
    async def _load_static_nodes(self):
        """从配置文件加载静态节点"""
        try:
            nodes_config = self.config_manager.get_config('nodes')
            static_nodes = nodes_config.get('static_nodes', [])
            
            for node_config in static_nodes:
                node = ComfyUINode(
                    node_id=node_config['node_id'],
                    host=node_config['host'],
                    port=node_config['port'],
                    status=NodeStatus.OFFLINE,
                    last_heartbeat=datetime.now(),
                    max_concurrent=node_config.get('max_concurrent', 4),
                    capabilities=node_config.get('capabilities', []),
                    metadata=node_config.get('metadata', {})
                )
                
                # 尝试连接并注册节点
                if await self._check_node_health(node):
                    node.status = NodeStatus.ONLINE
                    self._nodes[node.node_id] = node
                    logger.info(f"静态节点已注册: {node.node_id} ({node.url})")
                else:
                    logger.warning(f"静态节点连接失败: {node.node_id} ({node.url})")
                    
        except Exception as e:
            logger.error(f"加载静态节点失败: {e}")
    
    async def register_node(self, node: ComfyUINode) -> bool:
        """注册节点"""
        try:
            # 检查节点健康状态
            if not await self._check_node_health(node):
                logger.warning(f"节点健康检查失败: {node.node_id}")
                return False
            
            # 更新节点状态
            node.status = NodeStatus.ONLINE
            node.last_heartbeat = datetime.now()
            
            # 注册节点
            self._nodes[node.node_id] = node
            self._node_tasks[node.node_id] = set()
            
            logger.info(f"节点注册成功: {node.node_id} ({node.url})")
            return True
            
        except Exception as e:
            logger.error(f"注册节点失败 {node.node_id}: {e}")
            raise NodeManagementError(f"注册节点失败: {e}")
    
    async def unregister_node(self, node_id: str) -> bool:
        """注销节点"""
        try:
            if node_id in self._nodes:
                node = self._nodes[node_id]
                
                # 检查是否有正在执行的任务
                active_tasks = self._node_tasks.get(node_id, set())
                if active_tasks:
                    logger.warning(f"节点 {node_id} 仍有 {len(active_tasks)} 个活跃任务")
                    # 可以选择等待任务完成或强制转移任务
                
                # 移除节点
                del self._nodes[node_id]
                if node_id in self._node_tasks:
                    del self._node_tasks[node_id]
                
                logger.info(f"节点注销成功: {node_id}")
                return True
            else:
                logger.warning(f"尝试注销不存在的节点: {node_id}")
                return False
                
        except Exception as e:
            logger.error(f"注销节点失败 {node_id}: {e}")
            raise NodeManagementError(f"注销节点失败: {e}")
    
    async def get_available_nodes(self, task_type: Optional[TaskType] = None) -> List[ComfyUINode]:
        """获取可用节点"""
        available_nodes = []
        
        for node in self._nodes.values():

            # 检查节点是否可用
            if not node.is_available:
                continue
            
            # 检查任务类型兼容性
            if task_type and node.capabilities:
                if task_type.value not in node.capabilities:
                    continue
            
            available_nodes.append(node)
        
        # 按负载排序，负载低的优先
        available_nodes.sort(key=lambda n: n.load_percentage)
        
        return available_nodes
    
    async def get_best_node(self, task_type: Optional[TaskType] = None) -> Optional[ComfyUINode]:
        """获取最佳节点（负载最低的可用节点）"""
        available_nodes = await self.get_available_nodes(task_type)
        return available_nodes[0] if available_nodes else None
    
    async def update_node_status(self, node_id: str, status: NodeStatus) -> bool:
        """更新节点状态"""
        if node_id in self._nodes:
            self._nodes[node_id].status = status
            self._nodes[node_id].last_heartbeat = datetime.now()
            logger.debug(f"节点状态更新: {node_id} -> {status.value}")
            return True
        return False
    
    async def update_node_load(self, node_id: str, current_load: int) -> bool:
        """更新节点负载"""
        if node_id in self._nodes:
            self._nodes[node_id].current_load = current_load
            self._nodes[node_id].last_heartbeat = datetime.now()
            return True
        return False
    
    async def assign_task_to_node(self, node_id: str, task_id: str) -> bool:
        """分配任务到节点"""
        if node_id in self._nodes:
            self._node_tasks[node_id].add(task_id)
            self._nodes[node_id].current_load = len(self._node_tasks[node_id])
            logger.debug(f"任务分配: {task_id} -> {node_id}")
            return True
        return False
    
    async def remove_task_from_node(self, node_id: str, task_id: str) -> bool:
        """从节点移除任务"""
        if node_id in self._node_tasks:
            self._node_tasks[node_id].discard(task_id)
            if node_id in self._nodes:
                self._nodes[node_id].current_load = len(self._node_tasks[node_id])
            logger.debug(f"任务移除: {task_id} <- {node_id}")
            return True
        return False
    
    async def health_check(self, node_id: str) -> bool:
        """单个节点健康检查"""
        if node_id not in self._nodes:
            return False
        
        node = self._nodes[node_id]
        return await self._check_node_health(node)
    
    async def _check_node_health(self, node: ComfyUINode) -> bool:
        """检查节点健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{node.url}/system_stats",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        # 可以解析响应获取更多信息
                        stats = await response.json()
                        # 更新节点元数据
                        node.metadata.update({
                            'last_check': datetime.now().isoformat(),
                            'system_stats': stats
                        })
                        return True
                    else:
                        logger.warning(f"节点健康检查失败: {node.node_id}, 状态码: {response.status}")
                        return False
                        
        except Exception as e:
            logger.warning(f"节点健康检查异常: {node.node_id}, 错误: {e}")
            return False
    
    def get_all_nodes(self) -> Dict[str, ComfyUINode]:
        """获取所有节点"""
        return self._nodes.copy()
    
    def get_node_by_id(self, node_id: str) -> Optional[ComfyUINode]:
        """根据ID获取节点"""
        return self._nodes.get(node_id)

    async def _health_check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查循环异常: {e}")
                await asyncio.sleep(5)  # 出错时短暂等待

    async def _perform_health_checks(self):
        """执行所有节点的健康检查"""
        current_time = datetime.now()
        offline_nodes = []

        for node_id, node in self._nodes.items():
            # 检查心跳超时
            if (current_time - node.last_heartbeat).total_seconds() > self._heartbeat_timeout:
                logger.warning(f"节点心跳超时: {node_id}")
                node.status = NodeStatus.OFFLINE
                continue

            # 执行健康检查
            if node.status != NodeStatus.MAINTENANCE:
                is_healthy = await self._check_node_health(node)
                if is_healthy:
                    if node.status == NodeStatus.OFFLINE:
                        logger.info(f"节点恢复在线: {node_id}")
                    node.status = NodeStatus.ONLINE
                    node.last_heartbeat = current_time
                else:
                    if node.status == NodeStatus.ONLINE:
                        logger.warning(f"节点离线: {node_id}")
                    node.status = NodeStatus.OFFLINE
                    offline_nodes.append(node_id)

        # 处理离线节点的任务重新分配
        for node_id in offline_nodes:
            await self._handle_node_failure(node_id)

    async def _handle_node_failure(self, node_id: str):
        """处理节点故障"""
        if node_id in self._node_tasks:
            failed_tasks = self._node_tasks[node_id].copy()
            if failed_tasks:
                logger.warning(f"节点 {node_id} 故障，需要重新分配 {len(failed_tasks)} 个任务")
                # 这里可以实现任务重新分配逻辑
                # 暂时清空任务列表
                self._node_tasks[node_id].clear()
                if node_id in self._nodes:
                    self._nodes[node_id].current_load = 0

    def get_cluster_stats(self) -> Dict[str, any]:
        """获取集群统计信息"""
        total_nodes = len(self._nodes)
        online_nodes = len([n for n in self._nodes.values() if n.status == NodeStatus.ONLINE])
        total_capacity = sum(n.max_concurrent for n in self._nodes.values())
        current_load = sum(n.current_load for n in self._nodes.values())

        return {
            'total_nodes': total_nodes,
            'online_nodes': online_nodes,
            'offline_nodes': total_nodes - online_nodes,
            'total_capacity': total_capacity,
            'current_load': current_load,
            'load_percentage': (current_load / total_capacity * 100) if total_capacity > 0 else 0,
            'available_slots': total_capacity - current_load
        }


# 全局节点管理器实例
_node_manager = None


def get_node_manager() -> ComfyUINodeManager:
    """获取节点管理器实例"""
    global _node_manager
    if _node_manager is None:
        _node_manager = ComfyUINodeManager()
    return _node_manager
