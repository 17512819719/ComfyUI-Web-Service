#!/usr/bin/env python3
"""
分布式配置验证脚本
验证config.yaml中的分布式配置是否正确，并测试节点连接
"""

import sys
import os
import asyncio
import aiohttp
import yaml
from pathlib import Path

# 添加backend路径到sys.path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.core.config_manager import get_config_manager


class DistributedConfigValidator:
    """分布式配置验证器"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.errors = []
        self.warnings = []
        
    def validate_config(self):
        """验证配置文件"""
        print("🔍 开始验证分布式配置...")
        
        # 1. 检查分布式模式是否启用
        if not self.config_manager.is_distributed_mode():
            self.errors.append("分布式模式未启用，请检查nodes配置")
            return False
            
        # 2. 验证节点配置
        self._validate_nodes_config()
        
        # 3. 验证负载均衡配置
        self._validate_load_balancing_config()
        
        # 4. 验证健康检查配置
        self._validate_health_check_config()
        
        # 5. 验证Redis配置
        self._validate_redis_config()
        
        return len(self.errors) == 0
        
    def _validate_nodes_config(self):
        """验证节点配置"""
        nodes_config = self.config_manager.get_config('nodes')
        static_nodes = nodes_config.get('static_nodes', [])
        
        if not static_nodes:
            self.errors.append("未配置任何静态节点")
            return
            
        print(f"📋 发现 {len(static_nodes)} 个静态节点配置")
        
        for i, node in enumerate(static_nodes):
            node_id = node.get('node_id', f'node-{i}')
            
            # 检查必需字段
            required_fields = ['node_id', 'host', 'port']
            for field in required_fields:
                if field not in node:
                    self.errors.append(f"节点 {node_id} 缺少必需字段: {field}")
                    
            # 检查IP地址格式
            host = node.get('host', '')
            if host == "192.168.1.101":
                self.warnings.append(f"节点 {node_id} 使用默认IP地址，请修改为实际地址")
                
            # 检查端口范围
            port = node.get('port', 8188)
            if not (1 <= port <= 65535):
                self.errors.append(f"节点 {node_id} 端口号无效: {port}")
                
            # 检查并发数
            max_concurrent = node.get('max_concurrent', 1)
            if max_concurrent < 1:
                self.errors.append(f"节点 {node_id} 最大并发数必须大于0")
                
            print(f"  ✓ {node_id}: {host}:{port} (并发: {max_concurrent})")
            
    def _validate_load_balancing_config(self):
        """验证负载均衡配置"""
        nodes_config = self.config_manager.get_config('nodes')
        lb_config = nodes_config.get('load_balancing', {})
        
        strategy = lb_config.get('strategy', 'least_loaded')
        valid_strategies = ['round_robin', 'least_loaded', 'weighted', 'random', 'priority_based']
        
        if strategy not in valid_strategies:
            self.errors.append(f"无效的负载均衡策略: {strategy}")
        else:
            print(f"⚖️  负载均衡策略: {strategy}")
            
        # 检查故障转移配置
        enable_failover = lb_config.get('enable_failover', True)
        max_retries = lb_config.get('max_retries', 3)
        
        print(f"🔄 故障转移: {'启用' if enable_failover else '禁用'} (重试: {max_retries}次)")
        
    def _validate_health_check_config(self):
        """验证健康检查配置"""
        nodes_config = self.config_manager.get_config('nodes')
        hc_config = nodes_config.get('health_check', {})
        
        interval = hc_config.get('interval', 30)
        timeout = hc_config.get('timeout', 5)
        heartbeat_timeout = hc_config.get('heartbeat_timeout', 60)
        
        if interval < 10:
            self.warnings.append("健康检查间隔过短，可能影响性能")
            
        if timeout >= interval:
            self.errors.append("健康检查超时时间不应大于等于检查间隔")
            
        print(f"💓 健康检查: 间隔{interval}s, 超时{timeout}s, 心跳超时{heartbeat_timeout}s")
        
    def _validate_redis_config(self):
        """验证Redis配置"""
        redis_config = self.config_manager.get_config('redis')
        
        host = redis_config.get('host', 'localhost')
        port = redis_config.get('port', 6379)
        
        print(f"📦 Redis配置: {host}:{port}")
        
    async def test_node_connectivity(self):
        """测试节点连接性"""
        print("\n🌐 测试节点连接性...")
        
        nodes_config = self.config_manager.get_config('nodes')
        static_nodes = nodes_config.get('static_nodes', [])
        
        if not static_nodes:
            print("❌ 没有配置的节点可测试")
            return False
            
        all_connected = True
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for node in static_nodes:
                node_id = node.get('node_id')
                host = node.get('host')
                port = node.get('port', 8188)
                
                try:
                    # 测试ComfyUI API连接
                    url = f"http://{host}:{port}/system_stats"
                    async with session.get(url) as response:
                        if response.status == 200:
                            print(f"  ✅ {node_id} ({host}:{port}) - 连接成功")
                        else:
                            print(f"  ⚠️  {node_id} ({host}:{port}) - HTTP {response.status}")
                            all_connected = False
                            
                except aiohttp.ClientError as e:
                    print(f"  ❌ {node_id} ({host}:{port}) - 连接失败: {e}")
                    all_connected = False
                except Exception as e:
                    print(f"  ❌ {node_id} ({host}:{port}) - 未知错误: {e}")
                    all_connected = False
                    
        return all_connected
        
    def print_summary(self):
        """打印验证结果摘要"""
        print("\n" + "="*60)
        print("📊 配置验证结果摘要")
        print("="*60)
        
        if self.errors:
            print(f"❌ 发现 {len(self.errors)} 个错误:")
            for error in self.errors:
                print(f"   • {error}")
                
        if self.warnings:
            print(f"⚠️  发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings:
                print(f"   • {warning}")
                
        if not self.errors and not self.warnings:
            print("✅ 配置验证通过，没有发现问题")
            
        print("\n💡 建议:")
        print("   1. 确保所有从机已启动ComfyUI服务")
        print("   2. 检查网络连接和防火墙设置")
        print("   3. 验证从机ComfyUI监听在0.0.0.0:8188")
        print("   4. 运行 'python scripts/test_distributed.py' 进行完整测试")


async def main():
    """主函数"""
    print("🚀 ComfyUI分布式配置验证工具")
    print("="*60)
    
    validator = DistributedConfigValidator()
    
    # 验证配置
    config_valid = validator.validate_config()
    
    if config_valid:
        # 测试节点连接
        await validator.test_node_connectivity()
        
    # 打印摘要
    validator.print_summary()
    
    return config_valid


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 验证过程中发生错误: {e}")
        sys.exit(1)
