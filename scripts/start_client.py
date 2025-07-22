import os
import sys
import subprocess
from pathlib import Path

def start_client():
    """启动客户端前端服务"""
    try:
        # 获取项目根目录
        root_dir = Path(__file__).parent.parent
        client_dir = root_dir / 'frontend' / 'client'
        
        # 打印调试信息
        print("\n=== Debug Information ===")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Client directory: {client_dir}")
        print(f"Client directory exists: {client_dir.exists()}")
        print(f"PATH environment: {os.environ.get('PATH')}")
        print(f"Node version:")
        try:
            subprocess.run(['node', '-v'], shell=True, check=True)
        except Exception as e:
            print(f"Failed to get node version: {e}")
        print(f"NPM version:")
        try:
            subprocess.run(['npm', '-v'], shell=True, check=True)
        except Exception as e:
            print(f"Failed to get npm version: {e}")
        print("========================\n")

        # 检查目录是否存在
        if not client_dir.exists():
            print("[ERROR] Client directory not found:", client_dir)
            return False

        # 检查 package.json 是否存在
        if not (client_dir / 'package.json').exists():
            print("[ERROR] package.json not found in client directory")
            return False

        # 检查 node_modules 是否存在，不存在则安装依赖
        if not (client_dir / 'node_modules').exists():
            print("[INFO] Installing client dependencies...")
            subprocess.run('npm install', shell=True, cwd=client_dir, check=True)

        # 启动开发服务器
        print("[INFO] Starting client development server...")
        subprocess.run('npm run dev', shell=True, cwd=client_dir, check=True)
        return True

    except subprocess.CalledProcessError as e:
        print("[ERROR] Failed to start client:", e)
        return False
    except Exception as e:
        print("[ERROR] Unexpected error while starting client:", e)
        print(f"Error type: {type(e)}")
        print(f"Error details: {str(e)}")
        return False

if __name__ == '__main__':
    success = start_client()
    sys.exit(0 if success else 1) 