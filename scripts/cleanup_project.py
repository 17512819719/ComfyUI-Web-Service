#!/usr/bin/env python3
"""
项目清理脚本
清理项目中的临时文件、缓存文件、测试文件等
"""

import os
import shutil
import glob
from pathlib import Path


def cleanup_pycache():
    """清理Python缓存文件"""
    print("🧹 清理Python缓存文件...")
    
    project_root = Path(__file__).parent.parent
    pycache_dirs = list(project_root.rglob("__pycache__"))
    
    for cache_dir in pycache_dirs:
        try:
            shutil.rmtree(cache_dir)
            print(f"  ✅ 删除: {cache_dir}")
        except Exception as e:
            print(f"  ❌ 删除失败: {cache_dir} - {e}")
    
    print(f"📊 清理了 {len(pycache_dirs)} 个缓存目录")


def cleanup_pyc_files():
    """清理.pyc文件"""
    print("\n🧹 清理.pyc文件...")
    
    project_root = Path(__file__).parent.parent
    pyc_files = list(project_root.rglob("*.pyc"))
    
    for pyc_file in pyc_files:
        try:
            pyc_file.unlink()
            print(f"  ✅ 删除: {pyc_file}")
        except Exception as e:
            print(f"  ❌ 删除失败: {pyc_file} - {e}")
    
    print(f"📊 清理了 {len(pyc_files)} 个.pyc文件")


def cleanup_logs():
    """清理日志文件（可选）"""
    print("\n🧹 清理日志文件...")
    
    project_root = Path(__file__).parent.parent
    log_dirs = [
        project_root / "backend" / "logs",
        project_root / "logs"
    ]
    
    cleaned_count = 0
    for log_dir in log_dirs:
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            for log_file in log_files:
                try:
                    log_file.unlink()
                    print(f"  ✅ 删除: {log_file}")
                    cleaned_count += 1
                except Exception as e:
                    print(f"  ❌ 删除失败: {log_file} - {e}")
    
    if cleaned_count == 0:
        print("  ℹ️  没有找到日志文件")
    else:
        print(f"📊 清理了 {cleaned_count} 个日志文件")


def cleanup_temp_files():
    """清理临时文件"""
    print("\n🧹 清理临时文件...")
    
    project_root = Path(__file__).parent.parent
    temp_patterns = [
        "*.tmp",
        "*.temp",
        "*.bak",
        "*.swp",
        "*~"
    ]
    
    cleaned_count = 0
    for pattern in temp_patterns:
        temp_files = list(project_root.rglob(pattern))
        for temp_file in temp_files:
            try:
                temp_file.unlink()
                print(f"  ✅ 删除: {temp_file}")
                cleaned_count += 1
            except Exception as e:
                print(f"  ❌ 删除失败: {temp_file} - {e}")
    
    if cleaned_count == 0:
        print("  ℹ️  没有找到临时文件")
    else:
        print(f"📊 清理了 {cleaned_count} 个临时文件")


def cleanup_redis_dump():
    """清理Redis dump文件"""
    print("\n🧹 清理Redis dump文件...")
    
    project_root = Path(__file__).parent.parent
    dump_files = [
        project_root / "backend" / "Redis-x64-3.2.100" / "dump.rdb",
        project_root / "dump.rdb"
    ]
    
    cleaned_count = 0
    for dump_file in dump_files:
        if dump_file.exists():
            try:
                dump_file.unlink()
                print(f"  ✅ 删除: {dump_file}")
                cleaned_count += 1
            except Exception as e:
                print(f"  ❌ 删除失败: {dump_file} - {e}")
    
    if cleaned_count == 0:
        print("  ℹ️  没有找到Redis dump文件")
    else:
        print(f"📊 清理了 {cleaned_count} 个Redis dump文件")


def cleanup_node_modules():
    """清理node_modules（如果存在且很大）"""
    print("\n🧹 检查node_modules...")
    
    project_root = Path(__file__).parent.parent
    node_modules_dirs = list(project_root.rglob("node_modules"))
    
    for node_dir in node_modules_dirs:
        if node_dir.is_dir():
            # 计算目录大小
            total_size = sum(f.stat().st_size for f in node_dir.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            
            print(f"  📁 发现: {node_dir} ({size_mb:.1f} MB)")
            print(f"     ℹ️  提示: 如需清理，请在对应目录运行 'npm install' 重新安装")


def main():
    """主函数"""
    print("🚀 ComfyUI项目清理工具")
    print("=" * 50)
    
    try:
        # 执行清理操作
        cleanup_pycache()
        cleanup_pyc_files()
        cleanup_temp_files()
        cleanup_redis_dump()
        cleanup_node_modules()
        
        # 可选的清理操作（需要用户确认）
        print("\n" + "=" * 50)
        print("🤔 可选清理操作:")
        
        response = input("是否清理日志文件? (y/N): ").lower().strip()
        if response in ['y', 'yes']:
            cleanup_logs()
        else:
            print("  ⏭️  跳过日志文件清理")
        
        print("\n" + "=" * 50)
        print("✅ 项目清理完成！")
        print("\n💡 建议:")
        print("  • 定期运行此脚本保持项目整洁")
        print("  • 清理后可以重新启动服务")
        print("  • 如有问题，检查是否误删重要文件")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  清理被用户中断")
    except Exception as e:
        print(f"\n❌ 清理过程中发生错误: {e}")


if __name__ == "__main__":
    main()
