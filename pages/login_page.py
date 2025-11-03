#!/usr/bin/env python3
"""
简洁的用户登录页面
Simple User Login Page
"""

import logging
from typing import Optional, Dict, Any
from nicegui import ui
from datetime import datetime
import hashlib
import secrets

from api_client import get_api_client

logger = logging.getLogger(__name__)

class LoginPage:
    """登录页面类"""
    
    def __init__(self, config_manager, on_login_success=None):
        """
        初始化登录页面
        
        Args:
            config_manager: 配置管理器
            on_login_success: 登录成功回调函数
        """
        self.config = config_manager
        self.on_login_success = on_login_success
        self.current_user = None
        self.login_token = None
        
        # 内存存储替代ui.storage
        self.remember_me = False
        self.stored_username = None
        self.stored_token = None
        
        # API客户端
        self.api_client = get_api_client()
        
        # 默认用户配置(作为后备)
        self.default_users = {
            'admin': {
                'password': self._hash_password('admin123'),
                'role': 'administrator',
                'display_name': '系统管理员',
                'permissions': ['all']
            },
            'operator': {
                'password': self._hash_password('operator123'),
                'role': 'operator',
                'display_name': '操作员',
                'permissions': ['view', 'control']
            }
        }
        
        # 登录状态
        self.is_logged_in = False
        self.login_time = None
        self.session_timeout = 3600
        
        # UI元素
        self.username_input = None
        self.password_input = None
        self.login_button = None
        self.error_label = None
        self.remember_checkbox = None
        
    def _hash_password(self, password: str) -> str:
        """密码哈希处理"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_token(self) -> str:
        """生成登录令牌"""
        return secrets.token_urlsafe(32)
    
    def _validate_credentials(self, username: str, password: str) -> bool:
        """验证用户凭据"""
        if username in self.default_users:
            hashed_password = self._hash_password(password)
            return self.default_users[username]['password'] == hashed_password
        return False
    
    def _check_session_timeout(self) -> bool:
        """检查会话是否超时"""
        if not self.login_time:
            return True
        
        current_time = datetime.now()
        session_duration = (current_time - self.login_time).total_seconds()
        return session_duration > self.session_timeout
    
    async def _handle_login(self):
        """处理登录逻辑"""
        try:
            username = self.username_input.value.strip()
            password = self.password_input.value
            
            # 输入验证
            if not username or not password:
                self._show_error('请输入用户名和密码')
                return
            
            # 显示加载状态
            self.login_button.set_text('登录中...')
            self.login_button.set_enabled(False)
            
            try:
                # 首先尝试使用API客户端进行认证
                result = await self.api_client.login(username, password)
                
                if result.get('code') == 200:
                    # API认证成功
                    data = result.get('data', {})
                    user_info = data.get('user_info', {})
                    
                    self.current_user = username
                    self.is_logged_in = True
                    self.login_time = datetime.now()
                    self.login_token = data.get('token')
                    
                    logger.info(f"用户登录成功 - 用户名: {username}, 角色: {user_info.get('permission_type', 'unknown')}")
                    
                    # 记住登录状态
                    if self.remember_checkbox.value:
                        try:
                            ui.storage.user['remember_me'] = True
                            ui.storage.user['username'] = username
                            ui.storage.user['login_token'] = self.login_token
                        except AttributeError:
                            logger.warning("当前NiceGUI版本不支持ui.storage,使用内存存储")
                            self.remember_me = True
                            self.stored_username = username
                            self.stored_token = self.login_token
                    
                    # 隐藏错误信息
                    self._hide_error()
                    
                    # 显示成功消息
                    ui.notify('登录成功!', type='positive')
                    
                    # 调用成功回调
                    if self.on_login_success:
                        try:
                            user_info = {
                                'username': username,
                                'display_name': user_info.get('full_name', username),
                                'role': user_info.get('permission_type', 'unknown'),
                                'permissions': ['all'] if user_info.get('permission_type') == 'admin' else ['view', 'control'],
                                'login_time': self.login_time,
                                'token': self.login_token
                            }
                            self.on_login_success(user_info)
                        except Exception as callback_error:
                            logger.error(f"登录成功回调失败: {callback_error}")
                            ui.navigate.to('/main')
                    
                    return
                else:
                    # API认证失败,显示错误信息
                    logger.warning(f"API认证失败: {result.get('msg')}")
                    self._show_error(f"登录失败: {result.get('msg', '用户名或密码错误')}")
                    return
                    
            except Exception as api_error:
                logger.error(f"API认证失败: {api_error}")
                # 显示API返回的具体错误信息
                self._show_error(str(api_error))
                return
            
        except Exception as e:
            logger.error(f"登录处理失败: {e}")
            self._show_error('登录失败,请重试')
        finally:
            # 恢复登录按钮状态
            self.login_button.set_text('登录')
            self.login_button.set_enabled(True)
    
    def _show_error(self, message: str):
        """显示错误信息"""
        if self.error_label:
            self.error_label.text = message
            self.error_label.set_visibility(True)
        else:
            ui.notify(message, type='negative')
    
    def _hide_error(self):
        """隐藏错误信息"""
        if self.error_label:
            self.error_label.set_visibility(False)
    
    def check_auto_login(self):
        """检查自动登录"""
        try:
            try:
                remember_me = ui.storage.user.get('remember_me', False)
                username = ui.storage.user.get('username', None)
                stored_token = ui.storage.user.get('login_token', None)
            except AttributeError:
                remember_me = getattr(self, 'remember_me', False)
                username = getattr(self, 'stored_username', None)
                stored_token = getattr(self, 'stored_token', None)
            
            if remember_me and username and stored_token:
                if not self._check_session_timeout():
                    self.current_user = username
                    self.login_token = stored_token
                    self.is_logged_in = True
                    
                    logger.info(f"自动登录成功 - 用户名: {username}")
                    return True
                else:
                    try:
                        ui.storage.user['remember_me'] = False
                        ui.storage.user['username'] = None
                        ui.storage.user['login_token'] = None
                    except AttributeError:
                        self.remember_me = False
                        self.stored_username = None
                        self.stored_token = None
            
            return False
            
        except Exception as e:
            logger.error(f"自动登录检查失败: {e}")
            return False
    
    def get_current_user_info(self) -> Optional[Dict[str, Any]]:
        """获取当前用户信息"""
        if not self.current_user or not self.is_logged_in:
            return None
        
        user_data = self.default_users.get(self.current_user, {})
        return {
            'username': self.current_user,
            'display_name': user_data.get('display_name', self.current_user),
            'role': user_data.get('role', 'unknown'),
            'permissions': user_data.get('permissions', []),
            'login_time': self.login_time,
            'token': self.login_token
        }
    
    def create_login_page(self):
        """创建登录页面"""
        # 检查自动登录
        if self.check_auto_login():
            if self.on_login_success:
                user_info = self.get_current_user_info()
                self.on_login_success(user_info)
            return
        
        # 获取字体配置
        font_config = self.config.get_font_config()
        scale_factor = font_config.get('font_scale_factor', 1.0)
        
        # 设置页面样式
        ui.add_head_html('''
        <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            margin: 0 !important;
            padding: 0 !important;
            height: 100vh !important;
            overflow: hidden !important;
            font-family: 'Microsoft YaHei', Arial, sans-serif;
        }
        
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            width: 100vw;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            position: fixed;
            top: 0;
            left: 0;
        }
        
        .login-card {
            background: #f5f5f5;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            padding: 0;
            width: 440px;
            max-width: 90%;
            margin: 0 auto;
            position: relative;
        }
        
        .login-content {
            padding: 40px 50px 30px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        

        
        .user-avatar {
            width: 80px;
            height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #7b88db 0%, #8e7cc3 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .user-avatar svg {
            width: 45px;
            height: 45px;
            fill: white;
        }
        
        .login-title {
            text-align: center !important;
            color: #333;
            font-size: 22px;
            font-weight: 600;
            margin: 0 auto 8px auto !important;
            width: 100%;
            display: block;
        }
        
        .login-subtitle {
            text-align: center !important;
            color: #999;
            font-size: 9px;
            margin: 0 auto 30px auto !important;
            width: 100%;
            display: block;
        }
        

        
        .q-field__control {
            height: 48px !important;
            min-height: 48px !important;
            background: white !important;
            border: 1px solid #e0e0e0 !important;
            border-radius: 8px !important;
            padding: 0 12px !important;
        }
        
        .q-field__control:before,
        .q-field__control:after {
            display: none !important;
        }
        
        .q-field--float .q-field__label {
            transform: translateY(-135%) scale(0.75) !important;
            color: #999 !important;
        }
        
        .q-field__native {
            padding: 12px 0 !important;
            color: #333 !important;
        }
        

        
        .q-checkbox__label {
            color: #666 !important;
            font-size: 14px !important;
        }
        
        /* 登录按钮样式 */
        .login-btn {
            height: 48px !important;
            background: linear-gradient(135deg, #7b88db 0%, #8e7cc3 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-size: 16px !important;
            font-weight: 500 !important;
            cursor: pointer !important;
            transition: all 0.3s !important;
        }
        
        .login-btn:hover {
            opacity: 0.9 !important;
            transform: translateY(-1px) !important;
        }
        
        .login-footer {
            text-align: center !important;
            padding: 12px;
            color: #999;
            font-size: 12px;
            margin: 0 auto !important;
            width: 100%;
            display: block;
        }
        
        .error-msg {
            background: #fee;
            border-left: 3px solid #f44336;
            color: #c62828;
            padding: 10px 12px;
            border-radius: 4px;
            margin: 0 auto 16px auto !important;
            font-size: 14px;
            width: 100%;
            max-width: 320px;
            text-align: left;
        }
        

        </style>
        ''')
        
        # 创建登录界面
        with ui.element('div').classes('login-container'):
            with ui.card().classes('login-card'):
                with ui.element('div').classes('login-content'):
                    # 用户头像
                    with ui.element('div').classes('user-avatar'):
                        ui.html('''
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                        </svg>
                        ''')
                    
                    # 标题
                    ui.label('钢轨电位限制装置控制系统').classes('login-title')
                    
                    # 版本号
                    version = self.config.get('设备配置', '系统版本', '1.0.0')
                    ui.label(f'版本号：V{version}').classes('login-subtitle')
                    
                    # 错误信息
                    self.error_label = ui.label('').classes('error-msg')
                    self.error_label.set_visibility(False)
                    
                    # 用户名
                    with ui.element('div').style('display: flex; justify-content: center; margin-bottom: 16px;'):
                        self.username_input = ui.input(
                            placeholder='用户名',
                        ).props('outlined').style('width: 320px; max-width: 100%;')
                    
                    # 密码
                    with ui.element('div').style('display: flex; justify-content: center; margin-bottom: 16px;'):
                        self.password_input = ui.input(
                            placeholder='密码',
                            password=True,
                            password_toggle_button=True
                        ).props('outlined').style('width: 320px; max-width: 100%;')
                    
                    # 记住登录
                    with ui.element('div').style('display: flex; justify-content: flex-start; margin-bottom: 20px; width: 320px; max-width: 100%; margin-left: auto; margin-right: auto;'):
                        self.remember_checkbox = ui.checkbox('记住登录状态')
                    
                    # 登录按钮
                    with ui.element('div').style('display: flex; justify-content: center; margin-bottom: 16px;'):
                        self.login_button = ui.button(
                            '登录',
                            on_click=self._handle_login
                        ).classes('login-btn').style('width: 320px !important; max-width: 100%;')
                
                # 底部
                with ui.element('div').classes('login-footer'):
                    ui.label('湖南恒创开拓电气有限公司')
        
        # 回车登录
        self.username_input.on('keydown.enter', self._handle_login)
        self.password_input.on('keydown.enter', self._handle_login)
        
        # 自动填充用户名
        try:
            remember_me = ui.storage.user.get('remember_me', False)
            username = ui.storage.user.get('username', '')
            
            if remember_me and username:
                self.username_input.value = username
                self.remember_checkbox.value = True
        except AttributeError:
            pass