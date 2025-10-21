#!/usr/bin/env python3
"""
WebSocket连接测试脚本
"""
# flake8: noqa

import asyncio
import websockets
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """测试WebSocket连接"""
    uri = "ws://localhost:8766"
    
    try:
        logger.info(f"连接到 {uri}")
        async with websockets.connect(uri) as websocket:
            logger.info("连接成功！")
            
            # 等待欢迎消息
            welcome_msg = await websocket.recv()
            logger.info(f"收到欢迎消息: {welcome_msg}")
            
            # 发送心跳消息
            heartbeat_msg = {
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(heartbeat_msg))
            logger.info("发送心跳消息")
            
            # 等待响应
            response = await websocket.recv()
            logger.info(f"收到响应: {response}")
            
            # 发送状态查询
            status_msg = {
                "type": "get_status"
            }
            await websocket.send(json.dumps(status_msg))
            logger.info("发送状态查询")
            
            # 等待状态响应
            status_response = await websocket.recv()
            logger.info(f"收到状态响应: {status_response}")
            
            # 保持连接一段时间，接收广播消息
            logger.info("等待广播消息...")
            for i in range(3):
                try:
                    broadcast_msg = await asyncio.wait_for(websocket.recv(), timeout=6)
                    logger.info(f"收到广播消息 {i+1}: {broadcast_msg}")
                except asyncio.TimeoutError:
                    logger.warning("等待广播消息超时")
                    break
            
            logger.info("测试完成")
            
    except Exception as e:
        logger.error(f"连接失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())