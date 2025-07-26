# ComfyUI手动补丁说明

## 简单修改方案

由于自动劫持ComfyUI比较复杂，使用手动修改的方式更可靠。

### 第一步：复制文件

将以下文件复制到ComfyUI目录：
- `comfyui_file_download_patch.py`

### 第二步：修改ComfyUI的server.py

找到ComfyUI的 `server.py` 文件，通常在ComfyUI根目录下。

在文件开头添加导入：

```python
# 在文件开头添加
try:
    import comfyui_file_download_patch
    comfyui_file_download_patch.patch_comfyui_server()
    print("✅ 文件下载补丁已加载")
except Exception as e:
    print(f"⚠️ 文件下载补丁加载失败: {e}")
```

### 第三步：修改prompt处理函数

在 `server.py` 中找到处理 `/prompt` 请求的函数，通常是 `prompt` 函数。

在函数开头添加文件下载处理：

```python
async def prompt(request):
    # 添加文件下载处理
    try:
        data = await request.json()

        # 检查是否有文件下载指令
        if 'file_downloads' in data:
            print(f"🔽 检测到文件下载指令: {len(data['file_downloads'])} 个文件")

            # 调用文件下载处理函数（多种方式尝试）
            processed = False

            # 方式1: 从__builtins__获取
            if hasattr(__builtins__, 'comfyui_process_downloads'):
                data = __builtins__.comfyui_process_downloads(data)
                processed = True
            # 方式2: 从globals()获取
            elif 'comfyui_process_downloads' in globals():
                data = globals()['comfyui_process_downloads'](data)
                processed = True
            # 方式3: 直接从__builtins__获取属性
            elif 'comfyui_process_downloads' in dir(__builtins__):
                data = getattr(__builtins__, 'comfyui_process_downloads')(data)
                processed = True
            # 方式4: 直接导入处理
            else:
                try:
                    import comfyui_file_download_patch
                    data = comfyui_file_download_patch.process_prompt_with_file_downloads(data)
                    processed = True
                except Exception as import_error:
                    print(f"⚠️ 导入处理失败: {import_error}")

            if processed:
                print("✅ 文件下载处理完成")
            else:
                print("⚠️ 文件下载处理函数未找到")

        # 重新创建请求对象
        import json
        from aiohttp.web_request import Request
        request._body = json.dumps(data).encode()

    except Exception as e:
        print(f"❌ 文件下载处理失败: {e}")
        import traceback
        traceback.print_exc()

    # 原有的prompt处理逻辑继续...
```

### 第四步：重启ComfyUI

重启ComfyUI，应该看到：
```
[COMFYUI_DOWNLOADER] 文件下载补丁已加载，可手动调用patch_comfyui_server()应用
[COMFYUI_DOWNLOADER] 应用简化补丁
[COMFYUI_DOWNLOADER] 补丁应用成功
[COMFYUI_DOWNLOADER] 可通过 comfyui_process_downloads(data) 调用文件下载处理
✅ 文件下载补丁已加载
```

**✅ 当前状态**：补丁已成功加载，`comfyui_process_downloads` 函数已注册到全局命名空间。

**⚠️ 当前问题**：prompt处理代码中的函数查找方式需要更新，使用上面第三步中的多种方式尝试代码。

## 验证方法

### 1. 检查补丁加载

ComfyUI启动时应该显示补丁加载成功的消息。

### 2. 测试文件下载

从主机提交图生视频任务，观察ComfyUI日志：

```
🔽 检测到文件下载指令: 1 个文件
[COMFYUI_DOWNLOADER] 检测到文件下载指令: 1 个文件
[COMFYUI_DOWNLOADER] 开始下载: http://主机:8000/api/v2/files/upload/path/...
[COMFYUI_DOWNLOADER] 下载完成: E:\ComfyUI\ComfyUI\input\2025\07\26\image.png
[COMFYUI_DOWNLOADER] 更新路径: 54.inputs.image = 2025/07/26/image.png
✅ 文件下载处理完成
```

### 3. 检查文件

确认文件已下载到ComfyUI的input目录：
```
E:\ComfyUI\ComfyUI\input\2025\07\26\image.png
```

## 故障排除

### 问题1：找不到server.py

如果找不到 `server.py`，可能在以下位置：
- `ComfyUI/server.py`
- `ComfyUI/web/server.py`
- `ComfyUI/comfyui/server.py`

### 问题2：找不到prompt函数

搜索文件中的 `def prompt` 或 `async def prompt`。

### 问题3：修改后无效

1. 确认修改保存了
2. 重启ComfyUI
3. 检查控制台输出

### 问题4：文件下载处理函数未找到

如果看到 `⚠️ 文件下载处理函数未找到`，说明函数查找方式有问题。

**解决方法**：
1. 确认补丁已加载（启动时应该看到 `✅ 文件下载补丁已加载`）
2. 使用第三步中的多种方式尝试代码
3. 检查prompt处理函数中的代码是否正确

### 问题5：语法错误

确保Python缩进正确，建议使用代码编辑器。

## 备用方案

如果手动修改太复杂，可以使用代理服务器方案：

```bash
python comfyui_proxy_server.py --proxy-port 8189 --comfyui-port 8188
```

然后修改主机配置，将ComfyUI地址改为代理服务器地址。
