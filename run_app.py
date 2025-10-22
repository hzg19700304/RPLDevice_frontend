#!/usr/bin/env python3
# flake8: noqa
"""
应用启动脚本
Application Startup Script
"""

import logging
from nicegui import ui, app
from main import hmi_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 设置httpx日志级别为WARNING，减少HTTP请求调试信息
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx.http2').setLevel(logging.WARNING)
logging.getLogger('httpx.connection').setLevel(logging.WARNING)

# 设置NiceGUI日志级别为ERROR，减少客户端警告信息
logging.getLogger('nicegui').setLevel(logging.ERROR)

@ui.page('/')
async def index():
    """主页面"""
    try:
        print("正在启动钢轨电位限制柜人机界面...")
        
        # 初始化应用
        await hmi_app.initialize()
        print("✓ 应用初始化完成")
        
        # 启动WebSocket连接
        await hmi_app.start_websocket()
        print("✓ WebSocket客户端已启动")
        
        print("应用启动成功！")
        print("请在浏览器中访问: http://localhost:8080")
        
    except Exception as e:
        print(f"✗ 应用启动失败: {e}")
        raise

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="钢轨电位限制柜人机界面",
        port=8080,
        host="0.0.0.0",
        favicon="🚄",
        dark=False,
        show=False
    )