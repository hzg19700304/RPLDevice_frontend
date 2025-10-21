#!/usr/bin/env python3
"""
配置测试脚本
Configuration Test Script
"""
# flake8: noqa
import asyncio
import sys
from config_manager import ConfigManager

async def test_config():
    """测试配置管理器"""
    try:
        print("正在测试配置管理器...")
        
        # 创建配置管理器实例
        config = ConfigManager()
        
        # 加载配置
        await config.load_config()
        print("✓ 配置文件加载成功")
        
        # 测试设备信息
        device_info = config.get_device_info()
        print(f"✓ 设备名称: {device_info.get('设备名称')}")
        print(f"✓ 设备ID: {device_info.get('设备ID')}")
        
        # 测试WebSocket配置
        ws_config = config.get_websocket_config()
        print(f"✓ WebSocket端口: {ws_config.get('listen_port')}")
        
        # 测试界面配置
        enabled_pages = config.get_enabled_pages()
        print(f"✓ 启用的页面数量: {len(enabled_pages)}")
        for key, name in enabled_pages.items():
            print(f"  - {name}")
        
        # 测试状态位配置
        status_bits = config.get_system_status_bits()
        print(f"✓ 系统状态位配置数量: {len(status_bits)}")
        
        print("\n所有配置测试通过！")
        return True
        
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_config())
    sys.exit(0 if success else 1)