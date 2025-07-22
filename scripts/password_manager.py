#!/usr/bin/env python3
"""
密码管理脚本
用于生成、验证和重置bcrypt哈希密码
"""

import sys
import getpass
from pathlib import Path

# 添加backend路径到sys.path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from passlib.context import CryptContext
except ImportError:
    print("❌ 缺少依赖: passlib")
    print("请安装: pip install passlib[bcrypt]")
    sys.exit(1)


class PasswordManager:
    """密码管理器"""
    
    def __init__(self):
        # 创建密码上下文，使用bcrypt算法
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12  # 成本因子，对应$12$
        )
    
    def hash_password(self, password: str) -> str:
        """生成密码哈希"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def need_update(self, hashed_password: str) -> bool:
        """检查密码哈希是否需要更新"""
        return self.pwd_context.needs_update(hashed_password)


def generate_password_hash():
    """生成新密码哈希"""
    print("🔐 生成新密码哈希")
    print("-" * 40)
    
    password = getpass.getpass("请输入新密码: ")
    if not password:
        print("❌ 密码不能为空")
        return
    
    confirm_password = getpass.getpass("请确认密码: ")
    if password != confirm_password:
        print("❌ 两次输入的密码不一致")
        return
    
    manager = PasswordManager()
    hashed = manager.hash_password(password)
    
    print("\n✅ 密码哈希生成成功:")
    print(f"原密码: {password}")
    print(f"哈希值: {hashed}")
    print("\n💡 请将哈希值保存到数据库中")


def verify_password_hash():
    """验证密码哈希"""
    print("🔍 验证密码哈希")
    print("-" * 40)
    
    password = getpass.getpass("请输入要验证的密码: ")
    if not password:
        print("❌ 密码不能为空")
        return
    
    print("请输入哈希值:")
    hashed = input().strip()
    if not hashed:
        print("❌ 哈希值不能为空")
        return
    
    manager = PasswordManager()
    
    try:
        is_valid = manager.verify_password(password, hashed)
        
        if is_valid:
            print("✅ 密码验证成功！")
        else:
            print("❌ 密码验证失败！")
            
        # 检查是否需要更新哈希
        if manager.need_update(hashed):
            print("⚠️  建议更新密码哈希（使用更安全的参数）")
            
    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")


def reset_admin_password():
    """重置管理员密码"""
    print("🔄 重置管理员密码")
    print("-" * 40)
    
    try:
        # 导入数据库相关模块
        from app.database.connection import get_database_manager
        from app.admin_api.models import User
        from sqlalchemy.orm import sessionmaker
        
        # 获取新密码
        new_password = getpass.getpass("请输入新的管理员密码: ")
        if not new_password:
            print("❌ 密码不能为空")
            return
        
        confirm_password = getpass.getpass("请确认新密码: ")
        if new_password != confirm_password:
            print("❌ 两次输入的密码不一致")
            return
        
        # 生成密码哈希
        manager = PasswordManager()
        hashed_password = manager.hash_password(new_password)
        
        # 连接数据库
        db_manager = get_database_manager()
        admin_engine = db_manager.get_engine('admin')
        Session = sessionmaker(bind=admin_engine)
        session = Session()
        
        try:
            # 查找管理员用户
            admin_user = session.query(User).filter(User.username == 'admin').first()
            
            if not admin_user:
                print("❌ 未找到管理员用户")
                return
            
            # 更新密码
            admin_user.password_hash = hashed_password
            session.commit()
            
            print("✅ 管理员密码重置成功！")
            print(f"新密码哈希: {hashed_password}")
            
        except Exception as e:
            session.rollback()
            print(f"❌ 数据库操作失败: {e}")
        finally:
            session.close()
            
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保在项目根目录运行此脚本")
    except Exception as e:
        print(f"❌ 重置密码失败: {e}")


def analyze_hash():
    """分析密码哈希"""
    print("🔍 分析密码哈希")
    print("-" * 40)
    
    print("请输入要分析的哈希值:")
    hashed = input().strip()
    if not hashed:
        print("❌ 哈希值不能为空")
        return
    
    print(f"\n📊 哈希分析结果:")
    print(f"完整哈希: {hashed}")
    
    # 分析bcrypt哈希结构
    if hashed.startswith('$2') or hashed.startswith('$2a') or hashed.startswith('$2b') or hashed.startswith('$2y'):
        parts = hashed.split('$')
        if len(parts) >= 4:
            print(f"算法标识: ${parts[1]}$")
            print(f"成本因子: {parts[2]}")
            print(f"盐值: {parts[3][:22]}")
            print(f"哈希值: {parts[3][22:]}")
            print(f"算法: bcrypt")
            print(f"安全级别: {'高' if int(parts[2]) >= 12 else '中等' if int(parts[2]) >= 10 else '低'}")
        else:
            print("❌ 哈希格式不正确")
    else:
        print("⚠️  未识别的哈希格式")
    
    # 检查是否需要更新
    manager = PasswordManager()
    try:
        if manager.need_update(hashed):
            print("⚠️  建议更新此哈希（使用更安全的参数）")
        else:
            print("✅ 哈希参数符合当前安全标准")
    except Exception as e:
        print(f"⚠️  无法检查哈希状态: {e}")


def show_example():
    """显示示例"""
    print("📚 bcrypt密码哈希示例")
    print("-" * 40)
    
    example_password = "admin123"
    manager = PasswordManager()
    
    print(f"示例密码: {example_password}")
    
    # 生成多个哈希示例
    print("\n生成的哈希示例:")
    for i in range(3):
        hashed = manager.hash_password(example_password)
        print(f"  {i+1}. {hashed}")
    
    print("\n💡 注意:")
    print("  • 相同密码每次生成的哈希都不同（因为盐值随机）")
    print("  • 但都可以验证原密码")
    print("  • $12$ 表示成本因子为12，计算复杂度为2^12")
    print("  • 成本因子越高越安全，但验证时间越长")


def main():
    """主菜单"""
    while True:
        print("\n" + "=" * 50)
        print("🔐 ComfyUI 密码管理工具")
        print("=" * 50)
        print("1. 生成新密码哈希")
        print("2. 验证密码哈希")
        print("3. 重置管理员密码")
        print("4. 分析密码哈希")
        print("5. 查看示例")
        print("0. 退出")
        print("-" * 50)
        
        try:
            choice = input("请选择操作 (0-5): ").strip()
            
            if choice == "0":
                print("👋 再见！")
                break
            elif choice == "1":
                generate_password_hash()
            elif choice == "2":
                verify_password_hash()
            elif choice == "3":
                reset_admin_password()
            elif choice == "4":
                analyze_hash()
            elif choice == "5":
                show_example()
            else:
                print("❌ 无效选择，请输入 0-5")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出程序")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")


if __name__ == "__main__":
    print("🚀 ComfyUI密码管理工具")
    print("支持bcrypt密码哈希的生成、验证和管理")
    
    # 检查当前提供的哈希
    current_hash = "$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx/LBK2."
    print(f"\n🔍 检测到哈希: {current_hash}")
    
    manager = PasswordManager()
    print("📊 哈希信息:")
    print("  • 算法: bcrypt")
    print("  • 成本因子: 12")
    print("  • 安全级别: 高")
    print("\n💡 提示: bcrypt是单向哈希，无法解密，只能验证密码是否正确")
    
    main()
