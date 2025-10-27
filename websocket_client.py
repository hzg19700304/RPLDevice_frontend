"""
WebSocket客户端模块
WebSocket Client Module
"""
# flake8: noqa
import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketClient:
    """WebSocket客户端"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.websocket = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_interval = 5
        self.heartbeat_task = None
        self.receive_task = None
        
        # 数据回调函数
        self.data_callbacks = {}
        
        # 连接状态回调
        self.connection_callbacks = []
        
        # 获取WebSocket配置
        ws_config = self.config.get_websocket_config()
        self.server_host = ws_config.get('listen_ip', '127.0.0.1')
        self.server_port = ws_config.get('listen_port', 8765)
        self.heartbeat_interval = ws_config.get('heartbeat_interval', 10)
        self.max_reconnect_attempts = ws_config.get('reconnect_attempts', 10)
        
        # 如果配置的是0.0.0.0，改为localhost用于客户端连接
        if self.server_host == '0.0.0.0':
            self.server_host = 'localhost'
        
        # 构建WebSocket URL
        protocol = ws_config.get('protocol_type', 'ws')
        self.websocket_url = f"{protocol}://{self.server_host}:{self.server_port}"
        
    async def connect(self) -> bool:
        """连接到WebSocket服务器"""
        try:
            logger.info(f"正在连接到WebSocket服务器: {self.websocket_url}")
            # 清理旧连接
            if self.websocket:
                try:
                    await self.websocket.close()
                except:
                    pass

            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=self.heartbeat_interval,
                ping_timeout=self.heartbeat_interval * 2
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0 # ⭐ 重置重连计数器
            
            # 启动心跳和接收任务，异步任务在后台持续运行
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.receive_task = asyncio.create_task(self._receive_loop())
            
            # 发送设备注册信息
            await self._send_device_registration()
            
            # 通知连接状态变化
            await self._notify_connection_status(True)
            
            logger.info("WebSocket连接成功")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            self.is_connected = False
            await self._notify_connection_status(False)
            
            # 尝试重连
            if self.reconnect_attempts < self.max_reconnect_attempts:
                await self._schedule_reconnect()
            
            return False
    
    async def disconnect(self) -> None:
        """断开WebSocket连接"""
        self.is_connected = False
        
        # 取消任务
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.receive_task:
            self.receive_task.cancel()
        
        # 关闭连接
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        await self._notify_connection_status(False)
        logger.info("WebSocket连接已断开")
    
    async def send_message(self, message_type: str, data: Dict[str, Any]) -> bool:
        """发送消息到服务器"""
        if not self.is_connected or not self.websocket:
            logger.warning("WebSocket未连接，无法发送消息")
            return False
        
        try:
            message = {
                'type': message_type,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            message_str = json.dumps(message, ensure_ascii=False)
            await self.websocket.send(message_str)
            logger.info(f"发送消息: {message_type}")
            logger.info(f"消息内容: {message_str}")
            return True
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            await self._notify_connection_status(False)
            return False
    
    async def _receive_loop(self) -> None:
        """接收消息循环"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    # logger.info(f"收到消息: {data}")
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"消息解析失败: {e}")
                except Exception as e:
                    logger.error(f"处理消息失败: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已关闭")
            self.is_connected = False
            await self._notify_connection_status(False)
            
            # 尝试重连
            if self.reconnect_attempts < self.max_reconnect_attempts:
                # logger.info("准备重新连接...")
                await self._schedule_reconnect()
                
        except Exception as e:
            logger.error(f"接收消息循环异常: {e}")
    
    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """处理接收到的消息"""
        message_type = message.get('type')
        data = message.get('data', {})
        
        # 记录所有收到的消息类型
        # logger.info(f"收到消息类型: {message_type}")
        
        # 对于param_write_ack类型的消息，需要特殊处理，因为exec_status和exec_msg在根级别
        if message_type == 'param_write_ack':
            # 将根级别的字段合并到data中，确保回调函数可以访问
            for key in ['exec_status', 'exec_msg', 'request_id', 'device_id', 'timestamp']:
                if key in message and key not in data:
                    data[key] = message[key]
        
        # if message_type == 'full_snapshot':
        #     logger.info(f"全量快照数据详情: {message}")
        # # 处理特殊消息类型
        # if message_type == "welcome":
        #     logger.info("收到服务器欢迎消息")
        # elif message_type == "pong":
        #     logger.debug("收到心跳响应")
        
        # 调用注册的回调函数
        if message_type in self.data_callbacks:
            # logger.info(f"找到 {message_type} 类型的回调函数，数量: {len(self.data_callbacks[message_type])}")
            for callback in self.data_callbacks[message_type]:
                try:
                    # logger.info(f"执行 {message_type} 类型的回调函数")
                    await callback(data)
                except Exception as e:
                    logger.error(f"回调函数执行失败: {e}")
        else:
            logger.debug(f"未找到 {message_type} 类型的回调函数")
    
    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self.is_connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.is_connected:
                    await self.send_message('heartbeat', {'timestamp': datetime.now().isoformat()})
            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
                # 尝试重连
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    # logger.info("准备重新连接...")
                    await self._schedule_reconnect()
                break
    
    async def _schedule_reconnect(self) -> None:
        """安排重连"""
        self.reconnect_attempts += 1
        logger.info(f"将在{self.reconnect_interval}秒后尝试重连 (第{self.reconnect_attempts}次)")
        
        await asyncio.sleep(self.reconnect_interval)
        await self.connect()
    
    async def _send_device_registration(self) -> None:
        """发送设备注册信息"""
        try:
            # 获取设备配置信息
            device_config = self.config.get_device_info()
            
            registration_data = {
                "type": "device_register",
                "device_id": device_config.get('设备ID', 'HYP_RPLD_001'),
                "device_name": device_config.get('设备名称', '红岩坪站钢轨电位限制装置'),
                "device_ip": device_config.get('设备IP', '192.168.0.11'),
                "system_version": device_config.get('系统版本', '1.0.0'),
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket.send(json.dumps(registration_data, ensure_ascii=False))
            logger.info(f"发送设备注册信息: {device_config.get('设备ID')}")
            
        except Exception as e:
            logger.error(f"发送设备注册信息失败: {e}")
    
    async def _notify_connection_status(self, connected: bool) -> None:
        """通知连接状态变化"""
        for callback in self.connection_callbacks:
            try:
                await callback(connected)
            except Exception as e:
                logger.error(f"连接状态回调失败: {e}")
    
    def register_data_callback(self, message_type: str, callback: Callable) -> None:
        """注册数据回调函数"""
        if message_type not in self.data_callbacks:
            self.data_callbacks[message_type] = []
        self.data_callbacks[message_type].append(callback)
        logger.debug(f"注册数据回调: {message_type}")
    
    def register_connection_callback(self, callback: Callable) -> None:
        """注册连接状态回调函数"""
        self.connection_callbacks.append(callback)
        logger.debug("注册连接状态回调")
    
    def unregister_data_callback(self, message_type: str, callback: Callable) -> None:
        """取消注册数据回调函数"""
        if message_type in self.data_callbacks:
            try:
                self.data_callbacks[message_type].remove(callback)
                logger.debug(f"取消注册数据回调: {message_type}")
            except ValueError:
                pass
    
    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态信息"""
        return {
            'connected': self.is_connected,
            'server_url': self.websocket_url,
            'reconnect_attempts': self.reconnect_attempts,
            'max_reconnect_attempts': self.max_reconnect_attempts
        }