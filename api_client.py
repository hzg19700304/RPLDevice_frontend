#!/usr/bin/env python3
"""
API客户端模块
用于与后端API服务器通信
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import aiohttp

logger = logging.getLogger(__name__)


class APIClient:
    """API客户端类"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        """
        初始化API客户端
        
        Args:
            base_url: API服务器基础URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.token = None
        self.user_info = None
        
        # 创建HTTP客户端
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json"}
        )
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Dict[str, Any]: 登录结果
            
        Raises:
            Exception: 登录失败时抛出异常
        """
        try:
            # 构建登录请求
            login_data = {
                "username": username,
                "password": password
            }
            
            # 发送登录请求
            response = await self.client.post(
                "/api/v1/auth/login",
                json=login_data
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应数据
            result = response.json()
            
            if result.get("code") == 200:
                # 保存Token和用户信息
                data = result.get("data", {})
                self.token = data.get("token")
                self.user_info = data.get("user_info", {})
                
                # 更新客户端认证头
                if self.token:
                    self.client.headers["Authorization"] = f"Bearer {self.token}"
                
                logger.info(f"用户登录成功: {username}")
                return result
            else:
                error_msg = result.get("msg", "登录失败")
                logger.error(f"用户登录失败: {error_msg}")
                raise Exception(error_msg)
                
        except httpx.HTTPStatusError as e:
            # 处理HTTP状态错误，特别是401未授权错误
            if e.response.status_code == 401:
                # 尝试从响应中获取具体错误信息
                try:
                    # FastAPI的HTTPException通常返回{"detail": "错误信息"}
                    error_data = e.response.json()
                    error_msg = error_data.get("detail", "用户名或密码错误")
                    
                    # 根据具体的错误信息提供更友好的提示
                    if "用户不存在" in error_msg:
                        error_msg = "登录失败：用户不存在"
                    elif "密码错误" in error_msg or "密码验证失败" in error_msg:
                        error_msg = "登录失败：密码错误"
                    elif "用户已禁用" in error_msg:
                        error_msg = "登录失败：用户已禁用"
                except:
                    error_msg = "用户名或密码错误"
                logger.error(f"用户登录失败: {error_msg}")
                raise Exception(error_msg)
            else:
                error_msg = f"HTTP错误: {e.response.status_code}"
                logger.error(f"用户登录失败: {error_msg}")
                raise Exception(error_msg)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"用户登录失败: {error_msg}")
            raise Exception(error_msg)
    
    async def logout(self) -> Dict[str, Any]:
        """
        用户登出
        
        Returns:
            Dict[str, Any]: 登出结果
        """
        try:
            response = await self.client.post("/api/v1/auth/logout")
            response.raise_for_status()
            
            result = response.json()
            
            # 清理本地Token和用户信息
            self.token = None
            self.user_info = None
            if "Authorization" in self.client.headers:
                del self.client.headers["Authorization"]
            
            logger.info("用户登出成功")
            return result
            
        except Exception as e:
            logger.error(f"用户登出失败: {e}")
            # 即使API调用失败，也清理本地状态
            self.token = None
            self.user_info = None
            if "Authorization" in self.client.headers:
                del self.client.headers["Authorization"]
            raise Exception(f"登出失败: {str(e)}")
    
    async def get_device_info(self) -> Dict[str, Any]:
        """
        获取设备信息
        
        Returns:
            Dict[str, Any]: 设备信息
        """
        try:
            response = await self.client.get("/api/v1/device/info")
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                return result.get("data", {})
            else:
                raise Exception(result.get("msg", "获取设备信息失败"))
                
        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")
            raise Exception(f"获取设备信息失败: {str(e)}")
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """
        获取连接状态
        
        Returns:
            Dict[str, Any]: 连接状态信息
        """
        try:
            response = await self.client.get("/api/v1/device/connection_status")
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                return result.get("data", {})
            else:
                raise Exception(result.get("msg", "获取连接状态失败"))
                
        except Exception as e:
            logger.error(f"获取连接状态失败: {e}")
            raise Exception(f"获取连接状态失败: {str(e)}")
    
    async def get_analog_history(self, start_time: str, end_time: str, 
                                param_name: Optional[str] = None,
                                page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        获取历史模拟量数据
        
        Args:
            start_time: 开始时间 (ISO格式)
            end_time: 结束时间 (ISO格式)
            param_name: 参数名称（可选）
            page: 页码
            page_size: 每页条数
            
        Returns:
            Dict[str, Any]: 历史数据
        """
        try:
            params = {
                "start_time": start_time,
                "end_time": end_time,
                "page": page,
                "page_size": page_size
            }
            
            if param_name:
                params["param_name"] = param_name
            
            response = await self.client.get("/api/v1/history/analog", params=params)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                return result.get("data", {})
            else:
                raise Exception(result.get("msg", "获取历史数据失败"))
                
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            raise Exception(f"获取历史数据失败: {str(e)}")
    
    async def change_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        修改密码
        
        Args:
            current_password: 当前密码
            new_password: 新密码
            
        Returns:
            Dict[str, Any]: 修改密码结果
            
        Raises:
            Exception: 修改密码失败时抛出异常
        """
        try:
            # 构建修改密码请求
            password_data = {
                "current_password": current_password,
                "new_password": new_password
            }
            
            # 发送修改密码请求
            response = await self.client.post(
                "/api/v1/auth/change_password",
                json=password_data
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应数据
            result = response.json()
            
            if result.get("code") == 200:
                logger.info("密码修改成功")
                return result
            else:
                error_msg = result.get("msg", "修改密码失败")
                logger.error(f"密码修改失败: {error_msg}")
                raise Exception(error_msg)
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP错误: {e.response.status_code}"
            if e.response.status_code == 401:
                error_msg = "认证失败，请重新登录"
                # 清除认证状态
                self.token = None
                self.user_info = None
                if "Authorization" in self.client.headers:
                    del self.client.headers["Authorization"]
            elif e.response.status_code == 400:
                error_msg = "当前密码不正确"
            logger.error(f"密码修改失败: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"密码修改失败: {error_msg}")
            raise Exception(error_msg)
    
    def is_authenticated(self) -> bool:
        """
        检查是否已认证
        
        Returns:
            bool: 是否已认证
        """
        return self.token is not None and self.user_info is not None
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        获取当前用户信息
        
        Returns:
            Optional[Dict[str, Any]]: 当前用户信息
        """
        return self.user_info
    
    def get_token(self) -> Optional[str]:
        """
        获取当前Token
        
        Returns:
            Optional[str]: 当前Token
        """
        return self.token
    
    async def close(self):
        """关闭HTTP客户端"""
        if self.client:
            await self.client.aclose()


# 全局API客户端实例
api_client = None


def get_api_client() -> APIClient:
    """
    获取全局API客户端实例
    
    Returns:
        APIClient: API客户端实例
    """
    global api_client
    if api_client is None:
        api_client = APIClient()
    return api_client


async def init_api_client(base_url: str = "http://localhost:8000"):
    """
    初始化API客户端
    
    Args:
        base_url: API服务器基础URL
    """
    global api_client
    api_client = APIClient(base_url)
    logger.info(f"API客户端已初始化，服务器地址: {base_url}")


async def close_api_client():
    """关闭API客户端"""
    global api_client
    if api_client:
        await api_client.close()
        api_client = None
        logger.info("API客户端已关闭")