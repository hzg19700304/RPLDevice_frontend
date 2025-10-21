#!/usr/bin/env python3
"""
测试system_status数据格式和前端处理
"""
# flake8: noqa
import asyncio
import sys
import os
sys.path.append('.')

from websocket_client import WebSocketClient
from config_manager import ConfigManager
import logging
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_system_status():
    """测试system_status数据接收"""
    config = ConfigManager()
    await config.load_config()  # 加载配置文件
    client = WebSocketClient(config)
    
    # 连接状态回调
    async def connection_callback(connected):
        status = "已连接" if connected else "已断开"
        logger.info(f"WebSocket连接状态: {status}")
    
    # 注册连接状态回调
    client.register_connection_callback(connection_callback)
    
    # system_status数据回调
    async def system_status_callback(data):
        logger.info("=" * 50)
        logger.info("收到system_status数据:")
        logger.info(f"数据内容: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # 检查是否包含switch_input和switch_output
        if 'switch_input' in data:
            logger.info(f"✓ 找到switch_input数据: {data['switch_input']}")
        else:
            logger.warning("✗ 未找到switch_input数据")
            
        if 'switch_output' in data:
            logger.info(f"✓ 找到switch_output数据: {data['switch_output']}")
            # 检查KM1状态 (bit0)
            if 'bit0' in data['switch_output']:
                km1_status = "合位" if data['switch_output']['bit0'] == 1 else "分位"
                logger.info(f"KM1状态: {km1_status}")
            else:
                logger.warning("✗ switch_output中未找到bit0 (KM1)")
        else:
            logger.warning("✗ 未找到switch_output数据")
            
        if 'system_status' in data:
            logger.info(f"✓ 找到system_status数据: {data['system_status']}")
        else:
            logger.warning("✗ 未找到system_status数据")
    
    # 注册数据回调
    client.register_data_callback('system_status', system_status_callback)
    
    # 连接服务器
    logger.info("正在连接WebSocket服务器...")
    logger.info(f"WebSocket URL: {client.websocket_url}")
    connected = await client.connect()
    
    if connected:
        logger.info("连接成功，等待接收数据...")
        # 等待接收数据
        await asyncio.sleep(15)
        logger.info("测试完成，断开连接...")
        await client.disconnect()
    else:
        logger.error("连接失败")

if __name__ == "__main__":
    logger.info("开始测试system_status数据格式...")
    logger.info("请确保后端服务器正在运行...")
    asyncio.run(test_system_status())